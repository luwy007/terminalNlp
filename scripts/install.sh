#!/usr/bin/env bash
# terminalNlp 安装脚本
# 用法: curl -fsSL ... | bash
#    或: bash install.sh

set -euo pipefail

REPO_URL="https://github.com/yourusername/terminalNlp"
INSTALL_DIR="${HOME}/.local/share/terminalNlp"
BIN_DIR="${HOME}/.local/bin"
SHELL_RC=""

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测 shell
detect_shell() {
    local shell_name
    shell_name=$(basename "${SHELL}")
    case "${shell_name}" in
        bash)
            SHELL_RC="${HOME}/.bashrc"
            ;;
        zsh)
            SHELL_RC="${HOME}/.zshrc"
            ;;
        fish)
            SHELL_RC="${HOME}/.config/fish/config.fish"
            ;;
        *)
            warn "未知的 shell: ${shell_name}，将尝试修改 ~/.bashrc"
            SHELL_RC="${HOME}/.bashrc"
            ;;
    esac
}

# 检查依赖
check_dependencies() {
    info "检查依赖..."
    
    if ! command -v python3 &> /dev/null; then
        error "需要 Python 3，请先安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    info "Python 版本: ${PYTHON_VERSION}"
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        warn "未找到 pip3，尝试安装..."
        python3 -m ensurepip --upgrade 2>/dev/null || {
            error "无法安装 pip，请手动安装"
            exit 1
        }
    fi
    
    success "依赖检查通过"
}

# 安装 Python 依赖
install_python_deps() {
    info "安装 Python 依赖..."
    
    # 创建虚拟环境（可选）
    VENV_DIR="${INSTALL_DIR}/venv"
    if [[ ! -d "${VENV_DIR}" ]]; then
        python3 -m venv "${VENV_DIR}"
    fi
    
    # 安装基础依赖
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install requests 2>/dev/null || true
    
    success "Python 依赖安装完成"
}

# 安装项目文件
install_project() {
    info "安装 terminalNlp..."
    
    # 创建目录
    mkdir -p "${INSTALL_DIR}/src"
    mkdir -p "${BIN_DIR}"
    mkdir -p "${HOME}/.config/terminalNlp"
    
    # 如果当前目录是项目根目录，直接复制
    if [[ -f "src/translator.py" ]]; then
        cp src/translator.py "${INSTALL_DIR}/src/"
    else
        # 否则从 GitHub 下载
        info "从 GitHub 下载..."
        if command -v curl &> /dev/null; then
            curl -fsSL "${REPO_URL}/raw/main/src/translator.py" -o "${INSTALL_DIR}/src/translator.py"
        elif command -v wget &> /dev/null; then
            wget -q "${REPO_URL}/raw/main/src/translator.py" -O "${INSTALL_DIR}/src/translator.py"
        else
            error "需要 curl 或 wget 来下载文件"
            exit 1
        fi
    fi
    
    # 创建启动脚本
    cat > "${INSTALL_DIR}/nlp" << 'EOF'
#!/usr/bin/env bash
# terminalNlp 启动脚本

INSTALL_DIR="${HOME}/.local/share/terminalNlp"
VENV_DIR="${INSTALL_DIR}/venv"

# 如果虚拟环境存在，使用它
if [[ -f "${VENV_DIR}/bin/python" ]]; then
    PYTHON="${VENV_DIR}/bin/python"
else
    PYTHON="python3"
fi

exec "${PYTHON}" "${INSTALL_DIR}/src/translator.py" "$@"
EOF
    chmod +x "${INSTALL_DIR}/nlp"
    
    # 创建符号链接
    ln -sf "${INSTALL_DIR}/nlp" "${BIN_DIR}/nlp"
    
    success "项目文件安装完成"
}

