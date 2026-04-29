#!/usr/bin/env python3
"""
terminalNlp - 终端自然语言翻译引擎
将人类自然语言指令翻译成机器可执行的 shell 命令
"""

import os
import sys
import json
import re
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple, List


# ───────────────────────────────────────────────
# 配置管理
# ───────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / "terminalNlp"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

DEFAULT_CONFIG = {
    "provider": "openai",  # openai | anthropic | gemini | ollama
    "model": "gpt-3.5-turbo",
    "api_key": "",
    "api_base": "",
    "ollama_host": "http://localhost:11434",
    "ollama_model": "llama3",
    "max_history": 50,
    "auto_execute": False,  # 是否自动执行（危险，默认关闭）
    "danger_confirm": True,  # 危险命令是否需要确认
    "language": "zh",  # 输出语言
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-[rf]*[rf]",
    r">\s*/dev/[sh]d[a-z]",  # 只匹配写入物理设备如 /dev/sda, /dev/hda
    r"\bdd\s+if=",
    r"\bmv\s+.*\s+/dev/null",
    r"\bmkfs\.",
    r":\(\)\{\s*:\|:\&\};:",  # fork bomb
    r"\bwget\s+.*\s*\|\s*sh",
    r"\bcurl\s+.*\s*\|\s*sh",
    r">\s*~/.\w+",  # 覆盖 home 目录文件
    r"sudo\s+rm",
]


def load_config() -> dict:
    """加载配置，如果不存在则创建默认配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 合并默认配置（处理新增字段）
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置到文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history() -> List[dict]:
    """加载命令历史"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history: List[dict]):
    """保存命令历史"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    max_hist = config.get("max_history", 50)
    history = history[-max_hist:]  # 只保留最近 N 条
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ───────────────────────────────────────────────
# 环境上下文收集
# ───────────────────────────────────────────────

def get_shell_info() -> dict:
    """获取当前 shell 环境信息"""
    shell = os.environ.get("SHELL", "/bin/bash")
    shell_name = Path(shell).name
    return {
        "shell": shell_name,
        "shell_path": shell,
        "pwd": os.getcwd(),
        "home": str(Path.home()),
        "user": os.environ.get("USER", "unknown"),
        "os": os.uname().sysname if hasattr(os, "uname") else "unknown",
    }


def get_recent_history(n: int = 5) -> List[str]:
    """获取最近几条 shell 历史命令"""
    shell = get_shell_info()["shell"]
    history = []
    try:
        if shell in ("bash", "sh"):
            histfile = os.environ.get("HISTFILE", str(Path.home() / ".bash_history"))
            if Path(histfile).exists():
                with open(histfile, "r", errors="ignore") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                    history = lines[-n:]
        elif shell == "zsh":
            histfile = os.environ.get("HISTFILE", str(Path.home() / ".zsh_history"))
            if Path(histfile).exists():
                with open(histfile, "r", errors="ignore") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                    # zsh history 格式: `: 时间戳:0;命令`
                    cleaned = []
                    for line in lines[-n*2:]:
                        if ";" in line:
                            cleaned.append(line.split(";", 1)[1])
                        else:
                            cleaned.append(line)
                    history = cleaned[-n:]
    except Exception:
        pass
    return history


def get_directory_context() -> str:
    """获取当前目录上下文（文件列表、git 状态等）"""
    context = []
    pwd = os.getcwd()
    context.append(f"当前目录: {pwd}")
    
    # 检查是否是 git 仓库
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            repo = result.stdout.strip()
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=2
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            context.append(f"Git 仓库: {repo} (分支: {branch})")
    except Exception:
        pass
    
    return "\n".join(context)


# ───────────────────────────────────────────────
# Prompt 工程
# ───────────────────────────────────────────────

def build_prompt(user_input: str, config: dict) -> str:
    """构建发送给 LLM 的 prompt"""
    shell_info = get_shell_info()
    recent_history = get_recent_history(5)
    dir_context = get_directory_context()
    
    lang = config.get("language", "zh")
    
    if lang == "zh":
        system_msg = """你是一个专业的终端命令翻译助手。将用户的自然语言描述转换为精确的、可执行的 shell 命令。

