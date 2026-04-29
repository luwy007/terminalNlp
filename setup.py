#!/usr/bin/env python3
"""terminalNlp 安装脚本"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terminalNlp",
    version="0.1.0",
    author="terminalNlp Team",
    description="将自然语言翻译成终端命令的翻译壳",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/terminalNlp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.20.0"],
        "gemini": ["google-generativeai>=0.3.0"],
        "all": [
            "openai>=1.0.0",
            "anthropic>=0.20.0",
            "google-generativeai>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nlp=src.translator:main",
        ],
    },
)
