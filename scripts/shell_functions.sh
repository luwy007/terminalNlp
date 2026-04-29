# terminalNlp Shell 集成函数
# 用法: source 此文件到你的 ~/.bashrc 或 ~/.zshrc
#
# 提供函数:
#   nlp "自然语言描述"   - 翻译并执行命令
#   nlp                - 进入交互模式
#   ai()               - nlp 的别名
#   nlp-config         - 快速配置
#   nlp-history        - 查看历史

# ───────────────────────────────────────────────
# 路径设置
# ───────────────────────────────────────────────

TERMINALNLP_DIR="${HOME}/.local/share/terminalNlp"
TERMINALNLP_BIN="${TERMINALNLP_DIR}/nlp"

# 确保 nlp 在 PATH 中
if [[ -d "${HOME}/.local/bin" ]]; then
    case ":${PATH}:" in
        *:"${HOME}/.local/bin":*) ;;
        *) export PATH="${HOME}/.local/bin:${PATH}" ;;
    esac
fi

# ───────────────────────────────────────────────
# 核心函数
# ───────────────────────────────────────────────

# 检查 nlp 是否可用
__nlp_check() {
    if ! command -v nlp &> /dev/null; then
        if [[ -x "${TERMINALNLP_BIN}" ]]; then
            nlp() { "${TERMINALNLP_BIN}" "$@"; }
        else
            echo "[terminalNlp] 错误: nlp 命令未找到。请先运行安装脚本。" >&2
            return 1
        fi
    fi
}

# 主函数 - 自然语言翻译
# 用法:
#   nlp "查找大于100MB的文件"
#   nlp                    # 交互模式
#   nlp -e "重启nginx"      # 直接执行
#   nlp -d "删除临时文件"    # 干跑模式
#   nlp -x "docker ps"      # 解释命令
nlp() {
    __nlp_check || return 1
    command nlp "$@"
}

# 别名
alias ai='nlp'
alias ask='nlp'

# ───────────────────────────────────────────────
# 快捷函数
# ───────────────────────────────────────────────

# 快速配置
nlp-config() {
    __nlp_check || return 1
    if [[ $# -eq 0 ]]; then
        nlp --setup
    else
        nlp --config "$@"
    fi
}

# 查看历史
nlp-history() {
    __nlp_check || return 1
    nlp --history
}

# 解释一个命令（不执行）
nlp-explain() {
    __nlp_check || return 1
    if [[ $# -eq 0 ]]; then
        echo "用法: nlp-explain '命令或描述'"
        return 1
    fi
    nlp --explain "$@"
}

# 干跑模式 - 只看命令不执行
nlp-dry() {
    __nlp_check || return 1
    if [[ $# -eq 0 ]]; then
        echo "用法: nlp-dry '自然语言描述'"
        return 1
    fi
    nlp --dry-run "$@"
}

# ───────────────────────────────────────────────
# 交互增强
# ───────────────────────────────────────────────

# 使用 fzf 快速搜索历史命令并执行
if command -v fzf &> /dev/null; then
    
    # Bash readline widget
    __nlp_fzf_history_bash() {
        local selected
        # 从历史文件解析
        local hist_file="${HOME}/.config/terminalNlp/history.json"
        if [[ -f "${hist_file}" ]]; then
            selected=$(python3 -c "
import json, sys
try:
    with open('${hist_file}') as f:
        data = json.load(f)
    for item in data[-30:]:
        print(f\"{item['input']} | {item['command']}\")
except: pass
" 2>/dev/null | fzf --height 40% --reverse --delimiter=' | ' --with-nth=1 --preview='echo {2}' | sed 's/.* | //')
        fi
        
        if [[ -n "${selected}" ]]; then
            READLINE_LINE="${selected}"
            READLINE_POINT=${#selected}
        fi
    }
    
    # Zsh widget
    __nlp_fzf_history_zsh() {
        local selected
        local hist_file="${HOME}/.config/terminalNlp/history.json"
        if [[ -f "${hist_file}" ]]; then
            selected=$(python3 -c "
import json, sys
try:
    with open('${hist_file}') as f:
        data = json.load(f)
    for item in data[-30:]:
        print(f\"{item['input']} | {item['command']}\")
except: pass
" 2>/dev/null | fzf --height 40% --reverse --delimiter=' | ' --with-nth=1 --preview='echo {2}' | sed 's/.* | //')
        fi
        
        if [[ -n "${selected}" ]]; then
            LBUFFER="${selected}"
            CURSOR=${#selected}
        fi
    }
    
    # 注册 widget
    if [[ -n "${BASH_VERSION:-}" ]]; then
        bind -x '"\C-x\C-a": __nlp_fzf_history_bash' 2>/dev/null || true
    fi
    
    if [[ -n "${ZSH_VERSION:-}" ]]; then
        zle -N __nlp_fzf_history_zsh 2>/dev/null || true
        bindkey '^X^A' __nlp_fzf_history_zsh 2>/dev/null || true
    fi
fi

# ───────────────────────────────────────────────
# 首次使用提示
# ───────────────────────────────────────────────

if [[ ! -f "${HOME}/.config/terminalNlp/config.json" ]]; then
    echo "[terminalNlp] 💡 首次使用？运行 'nlp --setup' 配置 LLM 提供商"
fi