规则：
1. 只输出命令本身，不要添加解释、注释或 markdown 代码块标记
2. 如果有多条命令，用 && 连接（优先）或分号 ; 连接
3. 危险操作（删除、覆盖、格式化）在命令前添加 `# [DANGER] ` 标记
4. 如果意图不明确或无法安全推断，输出 `NEED_CLARIFY: 你的问题描述`
5. 优先使用通用 POSIX 命令，必要时使用当前 shell 的特定语法
6. 不要假设文件存在，使用适当的通配符或检查
7. 对于需要用户输入的命令，使用适当的非交互式替代方案"""
    else:
        system_msg = """You are a professional terminal command translator. Convert natural language descriptions into precise, executable shell commands.

Rules:
1. Output ONLY the command itself, no explanations, comments, or markdown code blocks
2. For multiple commands, use && (preferred) or ; 
3. Mark dangerous operations with `# [DANGER] ` prefix
4. If intent is unclear, output `NEED_CLARIFY: your question`
5. Prefer POSIX-compatible commands, use shell-specific syntax only when needed
6. Don't assume files exist, use appropriate wildcards or checks
7. For interactive commands, use non-interactive alternatives"""

    history_str = "\n".join([f"  {i+1}. {cmd}" for i, cmd in enumerate(recent_history)]) if recent_history else "  (无)"
    
    prompt = f"""{system_msg}

当前环境：
- 操作系统: {shell_info['os']}
- Shell: {shell_info['shell']}
- 当前用户: {shell_info['user']}
- 家目录: {shell_info['home']}

{dir_context}

最近命令历史：
{history_str}

用户输入: {user_input}

命令:"""
    
    return prompt


# ───────────────────────────────────────────────
# LLM 调用
# ───────────────────────────────────────────────

def call_openai(prompt: str, config: dict) -> str:
    """调用 OpenAI API"""
    try:
        import openai
    except ImportError:
        return "ERROR: 请先安装 openai 库: pip install openai"
    
    api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "ERROR: 未设置 OpenAI API Key。请设置 OPENAI_API_KEY 环境变量或在配置中指定。"
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url=config.get("api_base") or None,
    )
    
    try:
        response = client.chat.completions.create(
            model=config.get("model", "gpt-3.5-turbo"),
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: OpenAI API 调用失败: {e}"


def call_anthropic(prompt: str, config: dict) -> str:
    """调用 Anthropic Claude API"""
    try:
        import anthropic
    except ImportError:
        return "ERROR: 请先安装 anthropic 库: pip install anthropic"
    
    api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "ERROR: 未设置 Anthropic API Key。请设置 ANTHROPIC_API_KEY 环境变量或在配置中指定。"
    
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        response = client.messages.create(
            model=config.get("model", "claude-3-haiku-20240307"),
            max_tokens=500,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"ERROR: Anthropic API 调用失败: {e}"


def call_gemini(prompt: str, config: dict) -> str:
    """调用 Google Gemini API"""
    try:
        import google.generativeai as genai
    except ImportError:
        return "ERROR: 请先安装 google-generativeai 库: pip install google-generativeai"
    
    api_key = config.get("api_key") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "ERROR: 未设置 Google API Key。请设置 GOOGLE_API_KEY 环境变量或在配置中指定。"
    
    genai.configure(api_key=api_key)
    
    try:
        model = genai.GenerativeModel(config.get("model", "gemini-1.5-flash"))
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=500)
        )
        return response.text.strip()
    except Exception as e:
        return f"ERROR: Gemini API 调用失败: {e}"


def call_ollama(prompt: str, config: dict) -> str:
    """调用本地 Ollama 服务"""
    import urllib.request
    import urllib.error
    
    host = config.get("ollama_host", "http://localhost:11434")
    model = config.get("ollama_model", "llama3")
    
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except urllib.error.URLError as e:
        return f"ERROR: 无法连接到 Ollama ({host})。请确保 Ollama 服务已启动: {e}"
    except Exception as e:
        return f"ERROR: Ollama 调用失败: {e}"


def translate(user_input: str, config: dict) -> str:
    """主翻译函数"""
    prompt = build_prompt(user_input, config)
    provider = config.get("provider", "openai")
    
    if provider == "openai":
        return call_openai(prompt, config)
    elif provider == "anthropic":
        return call_anthropic(prompt, config)
    elif provider == "gemini":
        return call_gemini(prompt, config)
    elif provider == "ollama":
        return call_ollama(prompt, config)
    else:
        return f"ERROR: 不支持的 provider: {provider}"


# ───────────────────────────────────────────────
# 安全与执行
# ───────────────────────────────────────────────

def is_dangerous(command: str) -> Tuple[bool, str]:
    """检查命令是否包含危险操作"""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"匹配危险模式: {pattern}"
    return False, ""


def execute_command(command: str, dry_run: bool = False) -> Tuple[int, str, str]:
    """执行命令，返回 (returncode, stdout, stderr)"""
    if dry_run:
        return 0, "[DRY RUN] 命令未执行", ""
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时 (300秒)"
    except Exception as e:
        return -1, "", str(e)


# ───────────────────────────────────────────────
# 交互界面
# ───────────────────────────────────────────────

def color_print(text: str, color: str = "", bold: bool = False):
    """带颜色的打印"""
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "gray": "\033[90m",
    }
    reset = "\033[0m"
    bold_code = "\033[1m" if bold else ""
    color_code = colors.get(color, "")
    print(f"{bold_code}{color_code}{text}{reset}")


def interactive_confirm(command: str, is_danger: bool) -> str:
    """
    交互式确认命令
    返回: "execute" | "edit" | "copy" | "explain" | "cancel"
    """
    if is_danger:
        color_print("⚠️  危险命令 detected!", "red", bold=True)
    
    color_print(f"\n💡 建议命令:", "cyan", bold=True)
    if is_danger:
        color_print(f"   {command}", "red")
    else:
        color_print(f"   {command}", "green")
    
    if is_danger:
        color_print("\n此命令可能修改或删除数据，请谨慎操作。", "yellow")
    
    color_print("\n操作选项:", "gray")
    color_print("  [Y] 执行    [e] 编辑    [c] 复制到剪贴板    [x] 解释    [n] 取消", "gray")
    
    while True:
        try:
            choice = input("→ 你的选择 [Y/e/c/x/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "cancel"
        
        if choice in ("y", "yes", ""):
            return "execute"
        elif choice == "e":
            return "edit"
        elif choice == "c":
            return "copy"
        elif choice == "x":
            return "explain"
        elif choice in ("n", "no", "q", "quit"):
            return "cancel"
        else:
            color_print("无效输入，请重新选择。", "yellow")


def edit_command(command: str) -> str:
    """让用户编辑命令"""
    color_print("编辑命令（直接修改后回车）:", "cyan")
    try:
        edited = input(f"→ {command}").strip()
        if edited:
            return edited
        return command
    except (EOFError, KeyboardInterrupt):
        return command


def copy_to_clipboard(text: str):
    """复制文本到剪贴板"""
    import platform
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
        elif system == "Linux":
            # 尝试多种方式
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, check=True)
        elif system == "Windows":
            subprocess.run(["clip"], input=text, text=True, check=True)
        color_print("✅ 已复制到剪贴板", "green")
    except Exception as e:
        color_print(f"❌ 复制失败: {e}", "red")
        color_print(f"手动复制: {text}", "gray")


def explain_command(command: str, config: dict):
    """让 LLM 解释命令"""
    lang = config.get("language", "zh")
    
    # 构建专门的解释 prompt，避免被当成自然语言翻译
    shell_info = get_shell_info()
    if lang == "zh":
        prompt = f"""你是一个终端命令解释专家。请详细解释以下 shell 命令的每个部分的作用，以及可能的副作用。

