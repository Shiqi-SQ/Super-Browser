import os
import sys
import time
import argparse
from browser import BrowserController

def test_browser_start(browser_type="chromium", headless=False, debug=False):
    print(f"=== 浏览器启动测试 ===")
    print(f"浏览器类型: {browser_type}")
    print(f"无头模式: {headless}")
    print(f"调试模式: {debug}")
    
    browser_controller = BrowserController()
    
    if debug:
        print("\n初始浏览器配置:")
        print(f"browser_options: {browser_controller.browser_options}")
        print(f"context_options: {browser_controller.context_options}")
    
    try:
        print("\n正在启动浏览器...")
        result = browser_controller.start_browser(
            browser_type=browser_type,
            headless=headless
        )
        
        print(f"启动结果: {result}")
        
        if browser_controller.running:
            print("浏览器成功启动!")
            
            if debug:
                print("\n执行测试操作...")
                try:
                    nav_result = browser_controller.goto("https://www.baidu.com")
                    print(f"导航结果: {nav_result}")
                    
                    title_result = browser_controller.get_title()
                    print(f"页面标题: {title_result}")
                    
                    time.sleep(2)
                except Exception as e:
                    print(f"执行测试操作时出错: {str(e)}")
            
            input("\n按Enter键关闭浏览器...")
            
            stop_result = browser_controller.stop_browser()
            print(f"关闭结果: {stop_result}")
        else:
            print("浏览器未成功启动!")
    
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        
        if debug:
            import traceback
            print("\n详细错误信息:")
            traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="浏览器启动测试工具")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], 
                        default="chromium", help="浏览器类型")
    parser.add_argument("--headless", type=str, default="false", 
                        help="无头模式 (true/false)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    if args.headless.lower() in ("true", "1", "yes"):
        headless = True
    else:
        headless = False
    
    test_browser_start(args.browser, headless, args.debug)

if __name__ == "__main__":
    main()