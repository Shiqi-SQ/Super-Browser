import socket
import threading
import json
import urllib.parse
import time
import sys
import os
import logging
import argparse
from typing import Dict, Any, Tuple, Optional

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "executor.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CommandExecutor")
logger.setLevel(logging.DEBUG)
logger.critical("============ 执行器启动 ============")

try:
    from browser import BrowserController
    logger.info("成功导入BrowserController")
except ImportError as e:
    logger.error(f"导入BrowserController失败: {str(e)}")
    logger.warning("将使用模拟的BrowserController")
    
    class BrowserController:
        def __init__(self):
            self.browser = None
            self.page = None
            self.running = False
        
        def start_browser(self, browser_type=None, headless=False, 
                         ignore_https_errors=True, java_script_enabled=True):
            logger.info(f"模拟启动浏览器: {browser_type}, headless={headless}")
            self.running = True
            return f"已启动 {browser_type} 浏览器"
        
        def stop_browser(self):
            logger.info("模拟停止浏览器")
            self.running = False
            return "浏览器已停止"
        
        def goto(self, url):
            logger.info(f"模拟导航到: {url}")
            return f"已导航到 {url}"
        
        def get_title(self):
            logger.info("模拟获取标题")
            return "页面标题"
        
        def get_browser_info(self):
            return {
                "browser_type": "chromium",
                "headless": False,
                "pages_count": 1
            }

