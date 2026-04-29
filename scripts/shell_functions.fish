# terminalNlp Fish Shell 集成
# 用法: source 此文件到你的 ~/.config/fish/config.fish

set -gx TERMINALNLP_DIR "$HOME/.local/share/terminalNlp"
set -gx TERMINALNLP_BIN "$TERMINALNLP_DIR/nlp"

# 确保 nlp 在 PATH 中
if not contains "$HOME/.local/bin" $PATH
    set -gx PATH "$HOME/.local/bin" $PATH
end

# 检查 nlp 是否可用
function __nlp_check
    if not command -v nlp > /dev/null
        if test -x "$TERMINALNLP_BIN"
            function nlp
                "$TERMINALNLP_BIN" $argv
            end
        else
            echo "[terminalNlp] 错误: nlp 命令未找到。请先运行安装脚本。" >&2
            return 1
        end
    end
end

# 主函数
function nlp
    __nlp_check; or return 1
    command nlp $argv
end

# 别名
alias ai='nlp'
alias ask='nlp'

# 快捷函数
function nlp-config
    __nlp_check; or return 1
    if test (count $argv) -eq 0
        nlp --setup
    else
        nlp --config $argv
    end
end

function nlp-history
    __nlp_check; or return 1
    nlp --history
end

function nlp-explain
    __nlp_check; or return 1
    if test (count $argv) -eq 0
        echo "用法: nlp-explain '命令或描述'"
        return 1
    end
    nlp --explain $argv
end

function nlp-dry
    __nlp_check; or return 1
    if test (count $argv) -eq 0
        echo "用法: nlp-dry '自然语言描述'"
        return 1
    end
    nlp --dry-run $argv
end

# 首次使用提示
if not test -f "$HOME/.config/terminalNlp/config.json"
    echo "[terminalNlp] 💡 首次使用？运行 'nlp --setup' 配置 LLM 提供商"
end
