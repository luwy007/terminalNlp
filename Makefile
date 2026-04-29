.PHONY: install test lint format clean dev-setup

# 默认 Python
PYTHON := python3
PIP := pip3

# 安装到开发环境
dev-setup:
	$(PIP) install -e ".[all]"
	$(PIP) install black isort pytest flake8

# 安装（生产）
install:
	$(PIP) install -e ".[all]"

# 运行测试
test:
	$(PYTHON) -m pytest tests/ -v

# 代码格式化
format:
	black src/ tests/
	isort src/ tests/

# 代码检查
lint:
	flake8 src/ tests/ --max-line-length=120
	black --check src/ tests/

# 清理
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# 运行交互模式
run:
	$(PYTHON) src/translator.py
