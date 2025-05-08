#!/usr/bin/env python3

import unittest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import json
import platform

# Add the parent directory to the Python path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.plan_exec_llm import query_planner_llm, _mock_response, _check_api_keys, get_error_recognizer

class TestPlanExecLLM(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Save original environment
        self.original_env = dict(os.environ)
        # Set test environment variables
        os.environ['OPENAI_API_KEY'] = 'test_key'
        os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key'
        os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
        os.environ['SILICONFLOW_API_KEY'] = 'test_siliconflow_key'
        
        self.test_env_content = """
OPENAI_API_KEY=test_key
DEEPSEEK_API_KEY=test_deepseek_key
ANTHROPIC_API_KEY=test_anthropic_key
SILICONFLOW_API_KEY=test_siliconflow_key
"""
        # Create temporary test files
        with open('.env.test', 'w') as f:
            f.write(self.test_env_content)
            
        # 设置测试环境标记
        os.environ['TEST_ENV'] = 'development'

    def tearDown(self):
        """Clean up test fixtures"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Remove temporary test files
        if os.path.exists('.env.test'):
            os.remove('.env.test')

    @patch('tools.plan_exec_llm.load_dotenv')
    def test_check_api_keys(self, mock_load_dotenv):
        """测试API密钥检查"""
        available_providers = _check_api_keys()
        self.assertIn('openai', available_providers)
        self.assertIn('deepseek', available_providers)
        self.assertIn('anthropic', available_providers)
        self.assertIn('siliconflow', available_providers)
        mock_load_dotenv.assert_called()

    def test_mock_response_planning(self):
        """测试模拟响应 - 规划任务"""
        prompt = "任务规划和分解：将这个复杂项目拆分为子任务"
        response = _mock_response(prompt)
        # 验证响应是JSON格式的任务列表
        try:
            tasks = json.loads(response)
            self.assertIsInstance(tasks, list)
            self.assertGreater(len(tasks), 0)
        except json.JSONDecodeError:
            self.fail("响应不是有效的JSON")

    def test_mock_response_instructions(self):
        """测试模拟响应 - 指令生成"""
        prompt = "为这个任务生成指令"
        response = _mock_response(prompt)
        self.assertIn("确认任务范围和目标", response)

    def test_error_recognizer(self):
        """测试错误模式识别系统"""
        recognizer = get_error_recognizer()
        self.assertIsNotNone(recognizer)
        
        # 测试不同类型的错误识别
        timeout_error = TimeoutError("连接超时")
        category, severity, recovery_action = recognizer.recognize_error(timeout_error, "test")
        self.assertEqual(category.name, "TIMEOUT")
        self.assertIsNotNone(recovery_action)
        
        conn_error = ConnectionError("无法连接到服务器")
        category, severity, recovery_action = recognizer.recognize_error(conn_error, "test")
        self.assertEqual(category.name, "NETWORK")
        self.assertIsNotNone(recovery_action)

    @patch('tools.plan_exec_llm._query_openai')
    def test_query_planner_llm_retry(self, mock_query_openai):
        """测试LLM调用重试机制"""
        # 模拟前两次调用失败，第三次成功
        mock_query_openai.side_effect = [
            ConnectionError("连接失败"),
            TimeoutError("请求超时"),
            "成功的响应"
        ]
        
        response = query_planner_llm("测试提示词", provider="openai", max_retries=3)
        self.assertEqual(response, "成功的响应")
        self.assertEqual(mock_query_openai.call_count, 3)

    @patch('tools.plan_exec_llm._query_openai')
    def test_query_planner_llm_max_retries(self, mock_query_openai):
        """测试达到最大重试次数后的行为"""
        # 所有调用都失败
        mock_query_openai.side_effect = ConnectionError("连接始终失败")
        
        response = query_planner_llm("测试提示词", provider="openai", max_retries=2)
        # 应该返回模拟响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertEqual(mock_query_openai.call_count, 2)

    def test_provider_validation(self):
        """测试提供商验证逻辑"""
        # 使用无效的提供商名称
        response = query_planner_llm("测试提示词", provider="invalid_provider")
        # 应该回退到模拟模式
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    @patch('tools.plan_exec_llm.platform.system')
    def test_cross_platform_detection(self, mock_system):
        """测试跨平台检测"""
        # 测试Windows检测
        mock_system.return_value = "Windows"
        self.assertEqual(platform.system(), "Windows")
        
        # 测试Linux检测
        mock_system.return_value = "Linux"
        self.assertEqual(platform.system(), "Linux")
        
        # 测试macOS检测
        mock_system.return_value = "Darwin"
        self.assertEqual(platform.system(), "Darwin")

    @patch('tools.plan_exec_llm._check_api_keys')
    def test_provider_fallback(self, mock_check_api_keys):
        """测试提供商回退机制"""
        # 模拟没有可用的提供商
        mock_check_api_keys.return_value = []
        
        # 创建mock响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "模拟的LLM响应"
        
        with patch('tools.plan_exec_llm._mock_response', return_value=mock_response.choices[0].message.content):
            response = query_planner_llm("测试提示词", provider="openai")
            # 应该回退到模拟模式
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            self.assertEqual(response, "模拟的LLM响应")

if __name__ == '__main__':
    unittest.main() 