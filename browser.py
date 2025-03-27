import os
import time
import datetime
import threading
import queue
from typing import Dict, List, Any, Optional, Union, Callable
import json
import re
import urllib.parse
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, ElementHandle, Response, Request, Route, ConsoleMessage, Dialog, Download, FileChooser, Frame, JSHandle, Locator, WebSocket, Playwright

_browser_controller_instance = None

class BrowserController:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.browser_thread = None
        self.running = False
        self.current_page_index = 0
        self.pages = []
        self.browser_type = "chromium"
        self.browser_options = {
            "headless": False,
            "slow_mo": 50,
        }
        self.context_options = {
            "viewport": {"width": 1280, "height": 800},
            "ignore_https_errors": True,
            "java_script_enabled": True,
        }
        self.event_listeners = {
            "browser_closed": [],
        }
        self._trigger_event_called = False

    # 事件监听
    def add_event_listener(self, event_name: str, callback: Callable):
        if event_name in self.event_listeners:
            self.event_listeners[event_name].append(callback)
            return True
        return False

    def remove_event_listener(self, event_name: str, callback: Callable):
        if event_name in self.event_listeners and callback in self.event_listeners[event_name]:
            self.event_listeners[event_name].remove(callback)
            return True
        return False

    def _trigger_event(self, event_name: str, *args, **kwargs):
        self._trigger_event_called = True
        
        if event_name in self.event_listeners:
            for callback in self.event_listeners[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"事件回调执行出错: {str(e)}")

    def start_browser(self, browser_type=None, **kwargs):
        bool_params = ["headless", "ignore_https_errors", "java_script_enabled"]
        
        for param in bool_params:
            if param in kwargs and isinstance(kwargs[param], str):
                kwargs[param] = kwargs[param].lower() in ("true", "1", "yes")
        
        if self.running:
            return "浏览器已经在运行"
        
        if browser_type:
            self.browser_type = browser_type
        
        for key, value in kwargs.items():
            if key in self.browser_options:
                self.browser_options[key] = value
            elif key in self.context_options:
                self.context_options[key] = value
        
        self.browser_thread = threading.Thread(target=self._browser_thread_func)
        self.running = True
        self.browser_thread.start()
        
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.browser and self.page:
                return f"已启动 {self.browser_type} 浏览器"
            time.sleep(0.1)
        
        self.running = False
        
        if self.browser_thread.is_alive():
            self.browser_thread.join(timeout=1)
        
        return "启动浏览器超时"

    def _browser_thread_func(self):
        try:
            self.playwright = sync_playwright().start()
            
            if self.browser_type == "firefox":
                browser_instance = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_instance = self.playwright.webkit
            else:
                browser_instance = self.playwright.chromium
            
            self.browser = browser_instance.launch(**self.browser_options)
            self.context = self.browser.new_context(**self.context_options)
            self.page = self.context.new_page()
            self.pages = [self.page]
            self.current_page_index = 0
            
            self._setup_page_listeners(self.page)
            self.page.goto("about:blank")
            self.result_queue.put(True)
            
            while self.running:
                try:
                    command, args, kwargs = self.command_queue.get(timeout=0.1)
                    
                    try:
                        result = command(*args, **kwargs)
                        self.result_queue.put(result)
                    except Exception as e:
                        self.result_queue.put(e)
                except queue.Empty:
                    if self.browser and not self.browser.is_connected():
                        print("检测到浏览器已被关闭")
                        self.running = False
                        self._trigger_event("browser_closed")
                    continue
        except Exception as e:
            self.result_queue.put(e)
        finally:
            try:
                if self.context:
                    self.context.close()
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
            except:
                pass
            
            if not self._trigger_event_called:
                self._trigger_event("browser_closed")

    def _setup_page_listeners(self, page):
        page.on("console", lambda msg: print(f"控制台 [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"页面错误: {err}"))
        page.on("dialog", lambda dialog: dialog.accept())
        page.on("download", lambda download: print(f"下载文件: {download.suggested_filename}"))
        page.on("filechooser", lambda chooser: print("文件选择器已打开"))

    def stop_browser(self):
        if not self.browser_thread or not self.browser_thread.is_alive():
            return "浏览器未启动"
        
        self.running = False
        self.browser_thread.join(timeout=5)
        
        if self.browser_thread.is_alive():
            return "浏览器停止超时"
        
        return "浏览器已停止"

    def execute_command(self, command_func, *args, **kwargs):
        if not self.running:
            raise RuntimeError("浏览器未启动")
        
        self.command_queue.put((command_func, args, kwargs))
        result = self.result_queue.get()
        
        if isinstance(result, Exception):
            raise result
        
        return result

    def click(self, selector: str) -> str:
        return self.execute_command(
            lambda: (self.page.click(selector), f"已点击元素: {selector}")[1]
        )

    def fill(self, selector: str, value: str) -> str:
        return self.execute_command(
            lambda: (self.page.fill(selector, value), f"已在元素 {selector} 中填入值: {value}")[1]
        )

    def type_text(self, selector: str, text: str, delay: int = 0) -> str:
        delay_ms = int(delay) if delay else 0
        
        return self.execute_command(
            lambda: (self.page.type(selector, text, delay=delay_ms), 
                    f"已在元素 {selector} 中输入文本: {text}")[1]
        )

    def hover(self, selector: str) -> str:
        return self.execute_command(
            lambda: (self.page.hover(selector), f"已将鼠标悬停在元素: {selector}")[1]
        )

    def select_option(self, selector: str, value: str) -> str:
        return self.execute_command(
            lambda: (self.page.select_option(selector, value=value), 
                    f"已在下拉菜单 {selector} 中选择选项: {value}")[1]
        )

    def check(self, selector: str) -> str:
        return self.execute_command(
            lambda: (self.page.check(selector), f"已勾选复选框: {selector}")[1]
        )

    def uncheck(self, selector: str) -> str:
        return self.execute_command(
            lambda: (self.page.uncheck(selector), f"已取消勾选复选框: {selector}")[1]
        )

    def upload_file(self, selector: str, path: str) -> str:
        return self.execute_command(
            lambda: (self.page.set_input_files(selector, path), 
                    f"已上传文件 {path} 到元素: {selector}")[1]
        )

    def get_title(self) -> str:
        return self.execute_command(
            lambda: f"页面标题: {self.page.title()}"
        )

    def get_url(self) -> str:
        return self.execute_command(
            lambda: f"页面URL: {self.page.url}"
        )

    def get_html(self) -> str:
        return self.execute_command(
            lambda: f"页面HTML: {self.page.content()}"
        )

    def get_text(self, selector: str) -> str:
        return self.execute_command(
            lambda: f"元素 {selector} 的文本内容: {self.page.text_content(selector)}"
        )

    def get_attribute(self, selector: str, name: str) -> str:
        return self.execute_command(
            lambda: f"元素 {selector} 的 {name} 属性值: {self.page.get_attribute(selector, name)}"
        )

    def get_elements(self, selector: str) -> str:
        return self.execute_command(
            lambda: self._get_elements_info(selector)
        )

    def _get_elements_info(self, selector: str) -> str:
        elements = self.page.query_selector_all(selector)
        count = len(elements)
        
        if count == 0:
            return f"未找到匹配选择器 {selector} 的元素"
        
        result = f"找到 {count} 个匹配选择器 {selector} 的元素:\n"
        
        for i, element in enumerate(elements[:10]):  # 限制显示前10个
            tag_name = self.page.evaluate("el => el.tagName", element).lower()
            text = self.page.evaluate("el => el.textContent", element)
            text = text.strip() if text else ""
            text_preview = text[:50] + "..." if len(text) > 50 else text
            result += f"{i+1}. <{tag_name}> {text_preview}\n"
        
        if count > 10:
            result += f"... 还有 {count - 10} 个元素未显示"
        
        return result

    def evaluate(self, expression: str) -> str:
        return self.execute_command(
            lambda: f"JavaScript执行结果: {self.page.evaluate(expression)}"
        )

    def add_script_tag(self, url: str = None, content: str = None) -> str:
        if not url and not content:
            return "错误: 必须提供url或content参数"
        
        params = {}
        if url:
            params["url"] = url
        if content:
            params["content"] = content
        
        return self.execute_command(
            lambda: (self.page.add_script_tag(**params), 
                    f"已添加脚本: {url if url else '内联脚本'}" )[1]
        )

    def add_style_tag(self, url: str = None, content: str = None) -> str:
        if not url and not content:
            return "错误: 必须提供url或content参数"
        
        params = {}
        if url:
            params["url"] = url
        if content:
            params["content"] = content
        
        return self.execute_command(
            lambda: (self.page.add_style_tag(**params), 
                    f"已添加样式: {url if url else '内联样式'}" )[1]
        )

    def get_response_body(self) -> str:
        return self.execute_command(
            lambda: "此功能需要在导航时设置拦截器，当前不支持直接获取"
        )

    def get_cookies(self) -> str:
        return self.execute_command(
            lambda: self._format_cookies(self.context.cookies())
        )

    def _format_cookies(self, cookies: List[Dict]) -> str:
        if not cookies:
            return "没有Cookie"
        
        result = f"找到 {len(cookies)} 个Cookie:\n"
        
        for i, cookie in enumerate(cookies):
            result += f"{i+1}. {cookie['name']} = {cookie['value']} (域: {cookie['domain']})\n"
        
        return result

    def get_local_storage(self) -> str:
        return self.execute_command(
            lambda: self._format_storage(self.page.evaluate("() => Object.entries(localStorage)"))
        )

    def _format_storage(self, items: List) -> str:
        if not items:
            return "localStorage为空"
        
        result = f"找到 {len(items)} 个localStorage项:\n"
        
        for i, (key, value) in enumerate(items):
            value_preview = value[:50] + "..." if len(value) > 50 else value
            result += f"{i+1}. {key} = {value_preview}\n"
        
        return result

    def goto(self, url: str, waitUntil: str = "load") -> str:
        return self.execute_command(
            lambda: (self.page.goto(url, wait_until=waitUntil), 
                    f"已导航到: {self.page.url}")[1]
        )

    def reload(self) -> str:
        return self.execute_command(
            lambda: (self.page.reload(), f"已刷新页面: {self.page.url}")[1]
        )

    def go_back(self) -> str:
        return self.execute_command(
            lambda: (self.page.go_back(), f"已返回上一页: {self.page.url}")[1]
        )

    def go_forward(self) -> str:
        return self.execute_command(
            lambda: (self.page.go_forward(), f"已前进到下一页: {self.page.url}")[1]
        )

    def new_page(self) -> str:
        return self.execute_command(
            lambda: self._create_new_page()
        )
    
    def _create_new_page(self) -> str:
        page = self.context.new_page()
        page.goto("about:blank")
        self._setup_page_listeners(page)
        self.pages.append(page)
        self.current_page_index = len(self.pages) - 1
        self.page = page
        
        return f"已创建新标签页，当前共有 {len(self.pages)} 个标签页，当前标签页索引: {self.current_page_index}"

    def close_page(self, index: int = None) -> str:
        return self.execute_command(
            lambda: self._close_page(index)
        )

    def _close_page(self, index: int = None) -> str:
        if len(self.pages) <= 1:
            return "无法关闭，至少需要保留一个标签页"
        
        idx = self.current_page_index if index is None else int(index)
        
        if idx < 0 or idx >= len(self.pages):
            return f"错误: 标签页索引 {idx} 超出范围 (0-{len(self.pages)-1})"
        
        page_to_close = self.pages[idx]
        page_to_close.close()
        self.pages.pop(idx)
        
        if idx == self.current_page_index:
            self.current_page_index = max(0, idx - 1)
        elif idx < self.current_page_index:
            self.current_page_index -= 1
        
        self.page = self.pages[self.current_page_index]
        
        return f"已关闭标签页 {idx}，当前共有 {len(self.pages)} 个标签页，当前标签页索引: {self.current_page_index}"

    def switch_page(self, index: int) -> str:
        return self.execute_command(
            lambda: self._switch_page(index)
        )

    def _switch_page(self, index: int) -> str:
        idx = int(index)
        
        if idx < 0 or idx >= len(self.pages):
            return f"错误: 标签页索引 {idx} 超出范围 (0-{len(self.pages)-1})"
        
        self.current_page_index = idx
        self.page = self.pages[idx]
        
        return f"已切换到标签页 {idx}，URL: {self.page.url}"

    def get_pages(self) -> str:
        return self.execute_command(
            lambda: self._get_pages_info()
        )

    def _get_pages_info(self) -> str:
        result = f"共有 {len(self.pages)} 个标签页，当前标签页索引: {self.current_page_index}\n"
        
        for i, page in enumerate(self.pages):
            title = page.title() or "无标题"
            url = page.url
            current = " (当前)" if i == self.current_page_index else ""
            result += f"{i}. {title} - {url}{current}\n"
        
        return result

    def screenshot(self, path: str = None, fullPage: bool = False, selector: str = None) -> str:
        return self.execute_command(
            lambda: self._take_screenshot(path, fullPage, selector)
        )

    def _take_screenshot(self, path: str = None, fullPage: bool = False, selector: str = None) -> str:
        options = {"full_page": bool(fullPage) if fullPage is not None else False}
        
        if not path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshot_{timestamp}.png"
        
        os.makedirs(os.path.dirname(os.path.abspath(path)) if os.path.dirname(path) else ".", exist_ok=True)
        
        if selector:
            element = self.page.query_selector(selector)
            if not element:
                return f"错误: 未找到元素 {selector}"
            element.screenshot(path=path)
            return f"已截取元素 {selector} 的截图并保存到: {path}"
        else:
            self.page.screenshot(path=path, **options)
            return f"已截取{'整个' if options['full_page'] else '可视区域'}页面截图并保存到: {path}"

    def pdf(self, path: str = None, landscape: bool = False) -> str:
        return self.execute_command(
            lambda: self._save_pdf(path, landscape)
        )

    def _save_pdf(self, path: str = None, landscape: bool = False) -> str:
        if not path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"page_{timestamp}.pdf"
        
        os.makedirs(os.path.dirname(os.path.abspath(path)) if os.path.dirname(path) else ".", exist_ok=True)
        
        try:
            self.page.pdf(path=path, landscape=bool(landscape) if landscape is not None else False)
            return f"已将页面保存为PDF: {path}"
        except Exception as e:
            return f"保存PDF失败: {str(e)}（注意：PDF功能仅在Chromium的headless模式下可用）"

    def set_cookies(self, cookies: str) -> str:
        return self.execute_command(
            lambda: self._set_cookies(cookies)
        )

    def _set_cookies(self, cookies_str: str) -> str:
        try:
            cookies_list = json.loads(cookies_str)
            
            if not isinstance(cookies_list, list):
                return "错误: cookies参数必须是JSON格式的Cookie列表"
            
            self.context.add_cookies(cookies_list)
            return f"已成功设置 {len(cookies_list)} 个Cookie"
        except json.JSONDecodeError:
            return "错误: cookies参数不是有效的JSON格式"
        except Exception as e:
            return f"设置Cookie失败: {str(e)}"

    def clear_cookies(self) -> str:
        return self.execute_command(
            lambda: (self.context.clear_cookies(), "已清除所有Cookie")[1]
        )

    def set_local_storage_item(self, key: str, value: str) -> str:
        return self.execute_command(
            lambda: (self.page.evaluate(f"localStorage.setItem('{key}', '{value}')"), 
                    f"已设置localStorage项: {key} = {value}")[1]
        )

    def clear_local_storage(self) -> str:
        return self.execute_command(
            lambda: (self.page.evaluate("localStorage.clear()"), "已清除所有localStorage内容")[1]
        )

    def wait_for_url(self, url: str, timeout: int = 30000) -> str:
        return self.execute_command(
            lambda: (self.page.wait_for_url(url, timeout=timeout), 
                    f"页面URL已变为: {self.page.url}")[1]
        )

    def wait_for_selector(self, selector: str, timeout: int = 30000, state: str = "visible") -> str:
        return self.execute_command(
            lambda: (self.page.wait_for_selector(selector, timeout=timeout, state=state), 
                    f"元素 {selector} 已" + {'visible': '可见', 'attached': '附加', 'detached': '分离', 'hidden': '隐藏'}[state])[1]
        )

    def wait_for_load_state(self, state: str = "load") -> str:
        return self.execute_command(
            lambda: (self.page.wait_for_load_state(state), 
                    f"页面已达到 {state} 加载状态")[1]
        )

    def press(self, selector: str, key: str) -> str:
        return self.execute_command(
            lambda: (self.page.press(selector, key), 
                    f"已在元素 {selector} 上按下 {key} 键")[1]
        )

    def keyboard_press(self, key: str) -> str:
        return self.execute_command(
            lambda: (self.page.keyboard.press(key), 
                    f"已按下 {key} 键")[1]
        )

    def keyboard_type(self, text: str, delay: int = 0) -> str:
        delay_ms = int(delay) if delay else 0
        
        return self.execute_command(
            lambda: (self.page.keyboard.type(text, delay=delay_ms), 
                    f"已输入文本: {text}")[1]
        )

    def mouse_click(self, x: int, y: int, button: str = "left") -> str:
        return self.execute_command(
            lambda: (self.page.mouse.click(x, y, button=button), 
                    f"已在坐标 ({x}, {y}) 点击" + {'left': '左键', 'right': '右键', 'middle': '中键'}[button])[1]
        )

    def set_viewport_size(self, width: int, height: int) -> str:
        return self.execute_command(
            lambda: (self.page.set_viewport_size({"width": int(width), "height": int(height)}), 
                    f"已设置视口大小为 {width}x{height}")[1]
        )

    def set_extra_http_headers(self, headers: str) -> str:
        return self.execute_command(
            lambda: self._set_extra_headers(headers)
        )

    def _set_extra_headers(self, headers_str: str) -> str:
        try:
            headers_dict = json.loads(headers_str)
            
            if not isinstance(headers_dict, dict):
                return "错误: headers参数必须是JSON格式的对象"
            
            self.page.set_extra_http_headers(headers_dict)
            return f"已成功设置 {len(headers_dict)} 个HTTP请求头"
        except json.JSONDecodeError:
            return "错误: headers参数不是有效的JSON格式"
        except Exception as e:
            return f"设置HTTP请求头失败: {str(e)}"

    def set_geolocation(self, latitude: float, longitude: float) -> str:
        return self.execute_command(
            lambda: (self.context.grant_permissions(["geolocation"]), 
                    self.context.set_geolocation({"latitude": float(latitude), "longitude": float(longitude)}), 
                    f"已设置地理位置为: 纬度 {latitude}, 经度 {longitude}")[2]
        )

    def set_user_agent(self, userAgent: str) -> str:
        return self.execute_command(
            lambda: (self.page.set_extra_http_headers({"User-Agent": userAgent}), 
                    f"已设置用户代理为: {userAgent}")[1]
        )

    def run_js_file(self, path: str) -> str:
        return self.execute_command(
            lambda: self._run_js_file(path)
        )

    def _run_js_file(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                js_code = file.read()
            
            result = self.page.evaluate(js_code)
            return f"已执行JavaScript文件: {path}, 结果: {result}"
        except FileNotFoundError:
            return f"错误: 找不到文件 {path}"
        except Exception as e:
            return f"执行JavaScript文件时出错: {str(e)}"