class CommandExecutor:
    def __init__(self, host='127.0.0.1', port=9876):
        self.host = host
        self.port = port
        self.browser_controller = BrowserController()
        self.server_socket = None
        self.running = False
        self.browser_started = False
        self.command_map = {
            "startBrowser": self.start_browser,
            "stopBrowser": self.stop_browser,
            "status": self.get_status,
        }
        self._add_browser_methods()
    
    def _add_browser_methods(self):
        self._try_add_method("click")
        self._try_add_method("fill")
        self._try_add_method("type", "type_text")
        self._try_add_method("hover")
        self._try_add_method("select", "select_option")
        self._try_add_method("check")
        self._try_add_method("uncheck")
        self._try_add_method("upload", "upload_file")
        self._try_add_method("getTitle", "get_title")
        self._try_add_method("getUrl", "get_url")
        self._try_add_method("getHtml", "get_html")
        self._try_add_method("getText", "get_text")
        self._try_add_method("getAttribute", "get_attribute")
        self._try_add_method("getElements", "get_elements")
        self._try_add_method("evaluate")
        self._try_add_method("addScriptTag", "add_script_tag")
        self._try_add_method("addStyleTag", "add_style_tag")
        self._try_add_method("getResponseBody", "get_response_body")
        self._try_add_method("getCookies", "get_cookies")
        self._try_add_method("getLocalStorage", "get_local_storage")
        self._try_add_method("goto")
        self._try_add_method("reload")
        self._try_add_method("goBack", "go_back")
        self._try_add_method("goForward", "go_forward")
        self._try_add_method("newPage", "new_page")
        self._try_add_method("closePage", "close_page")
        self._try_add_method("switchPage", "switch_page")
        self._try_add_method("getPages", "get_pages")
        self._try_add_method("screenshot")
        self._try_add_method("pdf")
        self._try_add_method("setCookies", "set_cookies")
        self._try_add_method("clearCookies", "clear_cookies")
        self._try_add_method("setLocalStorageItem", "set_local_storage_item")
        self._try_add_method("removeLocalStorageItem", "remove_local_storage_item")
        self._try_add_method("clearLocalStorage", "clear_local_storage")
        
        logger.info(f"已添加 {len(self.command_map) - 3} 个浏览器控制方法到命令映射表")
    
    def _try_add_method(self, command_name, method_name=None):
        if method_name is None:
            method_name = command_name
            
        if hasattr(self.browser_controller, method_name):
            self.command_map[command_name] = getattr(self.browser_controller, method_name)
            logger.debug(f"已添加命令 {command_name} -> {method_name}")
        else:
            logger.warning(f"浏览器控制器中不存在方法 {method_name}，跳过添加命令 {command_name}")
    
    def parse_command(self, command_str: str) -> Tuple[str, Dict[str, Any]]:
        logger.debug(f"解析命令字符串: {command_str}")
        parts = command_str.split('?', 1)
        command = parts[0]
        params = {}
        
        if len(parts) > 1:
            query_string = parts[1]
            parsed_params = urllib.parse.parse_qs(query_string)
            for key, values in parsed_params.items():
                params[key] = values[0] if len(values) == 1 else values
                
        logger.debug(f"解析结果: 命令={command}, 参数={params}")
        return command, params
    
    def _convert_param_type(self, key: str, value: str) -> Any:
        if value in ["true", "True", "1", "yes", "Yes"]:
            return True
            
        if value in ["false", "False", "0", "no", "No"]:
            return False
            
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value
    
    def execute_command(self, client_socket, client_address, command_str):
        try:
            command, params = self.parse_command(command_str)
            logger.info(f"解析命令: {command}, 参数: {params}")
            command_func = self.get_command_function(command)
            
            if command_func:
                logger.info(f"执行命令函数: {command_func.__name__}")
                result = command_func(params)
                logger.info(f"命令执行结果: {result}")
                
                if isinstance(result, dict):
                    result_str = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, (list, tuple)):
                    result_str = json.dumps(result, ensure_ascii=False)
                else:
                    result_str = str(result)
                
                if (isinstance(result_str, str) and 
                    result_str.startswith('[') and result_str.endswith(']')):
                    response = result_str
                else:
                    if isinstance(result, dict) and "status" in result:
                        response = result_str
                    else:
                        response = json.dumps({
                            "status": "success",
                            "message": result_str
                        }, ensure_ascii=False)
            else:
                logger.warning(f"未知命令: {command}")
                response = json.dumps({
                    "status": "error",
                    "message": f"未知指令 '{command}'"
                }, ensure_ascii=False)
                
            client_socket.sendall(response.encode('utf-8'))
            logger.info(f"已发送响应到客户端 {client_address}: {response}")
            
        except Exception as e:
            logger.error(f"执行命令时出错: {str(e)}")
            logger.error(traceback.format_exc())
            
            error_response = json.dumps({
                "status": "error",
                "message": f"执行命令时出错: {str(e)}"
            }, ensure_ascii=False)
            
            try:
                client_socket.sendall(error_response.encode('utf-8'))
                logger.info(f"已发送响应到客户端 {client_address}: {error_response}")
            except:
                logger.error(f"发送错误响应失败")
    
    def start_browser(self, browser_type: str = "chromium", headless: bool = False, 
                     ignore_https_errors: bool = True, java_script_enabled: bool = True, **kwargs) -> str:
        try:
            logger.info(f"启动浏览器参数: browser_type={browser_type}, headless={headless}, "
                        f"ignore_https_errors={ignore_https_errors}, java_script_enabled={java_script_enabled}")
            logger.info("调用browser_controller.start_browser...")
            
            result = self.browser_controller.start_browser(
                browser_type=browser_type,
                headless=headless,
                ignore_https_errors=ignore_https_errors,
                java_script_enabled=java_script_enabled
            )
            
            self.browser_started = True
            logger.info(f"浏览器启动成功: {browser_type}, 结果: {result}")
            
            return json.dumps({
                "status": "success",
                "message": f"已成功启动{browser_type}浏览器"
            })
            
        except Exception as e:
            logger.exception(f"启动浏览器失败: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"启动浏览器失败: {str(e)}"
            })
    
    def stop_browser(self, **kwargs) -> str:
        try:
            if not self.browser_started:
                logger.warning("浏览器未启动，无需停止")
                return json.dumps({
                    "status": "warning",
                    "message": "浏览器未启动，无需停止"
                })
                
            logger.info("停止浏览器...")
            result = self.browser_controller.stop_browser()
            self.browser_started = False
            logger.info("浏览器已停止")
            
            return json.dumps({
                "status": "success",
                "message": "浏览器已成功停止"
            })
            
        except Exception as e:
            logger.exception(f"停止浏览器失败: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"停止浏览器失败: {str(e)}"
            })
    
    def get_status(self, params=None):
        try:
            status = {
                "status": "success",
                "server": "running",
                "browser_started": self.browser_started,
                "timestamp": time.time()
            }
            
            try:
                if self.browser_started and hasattr(self.browser_controller, "browser") and self.browser_controller.browser:
                    status["browser_type"] = getattr(self.browser_controller, "browser_type", "unknown")
                    status["browser_running"] = True
                else:
                    status["browser_running"] = False
            except Exception as e:
                logger.error(f"获取浏览器信息失败: {str(e)}")
                status["browser_error"] = str(e)
                
            return status
            
        except Exception as e:
            logger.error(f"获取状态信息失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取状态信息失败: {str(e)}"
            }
    
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            if hasattr(socket, 'TCP_KEEPINTVL'):
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, 'TCP_KEEPCNT'):
                self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"服务器已启动，监听 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"接受客户端连接: {client_address}")
                    
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    if hasattr(socket, 'TCP_KEEPIDLE'):
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                    if hasattr(socket, 'TCP_KEEPINTVL'):
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                    if hasattr(socket, 'TCP_KEEPCNT'):
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                        
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"接受客户端连接时出错: {str(e)}")
                    
        except Exception as e:
            logger.error(f"启动服务器时出错: {str(e)}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            logger.info("服务器已关闭")
    
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("服务器已停止")
    
    def handle_client(self, client_socket, client_address):
        try:
            client_socket.settimeout(60)
            
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    
                    if not data:
                        logger.info(f"客户端 {client_address} 断开连接")
                        break
                        
                    command_str = data.decode('utf-8')
                    logger.info(f"收到来自 {client_address} 的命令: {command_str}")
                    self.execute_command(client_socket, client_address, command_str)
                    
                except socket.timeout:
                    logger.debug(f"客户端 {client_address} 连接超时")
                    continue
                except ConnectionResetError:
                    logger.info(f"客户端 {client_address} 重置连接")
                    break
                except Exception as e:
                    logger.error(f"处理客户端 {client_address} 请求时出错: {str(e)}")
                    break
                    
        finally:
            try:
                client_socket.close()
                logger.info(f"客户端 {client_address} 连接已关闭")
            except:
                pass
    
    def get_command_function(self, command_name):
        if command_name in self.command_map:
            return self.command_map[command_name]
        return None

def main():
    parser = argparse.ArgumentParser(description='命令执行器服务')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    parser.add_argument('--port', type=int, default=9876, help='监听端口')
    
    args = parser.parse_args()
    executor = CommandExecutor(host=args.host, port=args.port)
    
    try:
        executor.start_server()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在停止服务器...")
        executor.stop_server()
    except Exception as e:
        logger.error(f"服务器运行时出错: {str(e)}")
        executor.stop_server()

if __name__ == "__main__":
    main()