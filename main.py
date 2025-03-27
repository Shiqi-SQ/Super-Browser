import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import sys
import subprocess
import json
import requests
import platform
import socket

print(f"Python解释器路径: {sys.executable}")
print(f"Python版本: {platform.python_version()}")
print(f"操作系统: {platform.system()} {platform.release()}")

from browser import get_browser_controller

class SuperBrowserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("超级浏览器")
        self.root.geometry("360x260")
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(False, False)
        
        self.browser_controller = get_browser_controller()
        self.browser_started = False
        self.ollama_started = False
        self.ollama_started_by_us = False
        self.executor_started = False
        self.executor_process = None
        
        self.browser_type = tk.StringVar(value="chromium")
        self.model_name = tk.StringVar()
        self.dev_mode = tk.BooleanVar(value=False)
        
        self.talk_process = None
        self.dev_tools_process = None
        
        self.setup_ollama_models_env()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.browser_controller.add_event_listener("browser_closed", self.on_browser_closed)
        
        self.initialize_app()

    def initialize_app(self):
        self.disable_all_controls()
        threading.Thread(target=self._initialize_app_thread, daemon=True).start()

    def _initialize_app_thread(self):
        if not self.start_executor():
            self.log_message("Executor启动失败，程序无法正常运行")
            self.root.after(0, lambda: messagebox.showerror("错误", "Executor启动失败，程序无法正常运行"))
            return
            
        self.start_ollama()
        self.refresh_models()
        self.root.after(0, self.enable_all_controls)

    def start_executor(self):
        try:
            if self.check_executor_running():
                self.log_message("Executor已经在运行")
                self.executor_started = True
                return True
                
            self.log_message("尝试启动executor.py服务器...")
            executor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")
            python_exe = sys.executable
            
            self.executor_process = subprocess.Popen(
                [python_exe, executor_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.log_message(f"Executor进程已启动，PID: {self.executor_process.pid}")
            
            def read_output(stream, prefix):
                try:
                    for line in stream:
                        self.log_message(f"{prefix}: {line.strip()}")
                except Exception as e:
                    self.log_message(f"读取{prefix}时出错: {str(e)}")
                    
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(self.executor_process.stdout, "Executor输出")
            )
            stderr_thread = threading.Thread(
                target=read_output, 
                args=(self.executor_process.stderr, "Executor错误")
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            self.log_message("等待Executor启动...")
            time.sleep(2)
            
            if self.executor_process.poll() is not None:
                self.log_message(f"Executor进程已退出，退出码: {self.executor_process.returncode}")
                return False
                
            for attempt in range(5):
                if self.check_executor_running():
                    self.log_message("Executor已成功启动并可以连接")
                    self.executor_started = True
                    return True
                    
                if self.executor_process.poll() is not None:
                    self.log_message(f"Executor进程已退出，退出码: {self.executor_process.returncode}")
                    return False
                    
                self.log_message(f"连接尝试 {attempt+1} 失败，等待后重试...")
                time.sleep(1)
                
            self.log_message("无法连接到Executor，可能启动失败")
            return False
            
        except Exception as e:
            self.log_message(f"启动Executor时出错: {str(e)}")
            return False

    def check_executor_running(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 9876))
            sock.close()
            return result == 0
        except:
            return False

    def stop_executor(self):
        if self.executor_process:
            self.log_message("尝试停止Executor进程...")
            try:
                self.executor_process.terminate()
                
                try:
                    self.executor_process.wait(timeout=5)
                    self.log_message("Executor进程已停止")
                except subprocess.TimeoutExpired:
                    self.log_message("Executor进程未能及时停止，强制结束")
                    self.executor_process.kill()
                    self.executor_process.wait()
                    self.log_message("Executor进程已强制停止")
                    
            except Exception as e:
                self.log_message(f"停止Executor进程时出错: {str(e)}")
                
            self.executor_process = None
            self.executor_started = False

    def setup_ollama_models_env(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(current_dir, "models")
            
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
                
            os.environ["OLLAMA_MODELS"] = models_dir
            print(f"已设置OLLAMA_MODELS环境变量为: {models_dir}")
            
        except Exception as e:
            print(f"设置OLLAMA_MODELS环境变量时出错: {str(e)}")

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        settings_frame = tk.LabelFrame(main_frame, text="启动设置", bg="#f0f0f0")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        browser_frame = tk.Frame(settings_frame, bg="#f0f0f0")
        browser_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(browser_frame, text="浏览器类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 5))
        browser_types = ["chromium", "firefox", "webkit"]
        self.browser_dropdown = ttk.Combobox(browser_frame, textvariable=self.browser_type, values=browser_types, state="readonly", width=15)
        self.browser_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        model_frame = tk.Frame(settings_frame, bg="#f0f0f0")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(model_frame, text="AI模型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 5))
        self.model_dropdown = ttk.Combobox(model_frame, textvariable=self.model_name, state="readonly", width=30)
        self.model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.refresh_button = tk.Button(model_frame, text="刷新", command=self.refresh_models, bg="#e0e0e0", width=8)
        self.refresh_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        dev_frame = tk.Frame(settings_frame, bg="#f0f0f0")
        dev_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.dev_checkbox = tk.Checkbutton(dev_frame, text="开发者模式", variable=self.dev_mode, bg="#f0f0f0")
        self.dev_checkbox.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(settings_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.start_button = tk.Button(button_frame, text="启动浏览器", command=self.start_browser, bg="#2196F3", fg="white", height=2)
        self.start_button.pack(fill=tk.X)
        
        status_frame = tk.Frame(main_frame, bg="#f0f0f0")
        status_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
        
        self.ollama_status = tk.Label(status_frame, text="Ollama状态: 正在启动...", bg="#f0f0f0", fg="orange")
        self.ollama_status.pack(side=tk.LEFT)
        
        self.browser_status = tk.Label(status_frame, text="浏览器状态: 未启动", bg="#f0f0f0", fg="red")
        self.browser_status.pack(side=tk.RIGHT)

    def disable_all_controls(self):
        self.model_dropdown.config(state="disabled")
        self.start_button.config(state="disabled")
        self.dev_checkbox.config(state="disabled")
        self.refresh_button.config(state="disabled")
        self.browser_dropdown.config(state="disabled")

    def enable_all_controls(self):
        self.model_dropdown.config(state="readonly")
        self.start_button.config(state="normal")
        self.dev_checkbox.config(state="normal")
        self.refresh_button.config(state="normal")
        self.browser_dropdown.config(state="readonly")

    def disable_controls_after_browser_start(self):
        self.model_dropdown.config(state="disabled")
        self.refresh_button.config(state="disabled")
        self.dev_checkbox.config(state="disabled")
        self.browser_dropdown.config(state="disabled")

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[{timestamp}] {message}")

    def start_ollama(self):
        self.log_message("正在启动Ollama服务...")
        
        try:
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    self.ollama_started = True
                    self.ollama_started_by_us = False
                    self.root.after(0, lambda: self.ollama_status.config(text="Ollama状态: 已运行 (外部进程)", fg="green"))
                    self.log_message("Ollama服务已经在运行 (外部进程)")
                    return
            except requests.exceptions.ConnectionError:
                pass
            except requests.exceptions.Timeout:
                pass
                
            ollama_path = ".\\ollama\\ollama.exe"
            if not os.path.exists(ollama_path):
                self.log_message(f"错误: 找不到Ollama可执行文件: {ollama_path}")
                self.root.after(0, lambda: self.ollama_status.config(text="Ollama状态: 未找到可执行文件", fg="red"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"找不到Ollama可执行文件: {ollama_path}"))
                return
                
            process = subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            start_time = time.time()
            while time.time() - start_time < 30:
                try:
                    response = requests.get("http://localhost:11434/api/tags", timeout=2)
                    if response.status_code == 200:
                        self.ollama_started = True
                        self.ollama_started_by_us = True
                        self.root.after(0, lambda: self.ollama_status.config(text="Ollama状态: 已运行", fg="green"))
                        self.log_message("Ollama服务已成功启动")
                        return
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    time.sleep(1)
                    
            self.log_message("Ollama启动失败或超时")
            self.root.after(0, lambda: self.ollama_status.config(text="Ollama状态: 启动失败", fg="red"))
            self.root.after(0, lambda: messagebox.showerror("错误", "Ollama服务启动失败或超时"))
            
        except Exception as e:
            self.log_message(f"启动Ollama时出错: {str(e)}")
            self.root.after(0, lambda: self.ollama_status.config(text="Ollama状态: 启动失败", fg="red"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"启动Ollama时出错: {str(e)}"))

    def refresh_models(self):
        if not self.ollama_started:
            self.log_message("Ollama服务尚未启动，无法获取模型列表")
            messagebox.showwarning("警告", "Ollama服务尚未启动，无法获取模型列表")
            return
            
        self.log_message("正在刷新模型列表...")
        
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            
            if response.status_code == 200:
                models_data = response.json()
                model_names = [model["name"] for model in models_data.get("models", [])]
                
                if not model_names:
                    self.log_message("未找到任何模型，请先使用ollama pull命令下载模型")
                    messagebox.showinfo("提示", "未找到任何模型，请先使用ollama pull命令下载模型")
                else:
                    self.model_dropdown["values"] = model_names
                    self.model_name.set(model_names[0])
                    self.log_message(f"找到 {len(model_names)} 个模型")
            else:
                self.log_message(f"获取模型列表失败: HTTP {response.status_code}")
                messagebox.showerror("错误", f"获取模型列表失败: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_message(f"刷新模型列表时出错: {str(e)}")
            messagebox.showerror("错误", f"刷新模型列表时出错: {str(e)}")

    def start_browser(self):
        if not self.model_name.get():
            messagebox.showwarning("警告", "请先选择一个AI模型")
            return
            
        self.start_button.config(state=tk.DISABLED, text="正在启动...")
        self.log_message(f"正在启动 {self.browser_type.get()} 浏览器...")
        threading.Thread(target=self.launch_browser, daemon=True).start()

    def launch_browser(self):
        try:
            browser_type = self.browser_type.get()
            dev_mode = self.dev_mode.get()
            
            command = f"startBrowser?browser_type={browser_type}"
            if not dev_mode:
                command += "&headless=true"
                
            self.log_message(f"发送启动浏览器命令: {command}")
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(30)
                    self.log_message("正在连接到executor服务器...")
                    s.connect(('127.0.0.1', 9876))
                    self.log_message("已连接到executor服务器，发送命令...")
                    s.sendall(command.encode('utf-8'))
                    self.log_message("命令已发送，等待响应...")
                    response = s.recv(4096).decode('utf-8')
                    self.log_message(f"收到启动浏览器响应: {response}")
            except socket.timeout:
                raise Exception("连接executor服务器超时，请检查服务器是否正常运行")
            except ConnectionRefusedError:
                raise Exception("无法连接到executor服务器，请确保服务器已启动")
            except Exception as e:
                raise Exception(f"与executor服务器通信时出错: {str(e)}")
                
            try:
                response_data = json.loads(response)
                if response_data.get("status") == "error":
                    raise Exception(response_data.get("message", "未知错误"))
                if response_data.get("status") == "success":
                    self.browser_started = True
                    self.log_message("浏览器已成功启动")
            except json.JSONDecodeError:
                if "error" in response.lower() or "失败" in response:
                    raise Exception(f"启动浏览器失败: {response}")
                else:
                    self.browser_started = True
                    self.log_message("浏览器已成功启动（非JSON响应）")
                    
            self.root.after(0, lambda: self.start_button.config(
                text="浏览器已启动", 
                bg="#8BC34A", 
                state=tk.DISABLED
            ))
            
            self.root.after(0, lambda: self.browser_status.config(
                text=f"浏览器状态: {browser_type} 已启动", 
                fg="green"
            ))
            
            self.root.after(0, self.disable_controls_after_browser_start)
            self.log_message(f"{browser_type} 浏览器已成功启动")
            
            self.start_talk_process()
            time.sleep(2)
            
            if self.dev_mode.get():
                self.log_message("开发者模式已启用，准备启动开发者工具...")
                self.start_dev_tools()
            else:
                self.log_message("开发者模式未启用，跳过启动开发者工具")
                
        except Exception as e:
            error_msg = f"启动浏览器时出错: {str(e)}"
            self.log_message(error_msg)
            
            self.root.after(0, lambda: self.start_button.config(
                text="启动浏览器", 
                bg="#2196F3", 
                state=tk.NORMAL
            ))
            
            self.root.after(0, lambda: self.browser_status.config(
                text="浏览器状态: 启动失败", 
                fg="red"
            ))
            
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))

    def start_talk_process(self):
        try:
            model = self.model_name.get()
            talk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "talk.py")
            
            if not os.path.exists(talk_path):
                self.log_message(f"错误: 找不到talk.py文件: {talk_path}")
                return
                
            self.talk_process = subprocess.Popen(
                [sys.executable, talk_path, "--model", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.log_message(f"已启动talk.py进程，使用模型: {model}")
            
        except Exception as e:
            self.log_message(f"启动talk.py时出错: {str(e)}")

    def start_dev_tools(self):
        try:
            dev_tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev_tools.py")
            
            if not os.path.exists(dev_tools_path):
                self.log_message(f"错误: 找不到dev_tools.py文件: {dev_tools_path}")
                return
                
            self.dev_tools_process = subprocess.Popen(
                [sys.executable, dev_tools_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            time.sleep(1)
            
            if self.dev_tools_process.poll() is None:
                self.log_message("已成功启动开发者工具")
            else:
                stdout, stderr = self.dev_tools_process.communicate(timeout=1)
                self.log_message("开发者工具启动失败")
                if stderr:
                    self.log_message(f"错误信息: {stderr}")
                    
        except Exception as e:
            self.log_message(f"启动开发者工具时出错: {str(e)}")

    def on_browser_closed(self):
        self.root.after(0, self._handle_browser_closed)

    def _handle_browser_closed(self):
        if not self.browser_started:
            return
            
        self.browser_started = False
        self.log_message("检测到浏览器已关闭")
        
        self.start_button.config(
            text="启动浏览器", 
            bg="#2196F3", 
            state=tk.NORMAL
        )
        
        self.browser_status.config(
            text="浏览器状态: 已关闭", 
            fg="red"
        )
        
        self.enable_all_controls()
        self.stop_talk_process()
        self.stop_dev_tools()

    def stop_talk_process(self):
        if self.talk_process:
            try:
                self.log_message("正在停止talk.py进程...")
                self.talk_process.terminate()
                
                try:
                    self.talk_process.wait(timeout=5)
                    self.log_message("talk.py进程已停止")
                except subprocess.TimeoutExpired:
                    self.log_message("talk.py进程未能及时停止，强制结束")
                    self.talk_process.kill()
                    self.talk_process.wait()
                    self.log_message("talk.py进程已强制停止")
                    
            except Exception as e:
                self.log_message(f"停止talk.py进程时出错: {str(e)}")
                
            self.talk_process = None

    def stop_dev_tools(self):
        if self.dev_tools_process:
            try:
                self.log_message("正在停止开发者工具进程...")
                self.dev_tools_process.terminate()
                
                try:
                    self.dev_tools_process.wait(timeout=5)
                    self.log_message("开发者工具进程已停止")
                except subprocess.TimeoutExpired:
                    self.log_message("开发者工具进程未能及时停止，强制结束")
                    self.dev_tools_process.kill()
                    self.dev_tools_process.wait()
                    self.log_message("开发者工具进程已强制停止")
                    
            except Exception as e:
                self.log_message(f"停止开发者工具进程时出错: {str(e)}")
                
            self.dev_tools_process = None

    def on_closing(self):
        if self.browser_started:
            if messagebox.askyesno("确认", "浏览器正在运行，确定要退出吗？"):
                self.cleanup_and_exit()
        else:
            self.cleanup_and_exit()

    def cleanup_and_exit(self):
        self.log_message("正在清理资源并退出...")
        
        try:
            if self.browser_started:
                self.log_message("尝试停止浏览器...")
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5)
                        s.connect(('127.0.0.1', 9876))
                        s.sendall("stopBrowser".encode('utf-8'))
                        response = s.recv(4096).decode('utf-8')
                        self.log_message(f"停止浏览器响应: {response}")
                except Exception as e:
                    self.log_message(f"停止浏览器时出错: {str(e)}")
                    
            self.stop_talk_process()
            self.stop_dev_tools()
            
            if self.ollama_started and self.ollama_started_by_us:
                self.log_message("尝试停止Ollama服务...")
                try:
                    requests.post("http://localhost:11434/api/shutdown", timeout=5)
                    self.log_message("已发送Ollama关闭请求")
                except Exception as e:
                    self.log_message(f"停止Ollama服务时出错: {str(e)}")
                    
            self.stop_executor()
            
        except Exception as e:
            self.log_message(f"清理资源时出错: {str(e)}")
            
        self.log_message("程序退出")
        self.root.destroy()

def main():
    root = tk.Tk()
    app = SuperBrowserApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()