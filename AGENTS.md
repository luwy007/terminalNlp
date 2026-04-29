# terminalNlp - Agent Guide

> 本文档面向 AI 编码助手。项目的主要自然语言为中文（代码注释、文档、用户界面均为中文）。

## 项目概述

terminalNlp 是一个命令行"翻译壳"工具，将人类自然语言（中文/英文）翻译成可执行的 shell 命令。它通过调用外部 LLM API（OpenAI、Anthropic、Google Gemini、本地 Ollama）生成命令，并在执行前提供安全确认、编辑、解释等交互选项。

核心入口：`src/translator.py` 中的 `main()` 函数，通过 `setup.py` 注册为控制台命令 `nlp`。

## 技术栈

- **语言**：Python 3.8+
- **构建工具**：setuptools（`setup.py`），暂无 `pyproject.toml`
- **依赖管理**：`pip` + `setup.py` 的 `install_requires` / `extras_require`
- **测试框架**：pytest（实际测试文件使用标准库 `unittest` 编写，pytest 兼容运行）
- **代码格式化**：black、isort
- **代码检查**：flake8（最大行宽 120）

## 项目结构

```
terminalNlp/
├── src/
│   └── translator.py          # 唯一核心源码（~840 行），包含全部业务逻辑
├── tests/
│   └── test_translator.py     # 单元测试（unittest 风格）
├── scripts/
│   ├── install.sh             # 一键安装脚本（bash）
│   ├── shell_functions.sh     # bash/zsh shell 集成函数
│   └── shell_functions.fish   # fish shell 集成函数
├── setup.py                   # Python 包配置与入口点
├── Makefile                   # 常用开发命令封装
├── README.md                  # 中文项目文档
└── .vscode/extensions.json    # VS Code 扩展推荐（当前为空列表）
```

### 代码组织（单文件架构）

`src/translator.py` 按功能划分为以下区域，以 `─` 分隔线标注：

1. **配置管理** — `CONFIG_DIR` / `CONFIG_FILE` / `HISTORY_FILE` 路径；`load_config()` / `save_config()` / `load_history()` / `save_history()`
2. **环境上下文收集** — `get_shell_info()`、`get_recent_history()`、`get_directory_context()`
3. **Prompt 工程** — `build_prompt()`，根据当前 shell、目录、git 状态、历史命令构建发送给 LLM 的 prompt
4. **LLM 调用** — `call_openai()`、`call_anthropic()`、`call_gemini()`、`call_ollama()`、`translate()`
5. **安全与执行** — `is_dangerous()`（正则匹配危险命令）、`execute_command()`（subprocess 执行）
6. **交互界面** — `color_print()`、`interactive_confirm()`、`edit_command()`、`copy_to_clipboard()`、`explain_command()`
7. **主流程** — `main()` 参数解析、`run_interactive_mode()` REPL、`run_setup_wizard()` 配置向导

## 构建与测试命令

```bash
# 开发环境安装（含所有 LLM 依赖 + 开发工具）
make dev-setup
# 等价于: pip install -e ".[all]" && pip install black isort pytest flake8

# 仅安装运行依赖
make install

# 运行测试
make test
# 等价于: python3 -m pytest tests/ -v

# 代码格式化
make format
# 等价于: black src/ tests/ && isort src/ tests/

# 代码检查
make lint
# 等价于: flake8 src/ tests/ --max-line-length=120 && black --check src/ tests/

# 清理构建产物
make clean

# 直接运行交互模式
make run
```

## 代码风格指南

- **格式化**：black（无需配置），isort 排序 import
- **行宽上限**：120 字符（flake8 配置）
- **注释与文档字符串**：使用中文；模块级 docstring 描述功能；关键函数加中文 docstring
- **分隔风格**：大功能区块之间使用 `─` 重复符号的注释线分隔（如 `# ───────────────────────────────────────────────`）
- **类型注解**：部分函数已使用（如 `load_config() -> dict`），新增代码建议保持一致
- **字符串引号**：项目内混用单双引号，无强制约束，但建议与上下文保持一致

## 测试策略

- **测试文件**：`tests/test_translator.py`
- **框架**：`unittest`（pytest 可无缝兼容）
- **测试覆盖**：
  - `TestConfig`：配置加载、保存、默认值
  - `TestSecurity`：危险命令正则检测（`rm -rf`、`dd`、重定向到设备等）与安全命令放行
  - `TestShellInfo`：环境信息收集
  - `TestPromptBuilding`：prompt 内容包含用户输入、shell 信息、中英文切换
- **Mock 策略**：使用 `unittest.mock.patch` 替换 `CONFIG_DIR` / `CONFIG_FILE` 为临时目录，避免污染真实配置
- **运行方式**：`python -m pytest tests/ -v`

## 安全注意事项

- **危险命令检测**：`DANGEROUS_PATTERNS` 列表使用正则匹配，涵盖 `rm -rf`、`dd`、`mkfs`、fork bomb、`curl | sh`、向设备重定向等。修改此列表会直接影响用户安全，需谨慎。
- **执行方式**：`execute_command()` 使用 `shell=True` 的 `subprocess.run()`，存在命令注入风险；但输入来源为 LLM 返回内容，非直接用户输入。
- **配置存储**：API Key 以明文形式存储在 `~/.config/terminalNlp/config.json` 中，当前无加密机制。
- **自动执行**：`auto_execute` 配置项默认关闭；即使开启，危险命令仍受 `danger_confirm` 二次确认保护。

## 部署与安装

- **开发安装**：`pip install -e ".[all]"`
- **用户安装**：运行 `scripts/install.sh`，脚本会：
  1. 检查 Python 3 与 pip
  2. 在 `~/.local/share/terminalNlp` 创建虚拟环境并安装依赖
  3. 复制 `src/translator.py` 到安装目录
  4. 创建 `~/.local/bin/nlp` 符号链接
  5. 向当前 shell 的 rc 文件（`.bashrc`/`.zshrc`/`.config/fish/config.fish`）追加 source 语句
- **入口点**：`setup.py` 中通过 `console_scripts` 将 `nlp` 映射到 `src.translator:main`

## 配置与运行时

- **配置文件路径**：`~/.config/terminalNlp/config.json`
- **历史记录路径**：`~/.config/terminalNlp/history.json`
- **支持的 LLM 提供商**：`openai`、`anthropic`、`gemini`、`ollama`
- **环境变量备选**：各 provider 优先读取配置文件中的 `api_key`，若为空则 fallback 到对应环境变量（`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GOOGLE_API_KEY`）

## 开发注意事项

- 项目目前为**单文件架构**，几乎所有业务逻辑集中在 `src/translator.py`。新增功能时：
  - 若改动较小，可直接在对应功能区块内添加
  - 若改动较大，建议保持现有区块分隔风格，避免破坏可读性
- Shell 集成脚本（`scripts/shell_functions.sh` / `.fish`）与 `install.sh` 中的嵌入代码**存在重复**，修改时需同步检查
- 当前无 CI/CD 配置文件，测试与 lint 需在本地通过 `make` 执行
