#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import sys
import json
import logging
import tempfile
from unittest.mock import patch, MagicMock, mock_open
import psutil
from typing import Dict, Any

# 确保可以导入tools模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock LLM API imports
sys.modules['google.generativeai'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['anthropic'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# 导入工具选择器和环境监控器
from tools.tool_selector import LLMSelector, EnvironmentMonitor
from test_cursorrules import CursorRulesTester

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tool_integration_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestLLMToolSelection(unittest.TestCase):
    """测试LLM工具模型选择功能"""
    
    def setUp(self):
        """设置测试环境"""
        # 模拟环境变量
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-openai-key',
            'ANTHROPIC_API_KEY': 'test-anthropic-key',
            'GOOGLE_API_KEY': 'test-google-key',
            'AZURE_OPENAI_API_KEY': 'test-azure-key',
            'AZURE_OPENAI_MODEL_DEPLOYMENT': 'test-model-deployment'
        })
        self.env_patcher.start()
        
        # 创建任务复杂度分类
        self.low_complexity_task = {
            "type": "code_generation",
            "description": "生成一个简单的Python函数，实现数字求和",
            "complexity": "low",
            "requirements": ["基本功能实现"]
        }
        
        self.medium_complexity_task = {
            "type": "code_generation",
            "description": "实现一个RESTful API服务，支持用户认证和数据处理",
            "complexity": "medium",
            "requirements": ["用户认证", "数据验证", "错误处理", "日志记录"]
        }
        
        self.high_complexity_task = {
            "type": "system_optimization",
            "description": "优化分布式系统中的数据一致性算法",
            "complexity": "high",
            "requirements": ["高并发支持", "容错机制", "性能优化", "安全考虑", "分布式事务"]
        }
        
        # 创建LLM选择器实例
        self.selector = LLMSelector()
    
    def tearDown(self):
        """清理测试环境"""
        self.env_patcher.stop()
    
    def test_model_selection_by_complexity(self):
        """测试根据任务复杂度选择合适的模型"""
        # 测试低复杂度任务
        provider, model = self.selector.select_model_by_complexity(self.low_complexity_task)
        self.assertEqual(provider, "anthropic")
        self.assertEqual(model, "claude-3-5-sonnet-20241022")
        
        # 测试中等复杂度任务
        provider, model = self.selector.select_model_by_complexity(self.medium_complexity_task)
        self.assertEqual(provider, "openai")
        self.assertEqual(model, "gpt-4o")
        
        # 测试高复杂度任务
        provider, model = self.selector.select_model_by_complexity(self.high_complexity_task)
        self.assertEqual(provider, "openai")
        self.assertEqual(model, "o1")
        
        # 测试未指定复杂度时的默认选择
        provider, model = self.selector.select_model_by_complexity({})
        self.assertEqual(provider, "openai")
        self.assertEqual(model, "gpt-4o")
    
    def test_cost_optimization(self):
        """测试成本优化策略"""
        # 测试不同优先级和复杂度的任务
        high_priority_task = self.high_complexity_task.copy()
        high_priority_task["priority"] = "high"
        provider, model = self.selector.select_optimal_model(high_priority_task)
        self.assertEqual(model, "o1")
        
        low_priority_task = self.low_complexity_task.copy()
        low_priority_task["priority"] = "low"
        provider, model = self.selector.select_optimal_model(low_priority_task)
        self.assertEqual(provider, "anthropic")
        self.assertEqual(model, "claude-3-5-sonnet-20241022")
        
        medium_priority_task = self.medium_complexity_task.copy()
        medium_priority_task["priority"] = "medium"
        provider, model = self.selector.select_optimal_model(medium_priority_task)
        self.assertEqual(provider, "openai")
        self.assertEqual(model, "gpt-4o")
    
    def test_response_time_tracking(self):
        """测试响应时间跟踪功能"""
        # 模拟不同模型的响应时间
        self.selector.track_response_time("claude-3-5-sonnet-20241022", 2.5)
        self.selector.track_response_time("gpt-4o", 1.8)
        self.selector.track_response_time("o1", 3.5)
        self.selector.track_response_time("gpt-4o", 1.9)  # 添加第二个数据点
        
        # 验证平均响应时间计算
        self.assertEqual(self.selector.get_average_response_time("claude-3-5-sonnet-20241022"), 2.5)
        self.assertEqual(self.selector.get_average_response_time("gpt-4o"), 1.85)  # (1.8 + 1.9) / 2
        self.assertEqual(self.selector.get_average_response_time("o1"), 3.5)
        
        # 测试调用次数统计
        self.assertEqual(self.selector.call_counts["claude-3-5-sonnet-20241022"], 1)
        self.assertEqual(self.selector.call_counts["gpt-4o"], 2)
        self.assertEqual(self.selector.call_counts["o1"], 1)
    
    def test_token_usage_tracking(self):
        """测试token使用情况跟踪"""
        # 添加模拟数据
        self.selector.track_token_usage("gpt-4o", 500, 300)
        self.selector.track_token_usage("gpt-4o", 600, 400)
        self.selector.track_token_usage("o1", 1000, 500)
        
        # 获取使用统计
        stats = self.selector.get_usage_statistics()
        
        # 验证token统计
        self.assertEqual(stats["gpt-4o"]["token_usage"]["prompt_tokens"], 1100)  # 500 + 600
        self.assertEqual(stats["gpt-4o"]["token_usage"]["completion_tokens"], 700)  # 300 + 400
        self.assertEqual(stats["o1"]["token_usage"]["prompt_tokens"], 1000)
        self.assertEqual(stats["o1"]["token_usage"]["completion_tokens"], 500)
        
        # 验证成本计算（根据MODEL_METRICS中的定义）
        # gpt-4o: 0.8元/1k tokens，(1100 + 700) * 0.8 / 1000 = 1.44元
        # o1: 5.0元/1k tokens，(1000 + 500) * 5.0 / 1000 = 7.5元
        self.assertAlmostEqual(stats["gpt-4o"]["estimated_cost"], 1.44)
        self.assertAlmostEqual(stats["o1"]["estimated_cost"], 7.5)