当前环境：
- 操作系统: {shell_info['os']}
- Shell: {shell_info['shell']}

命令:
{command}

请按以下格式解释：
1. 命令整体功能概述
2. 每个参数/选项的含义
3. 可能的副作用或风险
4. 替代方案（如有）

解释："""
    else:
        prompt = f"""You are a shell command explanation expert. Please explain the following command in detail.

Environment:
- OS: {shell_info['os']}
- Shell: {shell_info['shell']}

Command:
{command}

Please explain:
1. Overall purpose
2. Each argument/option meaning
3. Potential side effects or risks
4. Alternative approaches (if any)

Explanation:"""
    
    color_print("\n🔍 正在获取解释...", "cyan")
    
    # 直接调用 LLM，不走 translate() 的通用 prompt 构建
    provider = config.get("provider", "openai")
    if provider == "openai":
        explanation = call_openai(prompt, config)
    elif provider == "anthropic":
        explanation = call_anthropic(prompt, config)
    elif provider == "gemini":
        explanation = call_gemini(prompt, config)
    elif provider == "ollama":
        explanation = call_ollama(prompt, config)
    else:
        explanation = f"ERROR: 不支持的 provider: {provider}"
    
    if explanation.startswith("ERROR:"):
        color_print(explanation, "red")
    else:
        color_print(f"\n{explanation}", "gray")


# ───────────────────────────────────────────────
# 主流程
# ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="terminalNlp - 将自然语言翻译成终端命令",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  nlp "查找当前目录下大于100MB的文件"
  nlp "把今天修改的文件打包成 backup.tar.gz"
  nlp --explain "docker ps -a | grep exited"
  nlp --config provider=gemini
        """
    )
    parser.add_argument("query", nargs="?", help="自然语言描述（可选，不提供则进入交互模式）")
    parser.add_argument("-e", "--execute", action="store_true", help="直接执行，不询问确认")
    parser.add_argument("-d", "--dry-run", action="store_true", help="只显示命令，不执行")
    parser.add_argument("-x", "--explain", action="store_true", help="解释命令含义")
    parser.add_argument("-c", "--config", metavar="KEY=VALUE", action="append", help="设置配置项")
    parser.add_argument("--setup", action="store_true", help="交互式配置向导")
    parser.add_argument("--history", action="store_true", help="显示命令历史")
    
    args = parser.parse_args()
    config = load_config()
    
    # 配置向导
    if args.setup:
        run_setup_wizard(config)
        return
    
    # 处理配置更新
    if args.config:
        for item in args.config:
            if "=" not in item:
                color_print(f"配置格式错误: {item} (应为 key=value)", "red")
                return
            key, value = item.split("=", 1)
            if key in ("auto_execute", "danger_confirm"):
                value = value.lower() in ("true", "1", "yes", "on")
            elif key == "max_history":
                value = int(value)
            config[key] = value
        save_config(config)
        color_print("✅ 配置已更新", "green")
        return
    
    # 显示历史
    if args.history:
        history = load_history()
        if not history:
            color_print("暂无历史记录", "gray")
        else:
            color_print("📜 命令历史:", "cyan", bold=True)
            for i, item in enumerate(history[-20:], 1):
                ts = item.get("timestamp", "")[:19]
                color_print(f"  {i}. [{ts}] {item['input']}", "gray")
                color_print(f"     → {item['command']}", "green")
        return
    
    # 交互模式
    if not args.query:
        run_interactive_mode(config)
        return
    
    # 单次查询模式
    user_input = args.query
    
    # 如果是解释模式
    if args.explain:
        explain_command(user_input, config)
        return
    
    # 翻译
    color_print("🤖 正在翻译...", "cyan")
    command = translate(user_input, config)
    
    if command.startswith("ERROR:"):
        color_print(command, "red")
        return
    
    if command.startswith("NEED_CLARIFY:"):
        color_print(f"❓ {command}", "yellow")
        return
    
    # 安全检查
    is_danger, reason = is_dangerous(command)
    
    # 记录历史
    history = load_history()
    history.append({
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "input": user_input,
        "command": command,
        "executed": False,
    })
    save_history(history)
    
    # 直接执行模式
    if args.execute and not (is_danger and config.get("danger_confirm", True)):
        color_print(f"$ {command}", "green")
        rc, stdout, stderr = execute_command(command)
        if stdout:
            print(stdout, end="")
        if stderr:
            color_print(stderr, "red")
        return
    
    # 干跑模式
    if args.dry_run:
        color_print(f"\n💡 {command}\n", "green")
        return
    
    # 交互确认
    choice = interactive_confirm(command, is_danger)
    
    if choice == "execute":
        color_print(f"\n$ {command}\n", "green")
        rc, stdout, stderr = execute_command(command)
        if stdout:
            print(stdout, end="")
        if stderr:
            color_print(stderr, "red")
        # 更新历史标记为已执行
        history[-1]["executed"] = True
        save_history(history)
    elif choice == "edit":
        edited = edit_command(command)
        if edited != command:
            color_print(f"\n$ {edited}\n", "green")
            rc, stdout, stderr = execute_command(edited)
            if stdout:
                print(stdout, end="")
            if stderr:
                color_print(stderr, "red")
    elif choice == "copy":
        copy_to_clipboard(command)
    elif choice == "explain":
        explain_command(command, config)
        # 解释后再次询问
        choice2 = interactive_confirm(command, is_danger)
        if choice2 == "execute":
            color_print(f"\n$ {command}\n", "green")
            rc, stdout, stderr = execute_command(command)
            if stdout:
                print(stdout, end="")
            if stderr:
                color_print(stderr, "red")
        elif choice2 == "copy":
            copy_to_clipboard(command)


