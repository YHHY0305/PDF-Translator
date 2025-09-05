# PDF Translator

一个功能强大的PDF翻译工具，支持多种翻译引擎和智能文本选择，内置大语言模型对话功能。

## ✨ 主要功能

### 📄 PDF 阅读与操作
- **智能文本选择**：支持跨行、跨列的光标式文本选择
- **渐进式高亮**：实时显示选中文本，支持回退取消选择
- **缩放与平移**：Ctrl + 鼠标滚轮缩放，拖拽模式平移视图
- **多页面导航**：支持前后翻页浏览

### 🔤 翻译功能
- **双模式翻译**：
  - 普通翻译：使用有道翻译API
  - LLM翻译：使用本地Ollama大语言模型
- **流式输出**：实时显示翻译进度，避免界面卡顿
- **Markdown渲染**：支持公式、代码块、表格等富文本显示
- **多语言支持**：可配置目标翻译语言

### 🤖 AI 对话助手
- **智能问答**：基于选中文本进行上下文对话
- **模型选择**：支持多种Ollama模型（llama3、qwen2等）
- **流式响应**：实时显示AI回答过程
- **上下文感知**：可选择是否包含翻译文本作为对话背景

### 🎨 用户界面
- **三栏布局**：PDF显示区、翻译区、对话区
- **可配置服务器**：支持自定义Ollama服务器地址
- **美观字体**：优化的中英文字体显示
- **响应式设计**：支持窗口大小调整

## 🚀 快速开始

### 环境要求
- Python 3.7+
- Windows 10/11 (推荐)

### 安装依赖
```bash
pip install pymupdf pillow translators requests markdown tkinterweb
```

### 启动应用
```bash
python pdftran.py
```

## 📖 使用指南

### 1. 打开PDF文件
- 点击菜单栏 "File" → "Open PDF"
- 选择要翻译的PDF文件

### 2. 选择文本
- 确保左上角模式为"选取"
- 在PDF上按住鼠标左键拖拽选择文本
- 支持跨行选择，自动识别列布局

### 3. 翻译文本
- **普通翻译**：选择"普通翻译"模式，使用有道API
- **LLM翻译**：选择"LLM翻译"模式，使用本地大语言模型
- 翻译结果实时显示在右侧面板

### 4. AI对话
- 在右侧对话区输入问题
- 可选择"带上下文(翻译)"来包含当前翻译内容
- 按回车或点击"发送"开始对话

### 5. 高级功能
- **缩放**：Ctrl + 鼠标滚轮
- **平移**：切换到"拖拽"模式，按住鼠标拖拽
- **Markdown渲染**：勾选复选框启用富文本显示
- **服务器配置**：修改Ollama服务器地址

## ⚙️ 配置说明

### Ollama 服务器设置
1. 安装 [Ollama](https://ollama.ai/)
2. 启动Ollama服务
3. 在应用中修改服务器地址（默认：`http://192.168.1.135:11434`）
4. 点击"连接测试"验证连接
5. 点击"刷新"获取可用模型列表

### 推荐模型
- `llama3`：通用对话模型
- `qwen2:7b`：中文优化模型
- `qwen2:14b`：更强大的中文模型

## 🛠️ 技术架构

### 核心技术栈
- **GUI框架**：Tkinter
- **PDF处理**：PyMuPDF (fitz)
- **图像处理**：Pillow
- **翻译引擎**：translators + Ollama API
- **Markdown渲染**：markdown + tkinterweb

### 项目结构
```
pdf-translator/
├── pdftran.py          # 主程序文件
└── readme.md     
```

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献
1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 报告问题
- 使用 GitHub Issues 报告bug
- 提供详细的复现步骤
- 包含系统环境信息

### 功能建议
- 在 Issues 中提出新功能建议
- 详细描述使用场景和预期效果

## 📝 更新日志

### v1.0.0 (2024-09-5)
- ✨ 初始版本发布
- 🔤 支持PDF文本选择和翻译
- 🤖 集成Ollama大语言模型
- 🎨 美观的三栏界面设计
- 📱 支持缩放、平移等交互操作

## 🙏 致谢

- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF处理库
- [Ollama](https://ollama.ai/) - 本地大语言模型运行环境
- [translators](https://github.com/UlionTse/translators) - 多引擎翻译库
- [tkinterweb](https://github.com/rdbende/tkinterweb) - Tkinter HTML渲染组件

## 📞 联系方式

- 项目地址：[https://github.com/YHHY0305/PDF-Translator ]
- 问题反馈：[https://github.com/YHHY0305/PDF-Translator/issues]
- 邮箱：[anyan5925480@163.com]

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！
