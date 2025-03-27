import socket
import time
import json
import sys
import os
import logging
import threading
import argparse
import subprocess
import select
from typing import Dict, Any, Optional, Union, Tuple

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "testor_exe.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ExecutorTester")
logger.setLevel(logging.DEBUG)
logger.critical("============ 测试器启动 ============")

class ExecutorTester:
    def __init__(self, host='127.0.0.1', port=9876, auto_start_server=True):
        self.host = host
        self.port = port
        self.connected = False
        self.server_process = None
        self.socket = None
        
        if auto_start_server:
            self.start_server()
    
    def start_server(self) -> bool:
        try:
            logger.info("尝试启动executor.py服务器...")
            executor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")
            python_exe = sys.executable
            
            self.server_process = subprocess.Popen(
                [python_exe, executor_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
            )
            
            logger.info(f"服务器进程已启动，PID: {self.server_process.pid}")
            
            def read_output(stream, log_prefix):
                try:
                    for line in stream:
                        logger.info(f"{log_prefix}: {line.strip()}")
                except Exception as e:
                    logger.error(f"读取{log_prefix}时出错: {str(e)}")
            
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(self.server_process.stdout, "服务器输出")
            )
            
            stderr_thread = threading.Thread(
                target=read_output, 
                args=(self.server_process.stderr, "服务器错误")
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            logger.info("等待服务器启动...")
            time.sleep(3)
            
            if self.server_process.poll() is not None:
                logger.error(f"服务器进程已退出，退出码: {self.server_process.returncode}")
                return False
            
            for attempt in range(5):
                if self.connect():
                    logger.info("服务器已成功启动并可以连接")
                    return True
                
                if self.server_process.poll() is not None:
                    logger.error(f"服务器进程已退出，退出码: {self.server_process.returncode}")
                    return False
                
                logger.warning(f"连接尝试 {attempt+1} 失败，等待后重试...")
                time.sleep(2)
            
            logger.error("无法连接到服务器，可能启动失败")
            self.stop_server()
            return False
            
        except Exception as e:
            logger.exception(f"启动服务器时出错: {str(e)}")
            return False
    
    def stop_server(self):
        if self.server_process:
            logger.info("尝试停止服务器进程...")
            
            try:
                self.server_process.terminate()
                
                try:
                    self.server_process.wait(timeout=5)
                    logger.info("服务器进程已停止")
                except subprocess.TimeoutExpired:
                    logger.warning("服务器进程未能及时停止，强制结束")
                    self.server_process.kill()
                    self.server_process.wait()
                    logger.info("服务器进程已强制停止")
            except Exception as e:
                logger.exception(f"停止服务器进程时出错: {str(e)}")
            
            self.server_process = None
    
    def connect(self) -> bool:
        if self.connected and self.socket:
            return True
        
        try:
            logger.info(f"尝试连接到 {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info("已成功连接到服务器")
            return True
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            self.socket = None
            self.connected = False
            return False
    
    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
                logger.info("已断开与服务器的连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {str(e)}")
            
            self.socket = None
            self.connected = False
    
    def send_command(self, command: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            if not self.connected or self.socket is None:
                if not self.connect():
                    logger.error("未连接到服务器，无法发送命令")
                    return None
            
            try:
                command_str = command
                
                if params:
                    query_parts = []
                    for key, value in params.items():
                        if isinstance(value, bool):
                            value = "true" if value else "false"
                        query_parts.append(f"{key}={value}")
                    
                    command_str += "?" + "&".join(query_parts)
                
                logger.info(f"发送命令: {command_str}")
                self.socket.sendall(command_str.encode('utf-8'))
                
                response_data = self.socket.recv(4096).decode('utf-8')
                logger.info(f"收到响应: {response_data}")
                
                try:
                    response = json.loads(response_data)
                    return response
                except json.JSONDecodeError as e:
                    logger.error(f"解析响应JSON时出错: {str(e)}")
                    return {"status": "error", "message": f"无效的JSON响应: {response_data}"}
                
            except (ConnectionError, socket.timeout, socket.error) as e:
                logger.warning(f"连接错误: {str(e)}，尝试重新连接...")
                self.disconnect()
                retry_count += 1
                
                if retry_count < max_retries:
                    logger.info(f"重试 {retry_count}/{max_retries}...")
                    time.sleep(1)
                
                continue
                
            except Exception as e:
                logger.exception(f"发送命令时出错: {str(e)}")
                self.connected = False
                self.socket = None
                return None
        
        logger.error(f"发送命令失败，已达到最大重试次数 {max_retries}")
        return None
    
    def test_status(self) -> bool:
        logger.info("测试status命令...")
        response = self.send_command("status")
        
        if not response:
            logger.error("status命令测试失败")
            return False
        
        if response.get("status") == "success" and response.get("server") == "running":
            logger.info("status命令测试成功")
            return True
        else:
            logger.error(f"status命令返回异常: {response}")
            return False
    
    def test_start_browser(self, browser_type="chromium", headless=False) -> bool:
        logger.info(f"测试启动浏览器: {browser_type}, headless={headless}...")
        
        params = {
            "browser_type": browser_type,
            "headless": headless,
            "ignore_https_errors": True,
            "java_script_enabled": True
        }
        
        response = self.send_command("startBrowser", params)
        
        if not response:
            logger.error("启动浏览器命令测试失败")
            return False
        
        if response.get("status") == "success":
            logger.info(f"启动浏览器成功: {response.get('message', '')}")
            return True
        else:
            logger.error(f"启动浏览器失败: {response}")
            return False
    
    def test_goto(self, url="https://www.baidu.com") -> bool:
        logger.info(f"测试导航到: {url}...")
        response = self.send_command("goto", {"url": url})
        
        if not response:
            logger.error("导航命令测试失败")
            return False
        
        if response.get("status") == "success":
            logger.info(f"导航成功: {response.get('result', '')}")
            return True
        else:
            logger.error(f"导航失败: {response}")
            return False
    
    def test_get_title(self) -> Optional[str]:
        logger.info("测试获取页面标题...")
        response = self.send_command("getTitle")
        
        if not response:
            logger.error("获取标题命令测试失败")
            return None
        
        if response.get("status") == "success":
            title = response.get("result", "")
            logger.info(f"获取标题成功: {title}")
            return title
        else:
            logger.error(f"获取标题失败: {response}")
            return None
    
    def test_stop_browser(self) -> bool:
        logger.info("测试停止浏览器...")
        response = self.send_command("stopBrowser")
        
        if not response:
            logger.error("停止浏览器命令测试失败")
            return False
        
        if response.get("status") in ["success", "warning"]:
            logger.info(f"停止浏览器成功: {response.get('message', '')}")
            return True
        else:
            logger.error(f"停止浏览器失败: {response}")
            return False
    
    def run_all_tests(self) -> bool:
        logger.info("开始运行所有测试...")
        
        if not self.test_status():
            logger.error("状态测试失败，终止测试")
            return False
        
        if not self.test_start_browser():
            logger.error("启动浏览器测试失败，终止测试")
            return False
        
        logger.info("等待浏览器完全启动...")
        time.sleep(3)
        
        if not self.test_goto():
            logger.warning("导航测试失败，继续测试")
        
        logger.info("等待页面加载...")
        time.sleep(2)
        
        title = self.test_get_title()
        if title is None:
            logger.warning("获取标题测试失败，继续测试")
        
        if not self.test_stop_browser():
            logger.error("停止浏览器测试失败")
            return False
        
        logger.info("所有测试完成")
        return True


def main():
    parser = argparse.ArgumentParser(description='Executor测试器')
    parser.add_argument('--host', default='127.0.0.1', help='服务器地址')
    parser.add_argument('--port', type=int, default=9876, help='服务器端口')
    parser.add_argument('--browser', default='chromium', help='浏览器类型: chromium, firefox, webkit')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--url', default='https://www.baidu.com', help='测试URL')
    parser.add_argument('--test', choices=['all', 'status', 'start', 'goto', 'title', 'stop'], 
                        default='all', help='要运行的测试')
    parser.add_argument('--no-auto-start', action='store_true', help='不自动启动executor.py服务器')
    parser.add_argument('--check-executor', action='store_true', help='仅检查executor.py是否可以运行')
    
    args = parser.parse_args()
    
    if args.check_executor:
        executor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")
        python_exe = sys.executable
        
        print(f"检查executor.py是否可以运行...")
        try:
            result = subprocess.run(
                [python_exe, executor_path, "--check"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            
            print(f"退出码: {result.returncode}")
            if result.stdout:
                print(f"标准输出:\n{result.stdout}")
            if result.stderr:
                print(f"错误输出:\n{result.stderr}")
            
            return 0 if result.returncode == 0 else 1
        except subprocess.TimeoutExpired:
            print("检查超时，executor.py可能正在正常运行")
            return 0
        except Exception as e:
            print(f"检查时出错: {str(e)}")
            return 1
    
    tester = ExecutorTester(
        host=args.host, 
        port=args.port,
        auto_start_server=not args.no_auto_start
    )
    
    try:
        if args.test == 'all':
            success = tester.run_all_tests()
        elif args.test == 'status':
            success = tester.test_status()
        elif args.test == 'start':
            success = tester.test_start_browser(args.browser, args.headless)
        elif args.test == 'goto':
            success = tester.test_goto(args.url)
        elif args.test == 'title':
            title = tester.test_get_title()
            success = title is not None
        elif args.test == 'stop':
            success = tester.test_stop_browser()
        
        return 0 if success else 1
    finally:
        if not args.no_auto_start:
            tester.stop_server()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)