class TestEnvironmentAwareness(unittest.TestCase):
    """测试环境感知功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file_path = os.path.join(self.temp_dir.name, "temp_file.txt")
        
        # 创建临时文件用于测试
        with open(self.temp_file_path, "w") as f:
            f.write("Temporary test file")
        
        # 创建环境监控器实例
        self.monitor = EnvironmentMonitor()
    
    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    def test_python_environment_checking(self):
        """测试Python环境检查功能"""
        # 测试Python版本检查
        is_compatible, message = self.monitor.check_python_version()
        
        # 获取当前Python版本
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # 验证结果
        self.assertIn(current_version, message)
        self.assertTrue(is_compatible)  # 假设当前Python版本符合要求
    
    @patch('psutil.disk_usage')
    def test_disk_space_monitoring(self, mock_disk_usage):
        """测试磁盘空间监控功能"""
        # 模拟磁盘空间充足的情况
        mock_disk_usage.return_value = MagicMock(free=1024 * 1024 * 1024)  # 1 GB
        
        # 测试磁盘空间检查 - 空间充足
        success, message = self.monitor.check_disk_space(".", required_mb=500)
        self.assertTrue(success)
        self.assertIn("足够", message)
        
        # 测试磁盘空间检查 - 空间不足
        success, message = self.monitor.check_disk_space(".", required_mb=2000)
        self.assertFalse(success)
        self.assertIn("不足", message)
    
    @patch('psutil.virtual_memory')
    def test_memory_usage_analysis(self, mock_virtual_memory):
        """测试内存使用分析功能"""
        # 模拟内存信息
        mock_memory = MagicMock()
        mock_memory.available = 1024 * 1024 * 1024  # 1 GB
        mock_memory.total = 4 * 1024 * 1024 * 1024  # 4 GB
        mock_memory.percent = 25.0  # 25% 使用率
        mock_virtual_memory.return_value = mock_memory
        
        # 测试内存检查 - 内存充足
        success, message = self.monitor.check_memory(required_mb=500)
        self.assertTrue(success)
        self.assertIn("足够", message)
        
        # 测试内存检查 - 内存不足
        success, message = self.monitor.check_memory(required_mb=2000)
        self.assertFalse(success)
        self.assertIn("不足", message)
    
    @patch('subprocess.check_output')
    def test_dependency_integrity_validation(self, mock_check_output):
        """测试依赖完整性验证功能"""
        # 模拟pip list输出
        mock_check_output.return_value = b"""
Package      Version
------------ -------
pytest       7.4.3
psutil       5.9.6
requests     2.28.2
"""
        
        # 测试依赖验证 - 所有依赖都符合要求
        result = self.monitor.validate_dependencies({
            "pytest": "7.4.3",
            "psutil": "5.9.6",
            "requests": "2.28.2"
        })
        self.assertTrue(result["success"])
        self.assertEqual(len(result["missing_packages"]), 0)
        self.assertEqual(len(result["version_mismatch"]), 0)
        
        # 测试依赖验证 - 版本不匹配
        result = self.monitor.validate_dependencies({
            "pytest": "7.4.3",
            "psutil": "5.9.5",  # 错误的版本
            "requests": "2.28.2"
        })
        self.assertFalse(result["success"])
        self.assertEqual(len(result["missing_packages"]), 0)
        self.assertEqual(len(result["version_mismatch"]), 1)
        self.assertEqual(result["version_mismatch"][0][0], "psutil")
        
        # 测试依赖验证 - 缺失的包
        result = self.monitor.validate_dependencies({
            "pytest": "7.4.3",
            "psutil": "5.9.6",
            "missing_package": "1.0.0"  # 不存在的包
        })
        self.assertFalse(result["success"])
        self.assertEqual(len(result["missing_packages"]), 1)
        self.assertEqual(result["missing_packages"][0], "missing_package")
    
    @patch('psutil.cpu_percent')
    def test_cpu_usage_monitoring(self, mock_cpu_percent):
        """测试CPU使用率监控"""
        # 模拟CPU使用率 - 低负载
        mock_cpu_percent.return_value = 30.0
        
        # 测试CPU使用率检查 - 负载正常
        success, message = self.monitor.check_cpu_usage(max_percent=80)
        self.assertTrue(success)
        self.assertIn("可接受", message)
        
        # 模拟CPU使用率 - 高负载
        mock_cpu_percent.return_value = 90.0
        
        # 测试CPU使用率检查 - 负载过高
        success, message = self.monitor.check_cpu_usage(max_percent=80)
        self.assertFalse(success)
        self.assertIn("过高", message)


if __name__ == '__main__':
    unittest.main() 