# 超级浏览器 (Super Browser)
![超级浏览器](https://img.shields.io/badge/超级浏览器-v0.7-blue)
![Python](https://img.shields.io/badge/Python-3.9x-green)
![Playwright](https://img.shields.io/badge/Playwright-1.51.0-orange)
![Ollama](https://img.shields.io/badge/Ollama-0.4.7-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

超级浏览器是一个集成了浏览器自动化和本地大语言模型的智能浏览工具，支持多种浏览器引擎，提供开发者工具，可用于网页交互、数据抓取和智能辅助。通过本地 AI 模型提供智能分析和辅助功能，无需联网即可使用。

## 📋 功能特点
- **🌐 多浏览器引擎支持**：基于 Playwright，支持 Chromium、Firefox 和 WebKit
- **🤖 本地 AI 集成**：通过 Ollama 集成本地大语言模型，无需联网即可使用 AI 功能
- **🛠️ 开发者工具**：提供丰富的浏览器控制命令，支持网页交互和数据抓取
- **💻 跨平台支持**：支持 Windows 系统，未来将支持多系统

## 🔧 安装要求
- **Python 3.9.x**
- **[Ollama](https://ollama.ai/)** (用于本地 AI 模型)
- **[Playwright](https://playwright.dev/)** (自动安装浏览器引擎)

## 🚀 快速开始
### 1. 克隆仓库
```bash
git clone https://github.com/Shiqi-SQ/super-browser.git
cd super-browser
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 安装 Ollama
从 [Ollama 官网](https://ollama.com/download) 下载并安装 Ollama。

### 4. 下载 AI 模型
```bash
ollama pull deepseek-r1:8b
```

### 5. 启动超级浏览器
```bash
python main.py
```
## 📖 使用说明
### 主界面
1. 选择浏览器类型 (Chromium, Firefox, WebKit)
2. 选择 AI 模型 (需要先通过 Ollama 下载模型)
3. 勾选"开发者模式"可启用开发者工具
4. 点击"启动浏览器"开始使用

### 开发者工具命令
| 命令                            | 说明             | 示例                                      |
| ------------------------------- | ---------------- | ----------------------------------------- |
| goto?url=网址                   | 导航到指定网址   | goto?url=https://www.example.com          |
| click?selector=选择器           | 点击元素         | click?selector=#submit-button             |
| fill?selector=选择器&text=文本  | 填充表单         | fill?selector=#search-input&text=查询内容 |
| getTitle                        | 获取页面标题     | getTitle                                  |
| getUrl                          | 获取当前URL      | getUrl                                    |
| getHtml                         | 获取页面HTML     | getHtml                                   |
| getText?selector=选择器         | 获取元素文本     | getText?selector=h1                       |
| screenshot                      | 截图             | screenshot                                |
| waitForSelector?selector=选择器 | 等待元素出现     | waitForSelector?selector=.loading         |
| waitForNavigation               | 等待页面导航完成 | waitForNavigation                         |
更多指令请参考 [commands.md](./commands.md) 文件

### AI 对话功能
超级浏览器集成了本地大语言模型，可以：
- 🔍 回答问题和提供信息
- 📊 分析网页内容
- 💻 生成代码和自动化脚本
- 🤖 辅助网页操作和数据提取

## 🏗️ 项目结构
```plaintext
超级浏览器/
├── main.py           # 主程序入口，负责UI界面和启动流程
├── browser.py        # 浏览器控制器，封装Playwright API
├── executor.py       # 命令执行服务器，处理客户端命令
├── dev_tools.py      # 开发者工具界面，提供命令输入和结果显示
├── talk.py           # AI 对话模块，与Ollama交互
├── prompt.py         # AI 提示词管理
├── interpreter.py    # Python代码解释器
├── commands.md       # 命令文档
├── requirements.txt  # 项目依赖
├── script/           # 辅助脚本目录
│   ├── jQloader.js
│   └── jQloader.min.js
└── jquery/           # jQuery库文件
    └── 3.7.1.min.js
```

## 👨‍💻 开发指南
### 添加新命令
在 executor.py 中添加新的命令处理函数，并在 get_command_function 方法中注册该命令：
```python
def my_new_command(self, params):
    # 实现命令逻辑
    return {"status": "success", "result": "命令执行结果"}
```
然后在 get_command_function 方法中注册：
```python
elif command == "my_new_command":
    return self.my_new_command
```

### 自定义 AI 模型
1. 使用 Ollama 下载所需模型：
```bash
ollama pull model_name
```

2. 在超级浏览器界面中选择该模型

### 扩展浏览器功能
可以通过修改 browser.py 来扩展浏览器功能，添加新的浏览器操作方法。

## ❓ 常见问题
### Ollama 无法启动
- ✅ 确保已正确安装 Ollama
- ✅ 检查 Ollama 服务是否已在运行
- ✅ 查看日志获取详细错误信息
### 浏览器启动失败
- ✅ 确保已安装相应的浏览器引擎
- ✅ 检查网络连接是否正常
- ✅ 尝试重启超级浏览器应用
### 开发者工具连接问题
- ✅ 确保浏览器已成功启动
- ✅ 检查 executor 服务是否正常运行
- ✅ 重新启动开发者工具

## 🤝 贡献指南
欢迎提交 Pull Request 或创建 Issue 来帮助改进项目。贡献步骤：
1. Fork 本仓库
2. 创建您的特性分支 ( git checkout -b feature/amazing-feature )
3. 提交您的更改 ( git commit -m 'Add some amazing feature' )
4. 推送到分支 ( git push origin feature/amazing-feature )
5. 打开一个 Pull Request

## 📄 许可证
MIT License

## 🙏 致谢
- Playwright - 浏览器自动化框架
- Ollama - 本地大语言模型运行工具
- jQuery - JavaScript库
