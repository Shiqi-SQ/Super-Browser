# 浏览器控制指令列表

每条指令采用"指令?参数=值&参数=值"的格式：

## 页面元素控制类

### 点击元素

**指令写法**: `click?selector=选择器`
**功能**: 点击指定的页面元素

### 填充表单

**指令写法**: `fill?selector=选择器&value=值`
**功能**: 在表单元素中填入指定值

### 模拟键盘输入

**指令写法**: `type?selector=选择器&text=文本&delay=延迟毫秒数`
**功能**: 模拟键盘在元素中逐字输入文本

### 鼠标悬停

**指令写法**: `hover?selector=选择器`
**功能**: 将鼠标悬停在指定元素上

### 选择下拉菜单选项

**指令写法**: `select?selector=选择器&value=选项值`
**功能**: 在下拉菜单中选择指定选项

### 勾选复选框

**指令写法**: `check?selector=选择器`
**功能**: 勾选复选框

### 取消勾选复选框

**指令写法**: `uncheck?selector=选择器`
**功能**: 取消勾选复选框

### 上传文件

**指令写法**: `upload?selector=选择器&path=文件路径`
**功能**: 上传文件到指定的文件输入框

## 页面信息获取类

### 获取页面标题

**指令写法**: `getTitle`
**功能**: 获取当前页面的标题

### 获取当前URL

**指令写法**: `getUrl`
**功能**: 获取当前页面的URL

### 获取页面HTML

**指令写法**: `getHtml`
**功能**: 获取当前页面的完整HTML（渲染后）

### 获取元素文本

**指令写法**: `getText?selector=选择器`
**功能**: 获取指定元素的文本内容

### 获取元素属性

**指令写法**: `getAttribute?selector=选择器&name=属性名`
**功能**: 获取指定元素的特定属性值

### 获取元素数量

**指令写法**: `getElements?selector=选择器`
**功能**: 获取匹配选择器的所有元素信息

## 页面底层控制类

### 执行JavaScript代码

**指令写法**: `evaluate?expression=JavaScript表达式`
**功能**: 在页面上下文中执行JavaScript代码并返回结果

### 添加脚本标签

**指令写法**: `addScriptTag?url=脚本URL` 或 `addScriptTag?content=脚本内容`
**功能**: 向页面添加JavaScript脚本

### 添加样式标签

**指令写法**: `addStyleTag?url=样式URL` 或 `addStyleTag?content=样式内容`
**功能**: 向页面添加CSS样式

## 页面底层获取类

### 获取原始响应内容

**指令写法**: `getResponseBody`
**功能**: 获取页面的原始HTTP响应内容

### 获取Cookie

**指令写法**: `getCookies`
**功能**: 获取当前页面的所有Cookie

### 获取localStorage

**指令写法**: `getLocalStorage`
**功能**: 获取页面的localStorage内容

## 浏览器控制类

### 导航到URL

**指令写法**: `goto?url=网址&waitUntil=load`
**功能**: 导航到指定URL

### 刷新页面

**指令写法**: `reload`
**功能**: 刷新当前页面

### 返回上一页

**指令写法**: `goBack`
**功能**: 返回浏览历史中的上一页

### 前进到下一页

**指令写法**: `goForward`
**功能**: 前进到浏览历史中的下一页

### 创建新标签页

**指令写法**: `newPage`
**功能**: 创建一个新的标签页

### 关闭标签页

**指令写法**: `closePage?index=标签页索引`
**功能**: 关闭指定索引的标签页

### 切换标签页

**指令写法**: `switchPage?index=标签页索引`
**功能**: 切换到指定索引的标签页

### 获取所有标签页

**指令写法**: `getPages`
**功能**: 获取所有标签页的信息

### 截图

**指令写法**: `screenshot?path=保存路径&fullPage=true&selector=选择器`
**功能**: 截取页面或元素的截图

### 保存为PDF

**指令写法**: `pdf?path=保存路径&landscape=false`
**功能**: 将页面保存为PDF文件（仅Chromium headless模式支持）

## 浏览器数据类

### 设置Cookie

**指令写法**: `setCookies?cookies=Cookie列表JSON`
**功能**: 设置浏览器Cookie

### 清除Cookie

**指令写法**: `clearCookies`
**功能**: 清除所有Cookie

### 设置localStorage项

**指令写法**: `setLocalStorageItem?key=键名&value=值`
**功能**: 设置localStorage中的键值对

### 清除localStorage

**指令写法**: `clearLocalStorage`
**功能**: 清除所有localStorage内容

### 等待URL变化

**指令写法**: `waitForUrl?url=目标URL&timeout=超时毫秒数`
**功能**: 等待页面URL变为指定值
