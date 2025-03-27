import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import sys
import json
import re
import socket
import queue

class DevToolsUI:
    def __init__(self, root):
        self.root = root
        self.root.title("超级浏览器 - 开发者工具")
        self.root.geometry("680x800")
        self.root.minsize(400, 500)
        self.root.configure(bg="#f5f5f5")
        self.root.attributes("-topmost", True)
        self.current_response = ""
        self.executor_host = '127.0.0.1'
        self.executor_port = 9876
        self.socket = None
        self.connected = False
        self.connection_lock = threading.Lock()
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.help()
        self.update_browser_status()
        self.root.after(5000, self.check_browser_status)
        
        self.response_thread = threading.Thread(target=self.response_processing_thread, daemon=True)
        self.response_thread.start()
        self.socket_thread = threading.Thread(target=self.socket_communication_thread, daemon=True)
        self.socket_thread.start()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        input_frame = tk.LabelFrame(main_frame, text="命令输入", bg="#f5f5f5")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.command_entry = tk.Entry(input_frame, font=("Consolas", 12))
        self.command_entry.pack(fill=tk.X, padx=5, pady=5)
        self.command_entry.bind("<Return>", self.execute_command)
        
        self.execute_button = tk.Button(input_frame, text="执行", command=self.execute_command, bg="#4CAF50", fg="white")
        self.execute_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        message_frame = tk.LabelFrame(main_frame, text="消息显示", bg="#f5f5f5")
        message_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.message_display = scrolledtext.ScrolledText(message_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.message_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.message_display.config(state=tk.DISABLED)
        
        self.message_display.tag_configure("bold", font=("Consolas", 10, "bold"))
        self.message_display.tag_configure("command", foreground="blue")
        self.message_display.tag_configure("result", foreground="black")
        self.message_display.tag_configure("error", foreground="red")
        self.message_display.tag_configure("code", foreground="green", font=("Consolas", 10))
        self.message_display.tag_configure("system", foreground="purple")
        
        status_frame = tk.Frame(self.root, bg="#f0f0f0")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.browser_status_label = tk.Label(status_frame, text="浏览器状态: 检查中...", fg="orange", bg="#f0f0f0")
        self.browser_status_label.pack(side=tk.LEFT, padx=5)
        
        self.connection_status_label = tk.Label(status_frame, text="连接状态: 未连接", fg="red", bg="#f0f0f0")
        self.connection_status_label.pack(side=tk.RIGHT, padx=5)

    def connect(self) -> bool:
        with self.connection_lock:
            if self.connected and self.socket:
                return True
                
            try:
                self.response_queue.put(("system", f"尝试连接到 {self.executor_host}:{self.executor_port}..."))
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(3)
                self.socket.connect((self.executor_host, self.executor_port))
                self.connected = True
                self.response_queue.put(("connection_status", "connected"))
                self.response_queue.put(("system", "已成功连接到服务器"))
                return True
            except Exception as e:
                self.response_queue.put(("error", f"连接失败: {str(e)}"))
                self.socket = None
                self.connected = False
                self.response_queue.put(("connection_status", "disconnected"))
                return False

    def disconnect(self):
        with self.connection_lock:
            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    self.response_queue.put(("error", f"关闭连接时出错: {str(e)}"))
                finally:
                    self.socket = None
                    self.connected = False
                    self.response_queue.put(("connection_status", "disconnected"))

    def socket_communication_thread(self):
        last_heartbeat_time = 0
        heartbeat_interval = 10
        
        while True:
            try:
                current_time = time.time()
                if not self.connected:
                    if not self.connect():
                        time.sleep(5)
                        continue
                        
                try:
                    command, callback = self.command_queue.get(timeout=1)
                    with self.connection_lock:
                        if not self.connected:
                            callback("错误: 未连接到服务器")
                            continue
                            
                        try:
                            self.socket.sendall(command.encode('utf-8'))
                            response = self.socket.recv(4096).decode('utf-8')
                            callback(response)
                        except socket.timeout:
                            self.response_queue.put(("error", "接收响应超时"))
                            callback("错误: 接收响应超时")
                            self.disconnect()
                        except ConnectionResetError:
                            self.response_queue.put(("error", "连接被重置"))
                            callback("错误: 连接被重置")
                            self.disconnect()
                        except Exception as e:
                            self.response_queue.put(("error", f"发送命令时出错: {str(e)}"))
                            callback(f"错误: 发送命令时出错 - {str(e)}")
                            self.disconnect()
                except queue.Empty:
                    if current_time - last_heartbeat_time >= heartbeat_interval:
                        with self.connection_lock:
                            if self.connected:
                                try:
                                    self.socket.sendall("status".encode('utf-8'))
                                    response = self.socket.recv(4096).decode('utf-8')
                                    
                                    try:
                                        status_data = json.loads(response)
                                        server_running = status_data.get("server") == "running"
                                        browser_started = status_data.get("browser_started", False)
                                        browser_running = server_running and browser_started
                                        self.response_queue.put(("browser_status", browser_running))
                                    except json.JSONDecodeError:
                                        self.response_queue.put(("system", f"心跳检测收到异常响应: {response}"))
                                except socket.timeout:
                                    self.response_queue.put(("error", "心跳检测超时"))
                                    self.disconnect()
                                except ConnectionResetError:
                                    self.response_queue.put(("error", "心跳检测时连接被重置"))
                                    self.disconnect()
                                except Exception as e:
                                    self.response_queue.put(("system", f"心跳检测失败: {str(e)}"))
                                    self.disconnect()
                        last_heartbeat_time = current_time
            except Exception as e:
                self.response_queue.put(("error", f"套接字通信线程异常: {str(e)}"))
                self.disconnect()
                time.sleep(5)
    
    def response_processing_thread(self):
        while True:
            try:
                response_type, content = self.response_queue.get()
                
                if response_type == "connection_status":
                    if content == "connected":
                        self.root.after(0, lambda: self.connection_status_label.config(
                            text="连接状态: 已连接", 
                            fg="green"
                        ))
                    else:
                        self.root.after(0, lambda: self.connection_status_label.config(
                            text="连接状态: 未连接", 
                            fg="red"
                        ))
                elif response_type == "browser_status":
                    self.root.after(0, lambda status=content: self.update_browser_status(connected=status))
                else:
                    self.root.after(0, lambda t=response_type, c=content: self.add_message_safe(t, c))
                    
                self.response_queue.task_done()
            except Exception as e:
                print(f"响应处理线程异常: {str(e)}")
                time.sleep(1)

    def add_message_safe(self, message_type, content):
        try:
            self.message_display.config(state=tk.NORMAL)
            self.message_display.insert(tk.END, "\n")
            
            if message_type == "command":
                self.message_display.insert(tk.END, "命令: ", "bold")
                self.message_display.insert(tk.END, content + "\n", "command")
            elif message_type == "error":
                self.message_display.insert(tk.END, "错误: ", "bold")
                self.message_display.insert(tk.END, content + "\n", "error")
            elif message_type == "system":
                self.message_display.insert(tk.END, "系统: ", "bold")
                self.message_display.insert(tk.END, content + "\n", "system")
            else:
                self.message_display.insert(tk.END, "结果: ", "bold")
                lines = content.split('\n')
                in_code_block = False
                
                for line in lines:
                    if line.startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        self.message_display.insert(tk.END, line + "\n", "code")
                    else:
                        self.message_display.insert(tk.END, line + "\n", "result")
            
            self.message_display.see(tk.END)
            self.message_display.config(state=tk.DISABLED)
        except Exception as e:
            print(f"添加消息时出错: {str(e)}")

    def add_message(self, message_type, content):
        if threading.current_thread() is threading.main_thread():
            self.add_message_safe(message_type, content)
        else:
            self.response_queue.put((message_type, content))

    def send_command(self, command):
        response_event = threading.Event()
        response_data = {"response": None}
        
        def response_callback(response):
            response_data["response"] = response
            response_event.set()
        
        self.command_queue.put((command, response_callback))
        
        if not response_event.wait(10):
            return "错误: 等待响应超时"
        
        return response_data["response"]

    def is_browser_running(self):
        try:
            response = self.send_command("status")
            
            if isinstance(response, str) and response.startswith("错误"):
                return False
                
            try:
                status = json.loads(response)
                if "browser_running" in status:
                    return status["browser_running"]
                elif "browser_started" in status:
                    return status["browser_started"]
                else:
                    return status.get("status") == "success" and status.get("server") == "running"
            except json.JSONDecodeError:
                return "running" in response.lower()
        except Exception as e:
            self.add_message("error", f"检查浏览器状态时出错: {str(e)}")
            return False

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted_message = f"[{timestamp}] {message}"
        
        self.add_message("error" if "错误" in message else "result", formatted_message)
        print(formatted_message)

    def check_browser_status(self):
        try:
            is_running = self.is_browser_running()
            
            self.update_browser_status(connected=is_running)
            
            if not is_running and self.browser_status_label.cget("text") == "浏览器状态: 已连接":
                self._handle_browser_closed()
        except Exception as e:
            self.add_message("error", f"检查浏览器状态时出错: {str(e)}")
        
        self.root.after(5000, self.check_browser_status)

    def update_browser_status(self, connected=None):
        if connected is None:
            try:
                response = self.send_command("status")
                
                if response.startswith("错误"):
                    connected = False
                else:
                    try:
                        status = json.loads(response)
                        connected = status.get("browser_running", False)
                    except json.JSONDecodeError:
                        connected = "running" in response.lower()
            except Exception as e:
                self.add_message("error", f"检查浏览器状态时出错: {str(e)}")
                connected = False
        
        if connected:
            self.browser_status_label.config(text="浏览器状态: 已连接", fg="green")
            self.execute_button.config(state=tk.NORMAL)
        else:
            self.browser_status_label.config(text="浏览器状态: 未连接", fg="red")
            self.execute_button.config(state=tk.DISABLED)
            self.log_message("错误: 无法连接到浏览器，5秒后将重试...")

    def execute_command(self, event=None):
        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.command_entry.delete(0, tk.END)
        self.add_message("command", command)
        
        if not self.is_browser_running() and not command.startswith("!python"):
            self.add_message("error", "浏览器未连接，无法执行浏览器命令")
            return
        
        threading.Thread(target=self._execute_command_thread, args=(command,), daemon=True).start()

    def _execute_command_thread(self, command):
        try:
            if command.startswith("!python "):
                python_code = command[8:].strip()
                result = self._execute_python_code(python_code)
            else:
                result = self.send_command(command)
            
            self.response_queue.put(("result", result))
        except Exception as e:
            self.response_queue.put(("error", str(e)))

    def _execute_python_code(self, code):
        local_ns = {
            "send_command": self.send_command,
            "time": time,
            "os": os,
            "sys": sys,
            "json": json,
            "re": re
        }
        
        import io
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        
        try:
            exec(code, globals(), local_ns)
            output = new_stdout.getvalue()
            return output if output.strip() else "代码执行成功，无输出"
        except Exception as e:
            return f"执行Python代码时出错: {str(e)}"
        finally:
            sys.stdout = old_stdout

    def add_message(self, message_type, content):
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, "\n")
        
        if message_type == "command":
            self.message_display.insert(tk.END, "命令: ", "bold")
            self.message_display.insert(tk.END, content + "\n", "command")
        elif message_type == "error":
            self.message_display.insert(tk.END, "错误: ", "bold")
            self.message_display.insert(tk.END, content + "\n", "error")
        elif message_type == "system":
            self.message_display.insert(tk.END, "系统: ", "bold")
            self.message_display.insert(tk.END, content + "\n", "system")
        else:
            self.message_display.insert(tk.END, "结果: ", "bold")
            lines = content.split('\n')
            in_code_block = False
            
            for line in lines:
                if line.startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    self.message_display.insert(tk.END, line + "\n", "code")
                else:
                    self.message_display.insert(tk.END, line + "\n", "result")
        
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)

    def _handle_browser_closed(self):
        self.browser_status_label.config(
            text="浏览器状态: 已关闭",
            fg="red"
        )
        self.add_message("error", "浏览器已关闭")

    def help(self):
        help_text = """
超级浏览器开发者工具使用说明:

1. 浏览器控制命令:
   - goto?url=网址 - 导航到指定网址
   - click?selector=选择器 - 点击元素
   - fill?selector=选择器&text=文本 - 填充表单
   - getTitle - 获取页面标题
   - getUrl - 获取当前URL
   - getHtml - 获取页面HTML
   - getText?selector=选择器 - 获取元素文本
   - screenshot - 截图

2. Python命令:
   - !python print("Hello World") - 执行Python代码

更多命令请参考文档。
        """
        self.add_message("result", help_text)

    def on_closing(self):
        try:
            self.disconnect()
            print("开发者工具正在关闭...")
            self.root.destroy()
        except Exception as e:
            print(f"关闭窗口时出错: {str(e)}")
            self.root.destroy()

def main():
    root = tk.Tk()
    app = DevToolsUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()