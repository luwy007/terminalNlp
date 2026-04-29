# terminalNlp 🚀

> 在命令行套一层"翻译壳"，用自然语言操作终端。

```bash
# 以前
$ find . -name "*.log" -size +100M -mtime -7 -exec ls -lh {} \;

# 现在
$ nlp "查找最近7天修改过的大于100MB的日志文件"
💡 建议命令:
   find . -name "*.log" -size +100M -mtime -7 -exec ls -lh {} \;

操作选项:
  [Y] 执行    [e] 编辑    [c] 复制到剪贴板    [x] 解释    [n] 取消
→ 你的选择 [Y/e/c/x/n]: Y
```

## 特性

- 🎯 **自然语言转命令** - 用中文/英文描述意图，自动翻译成 shell 命令
- 🛡️ **安全确认机制** - 危险命令自动检测，二次确认后才执行
- 🔍 **命令解释** - 不懂生成的命令？一键获取详细解释
- 📜 **历史记录** - 自动保存翻译历史，方便复用
- ⚡ **多 LLM 支持** - OpenAI / Anthropic / Google Gemini / 本地 Ollama
- 🖥️ **交互模式** - REPL 式交互，持续对话式操作
- 🔧 **Shell 集成** - 一行命令集成到 bash/zsh/fish

## 快速开始

### 安装

```bash
# 方式1: 一键安装
curl -fsSL https://raw.githubusercontent.com/yourusername/terminalNlp/main/scripts/install.sh | bash

# 方式2: 手动安装
git clone https://github.com/yourusername/terminalNlp.git
cd terminalNlp
pip install -e ".[all]"   # 安装所有 LLM 依赖
# 或
pip install -e ".[gemini]" # 只安装 Gemini 依赖
```

### 配置

```bash
# 交互式配置向导
nlp --setup

# 或手动配置
nlp --config provider=gemini
nlp --config api_key=YOUR_API_KEY
```

支持的提供商：
- `openai` - GPT-3.5/4（需 API Key）
- `anthropic` - Claude（需 API Key）
- `gemini` - Google Gemini（**推荐**，免费额度充足）
- `ollama` - 本地模型（无需联网，需安装 Ollama）

### 使用

```bash
# 单次翻译
nlp "把当前目录下所有 .txt 文件压缩成 archive.zip"

# 交互模式
nlp

# 解释命令含义
nlp -x "find . -type f -perm /111"

# 干跑模式（只显示命令，不执行）
nlp -d "删除所有 .tmp 文件"

# 直接执行（跳过确认）
nlp -e "显示磁盘使用情况"

# 查看历史
nlp --history
```

## Shell 集成

安装脚本会自动将以下功能添加到你的 shell：

```bash
# 别名
ai "查找大文件"     # 等同于 nlp
ask "重启服务"      # 等同于 nlp

# 快捷函数
nlp-config          # 快速配置
nlp-history         # 查看历史
nlp-explain "..."   # 解释命令
nlp-dry "..."       # 干跑模式
```

## 架构

```
用户输入 (自然语言)
    ↓
[翻译壳] ──→ 构建 Prompt（含环境上下文）
    ↓
[LLM API] ──→ 生成 shell 命令
    ↓
[安全检测] ──→ 危险命令标记
    ↓
[用户确认] ──→ Y(执行) / e(编辑) / c(复制) / x(解释) / n(取消)
    ↓
[执行] ──→ 输出结果
```

## 安全

- ✅ 危险命令自动检测（`rm -rf`, `dd`, 重定向覆盖等）
- ✅ 所有危险操作必须二次确认
- ✅ 支持干跑模式预览命令
- ✅ 命令执行前可编辑修改
- ✅ 历史记录可追溯

## 开发

```bash
# 克隆仓库
git clone https://github.com/yourusername/terminalNlp.git
cd terminalNlp

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -e ".[all]"

# 运行测试
python -m pytest tests/

# 代码格式化
black src/
isort src/
```

## 许可证

MIT License