# 安装 shell 集成
install_shell_integration() {
    info "安装 shell 集成..."
    
    detect_shell
    
    # 创建 shell 函数文件
    local shell_functions="${INSTALL_DIR}/shell_functions.sh"
    
    cat > "${shell_functions}" << 'EOF'
# terminalNlp Shell 集成
# 添加到 ~/.bashrc 或 ~/.zshrc 中使用

# 检查 nlp 命令是否存在
if ! command -v nlp &> /dev/null; then
    # 尝试添加 ~/.local/bin 到 PATH
    export PATH="${HOME}/.local/bin:${PATH}"
fi

# 主函数: 用自然语言执行命令
# 用法: nlp "描述"
# 或: nlp 进入交互模式

# 快捷别名
alias ai='nlp'
alias ask='nlp'

# 可选: 绑定快捷键（需要 fzf 或类似工具）
# Ctrl+G 快速查询历史
if command -v fzf &> /dev/null; then
    __nlp_history_widget() {
        local selected
        selected=$(nlp --history 2>/dev/null | fzf --height 40% --reverse | sed 's/.*→ //')
        if [[ -n "${selected}" ]]; then
            READLINE_LINE="${selected}"
            READLINE_POINT=${#selected}
        fi
    }
    
    # bash
    if [[ -n "${BASH_VERSION}" ]]; then
        bind -x '"\C-g": __nlp_history_widget' 2>/dev/null || true
    fi
    
    # zsh
    if [[ -n "${ZSH_VERSION}" ]]; then
        zle -N __nlp_history_widget
        bindkey '^G' __nlp_history_widget 2>/dev/null || true
    fi
fi

# 提示用户配置
if [[ ! -f "${HOME}/.config/terminalNlp/config.json" ]]; then
    echo "[terminalNlp] 首次使用？运行 'nlp --setup' 进行配置"
fi
EOF
    
    # 检查是否已添加
    if [[ -f "${SHELL_RC}" ]]; then
        if grep -q "terminalNlp" "${SHELL_RC}" 2>/dev/null; then
            warn "Shell 集成已存在于 ${SHELL_RC}"
        else
            cat >> "${SHELL_RC}" << EOF

# terminalNlp 集成
source "${shell_functions}"
EOF
            success "Shell 集成已添加到 ${SHELL_RC}"
        fi
    fi
    
    # fish shell 支持
    if [[ "$(basename "${SHELL}")" == "fish" ]]; then
        local fish_config="${HOME}/.config/fish/config.fish"
        mkdir -p "$(dirname "${fish_config}")"
        
        cat > "${INSTALL_DIR}/shell_functions.fish" << 'EOF'
# terminalNlp Fish Shell 集成

# 检查 nlp 命令
if not command -v nlp > /dev/null
    set -gx PATH $HOME/.local/bin $PATH
end

# 别名
alias ai='nlp'
alias ask='nlp'

# 首次使用提示
if not test -f "$HOME/.config/terminalNlp/config.json"
    echo "[terminalNlp] 首次使用？运行 'nlp --setup' 进行配置"
end
EOF
        
        if [[ -f "${fish_config}" ]] && grep -q "terminalNlp" "${fish_config}" 2>/dev/null; then
            warn "Fish 集成已存在"
        else
            echo "source ${INSTALL_DIR}/shell_functions.fish" >> "${fish_config}"
            success "Fish 集成已添加"
        fi
    fi
}

# 主安装流程
main() {
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════╗
║     terminalNlp - 终端自然语言翻译壳      ║
║                                          ║
║   将人类语言翻译成机器命令                ║
╚══════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_dependencies
    install_python_deps
    install_project
    install_shell_integration
    
    echo ""
    success "🎉 安装完成!"
    echo ""
    info "使用方式:"
    echo "  nlp \"你的自然语言描述\"     # 单次翻译"
    echo "  nlp                        # 进入交互模式"
    echo "  nlp --setup                # 配置 LLM 提供商"
    echo "  nlp --history              # 查看历史"
    echo ""
    info "快捷别名:"
    echo "  ai \"描述\"  或  ask \"描述\""
    echo ""
    warn "请运行 'source ${SHELL_RC}' 或重新打开终端以生效"
    echo ""
    info "推荐: 先运行 'nlp --setup' 配置你的 LLM API"
}

main "$@"