def run_interactive_mode(config: dict):
    """交互式 REPL 模式"""
    color_print("=" * 50, "cyan")
    color_print("🚀 terminalNlp 交互模式", "cyan", bold=True)
    color_print("   输入自然语言描述，我将翻译成终端命令", "gray")
    color_print("   特殊命令: /quit /history /config /explain", "gray")
    color_print("=" * 50, "cyan")
    
    while True:
        try:
            color_print("", "")
            user_input = input("nlp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            color_print("👋 再见!", "cyan")
            break
        
        if not user_input:
            continue
        
        if user_input in ("/quit", "/q", "/exit"):
            color_print("👋 再见!", "cyan")
            break
        elif user_input == "/history":
            history = load_history()
            for i, item in enumerate(history[-10:], 1):
                color_print(f"  {i}. {item['input']} → {item['command']}", "gray")
            continue
        elif user_input.startswith("/config "):
            parts = user_input.split(None, 2)
            if len(parts) >= 2:
                color_print(f"当前配置: {json.dumps(config, indent=2)}", "gray")
            continue
        elif user_input.startswith("/explain "):
            explain_command(user_input[9:], config)
            continue
        
        # 翻译
        color_print("🤖 翻译中...", "cyan")
        command = translate(user_input, config)
        
        if command.startswith("ERROR:"):
            color_print(command, "red")
            continue
        
        if command.startswith("NEED_CLARIFY:"):
            color_print(f"❓ {command}", "yellow")
            continue
        
        is_danger, _ = is_dangerous(command)
        
        # 记录历史
        history = load_history()
        history.append({
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "input": user_input,
            "command": command,
            "executed": False,
        })
        save_history(history)
        
        choice = interactive_confirm(command, is_danger)
        
        if choice == "execute":
            color_print(f"\n$ {command}\n", "green")
            rc, stdout, stderr = execute_command(command)
            if stdout:
                print(stdout, end="")
            if stderr:
                color_print(stderr, "red")
            history[-1]["executed"] = True
            save_history(history)
        elif choice == "edit":
            edited = edit_command(command)
            if edited != command:
                color_print(f"\n$ {edited}\n", "green")
                rc, stdout, stderr = execute_command(edited)
                if stdout:
                    print(stdout, end="")
                if stderr:
                    color_print(stderr, "red")
        elif choice == "copy":
            copy_to_clipboard(command)
        elif choice == "explain":
            explain_command(command, config)


def run_setup_wizard(config: dict):
    """交互式配置向导"""
    color_print("=" * 50, "cyan")
    color_print("🔧 terminalNlp 配置向导", "cyan", bold=True)
    color_print("=" * 50, "cyan")
    
    color_print("\n选择 LLM 提供商:", "yellow")
    color_print("  1. OpenAI (GPT-3.5/4)", "gray")
    color_print("  2. Anthropic (Claude)", "gray")
    color_print("  3. Google (Gemini - 免费额度充足)", "gray")
    color_print("  4. Ollama (本地模型，无需联网)", "gray")
    
    try:
        choice = input("→ 选择 [1-4]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    
    providers = {"1": "openai", "2": "anthropic", "3": "gemini", "4": "ollama"}
    if choice in providers:
        config["provider"] = providers[choice]
    else:
        color_print("无效选择", "red")
        return
    
    if config["provider"] == "openai":
        key = input("→ OpenAI API Key (留空使用环境变量 OPENAI_API_KEY): ").strip()
        if key:
            config["api_key"] = key
        model = input("→ 模型 [gpt-3.5-turbo/gpt-4]: ").strip()
        if model:
            config["model"] = model
    elif config["provider"] == "anthropic":
        key = input("→ Anthropic API Key (留空使用环境变量 ANTHROPIC_API_KEY): ").strip()
        if key:
            config["api_key"] = key
        config["model"] = "claude-3-haiku-20240307"
    elif config["provider"] == "gemini":
        key = input("→ Google API Key (留空使用环境变量 GOOGLE_API_KEY): ").strip()
        if key:
            config["api_key"] = key
        config["model"] = "gemini-1.5-flash"
    elif config["provider"] == "ollama":
        host = input("→ Ollama 地址 [http://localhost:11434]: ").strip()
        if host:
            config["ollama_host"] = host
        model = input("→ 模型名称 [llama3]: ").strip()
        if model:
            config["ollama_model"] = model
    
    save_config(config)
    color_print("\n✅ 配置已保存!", "green")
    color_print(f"配置文件: {CONFIG_FILE}", "gray")


if __name__ == "__main__":
    main()
