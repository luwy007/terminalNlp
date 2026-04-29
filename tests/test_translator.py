#!/usr/bin/env python3
"""terminalNlp 单元测试"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from translator import (
    load_config, save_config,
    is_dangerous,
    get_shell_info,
    build_prompt,
)


class TestConfig(unittest.TestCase):
    """测试配置管理"""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / ".config" / "terminalNlp"
        self.config_file = self.config_dir / "config.json"
        
        # Mock 配置路径
        self.patcher = patch("translator.CONFIG_DIR", self.config_dir)
        self.patcher.start()
        self.patcher2 = patch("translator.CONFIG_FILE", self.config_file)
        self.patcher2.start()
    
    def tearDown(self):
        self.patcher.stop()
        self.patcher2.stop()
        self.temp_dir.cleanup()
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        config = load_config()
        self.assertEqual(config["provider"], "openai")
        self.assertEqual(config["model"], "gpt-3.5-turbo")
        self.assertTrue(config["danger_confirm"])
    
    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        config = load_config()
        config["provider"] = "gemini"
        config["api_key"] = "test-key"
        save_config(config)
        
        loaded = load_config()
        self.assertEqual(loaded["provider"], "gemini")
        self.assertEqual(loaded["api_key"], "test-key")


class TestSecurity(unittest.TestCase):
    """测试安全检测"""
    
    def test_dangerous_rm_rf(self):
        """检测 rm -rf"""
        is_danger, reason = is_dangerous("rm -rf /")
        self.assertTrue(is_danger)
    
    def test_dangerous_dd(self):
        """检测 dd 命令"""
        is_danger, reason = is_dangerous("dd if=/dev/zero of=/dev/sda")
        self.assertTrue(is_danger)
    
    def test_dangerous_redirect(self):
        """检测危险重定向"""
        is_danger, reason = is_dangerous("echo '' > /dev/sda")
        self.assertTrue(is_danger)
    
    def test_safe_command(self):
        """安全命令不应被标记"""
        is_danger, reason = is_dangerous("ls -la")
        self.assertFalse(is_danger)
    
    def test_safe_find(self):
        """find 命令是安全的"""
        is_danger, reason = is_dangerous("find . -name '*.txt'")
        self.assertFalse(is_danger)


class TestShellInfo(unittest.TestCase):
    """测试环境信息收集"""
    
    def test_get_shell_info(self):
        """测试获取 shell 信息"""
        info = get_shell_info()
        self.assertIn("shell", info)
        self.assertIn("pwd", info)
        self.assertIn("home", info)
        self.assertTrue(Path(info["pwd"]).exists())


class TestPromptBuilding(unittest.TestCase):
    """测试 Prompt 构建"""
    
    def test_prompt_contains_user_input(self):
        """Prompt 应包含用户输入"""
        config = {"language": "zh"}
        prompt = build_prompt("查找大文件", config)
        self.assertIn("查找大文件", prompt)
    
    def test_prompt_contains_shell_info(self):
        """Prompt 应包含 shell 信息"""
        config = {"language": "zh"}
        prompt = build_prompt("test", config)
        self.assertIn("Shell:", prompt)
    
    def test_prompt_english(self):
        """英文模式"""
        config = {"language": "en"}
        prompt = build_prompt("list files", config)
        self.assertIn("You are a professional", prompt)


if __name__ == "__main__":
    unittest.main()
