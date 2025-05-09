#!/usr/bin/env python3
"""
MCP服务测试脚本

提供对多智能体MCP服务各功能的自动化测试，包括记忆银行、任务管理和LLM调用等功能。
"""

import os
import sys
import json
import time
import pytest
import asyncio
import logging
import requests
import unittest
from pathlib import Path

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('mcp_test')

# 添加父目录到系统路径以便导入工具模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 导入测试所需的模块
try:
    from multi_agent_mcp.server import init_components
    from tools import memory_init
    direct_import = True
except ImportError:
    direct_import = False
    logger.warning("无法直接导入MCP服务模块，将使用HTTP请求进行测试")

# MCP服务地址
MCP_SERVICE_URL = os.environ.get("MCP_SERVICE_URL", "http://localhost:8000")

class MCPServiceTest(unittest.TestCase):
    """MCP服务测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备工作"""
        # 初始化记忆银行
        cls.memory_bank_dir = parent_dir / "memory-bank"
        if not cls.memory_bank_dir.exists():
            logger.info("初始化记忆银行...")
            memory_init.create_memory_bank(
                project_name="MCP服务测试项目",
                description="用于测试MCP服务功能的演示项目"
            )
        
        # 尝试检查MCP服务是否可用
        cls.mcp_available = False
        try:
            response = requests.get(f"{MCP_SERVICE_URL}/health")
            if response.status_code == 200:
                cls.mcp_available = True
                logger.info("MCP服务可用")
            else:
                logger.warning(f"MCP服务健康检查失败，状态码: {response.status_code}")
        except Exception as e:
            logger.warning(f"无法连接到MCP服务: {e}")
    
    def setUp(self):
        """每个测试前的准备工作"""
        if not self.mcp_available and not direct_import:
            self.skipTest("MCP服务不可用，跳过测试")
    
    # 记忆银行测试
    def test_memory_operations(self):
        """测试记忆银行操作"""
        # 创建测试文件
        test_file_path = "test_memory.md"
        test_content = """# 测试文件

这是一个用于测试记忆银行操作的文件。
创建时间: ${timestamp}
"""
        test_content = test_content.replace("${timestamp}", time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 测试创建文件
        result = self._call_mcp("create_memory_file", {
            "file_path": test_file_path,
            "content": test_content
        })
        self.assertIn("已成功创建", result)
        
        # 测试读取文件
        result = self._call_mcp("read_memory", {
            "file_path": test_file_path
        })
        self.assertIn("测试文件", result)
        self.assertIn("用于测试记忆银行操作", result)
        
        # 测试更新文件
        updated_content = test_content + "\n\n更新时间: " + time.strftime("%Y-%m-%d %H:%M:%S")
        result = self._call_mcp("update_memory", {
            "file_path": test_file_path,
            "content": updated_content
        })
        self.assertIn("已成功更新", result)
        
        # 测试列出文件
        result = self._call_mcp("list_memory_files", {})
        files = json.loads(result)
        self.assertIsInstance(files, list)
        self.assertIn(test_file_path, files)
        
        # 测试搜索记忆
        result = self._call_mcp("search_memory", {
            "query": "测试记忆银行操作",
            "top_k": 3
        })
        results = json.loads(result)
        self.assertIsInstance(results, list)
        if len(results) > 0:
            self.assertIn("file", results[0])
            self.assertIn("content", results[0])
            self.assertIn("similarity", results[0])
    
    # 任务管理测试
    def test_task_operations(self):
        """测试任务管理操作"""
        # 创建任务
        test_task_desc = f"测试任务 {time.strftime('%Y%m%d%H%M%S')}"
        result = self._call_mcp("create_task", {
            "description": test_task_desc,
            "priority": "medium"
        })
        task_result = json.loads(result)
        self.assertIn("task_id", task_result)
        self.assertIn("status", task_result)
        
        task_id = task_result["task_id"]
        
        # 获取任务状态
        result = self._call_mcp("get_task_status", {
            "task_id": task_id
        })
        task_status = json.loads(result)
        if "error" not in task_status:
            self.assertIn("id", task_status)
            self.assertIn("description", task_status)
            self.assertEqual(task_status["description"], test_task_desc)
        
        # 列出所有任务
        result = self._call_mcp("list_tasks", {})
        tasks = json.loads(result)
        self.assertIsInstance(tasks, list)
        
        # 分析任务
        result = self._call_mcp("analyze_task", {
            "task_description": "构建一个简单的Web应用，包含用户登录、数据展示和管理功能"
        })
        analysis = json.loads(result)
        self.assertIn("title", analysis)
        self.assertIn("description", analysis)
        self.assertIn("subtasks", analysis)
        self.assertIsInstance(analysis["subtasks"], list)
    
    # LLM调用测试
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="需要设置OPENAI_API_KEY环境变量")
    def test_llm_call(self):
        """测试LLM调用"""
        result = self._call_mcp("call_llm", {
            "prompt": "Hello, what is the capital of France?",
            "provider": "openai",
            "model": "gpt-3.5-turbo"
        })
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)  # 应该得到有意义的回复
    
    # 健康检查测试
    def test_health_check(self):
        """测试健康检查"""
        result = self._call_mcp("check_health", {})
        health = json.loads(result)
        self.assertIn("status", health)
        self.assertIn("components", health)
        self.assertIn("version", health)
        self.assertIsInstance(health["components"], dict)
    
    def _call_mcp(self, tool_name, params):
        """调用MCP服务工具"""
        if direct_import and hasattr(self, f"_direct_{tool_name}"):
            # 如果可以直接导入且有直接调用方法，则使用直接调用
            direct_method = getattr(self, f"_direct_{tool_name}")
            return direct_method(**params)
        
        # 否则使用HTTP请求
        url = f"{MCP_SERVICE_URL}/tools/{tool_name}"
        try:
            response = requests.post(url, json=params)
            if response.status_code == 200:
                return response.text
            else:
                raise Exception(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")
        except Exception as e:
            logger.error(f"调用MCP服务失败: {e}")
            return f"错误: {str(e)}"

# 性能测试
class MCPPerformanceTest(unittest.TestCase):
    """MCP服务性能测试类"""
    
    def test_memory_read_performance(self):
        """测试记忆银行读取性能"""
        service_test = MCPServiceTest()
        
        # 创建大文件进行测试
        large_content = "# 大文件测试\n\n" + "测试内容\n" * 1000
        service_test._call_mcp("create_memory_file", {
            "file_path": "large_test.md",
            "content": large_content
        })
        
        # 性能测试
        start_time = time.time()
        for _ in range(10):
            service_test._call_mcp("read_memory", {
                "file_path": "large_test.md"
            })
        
        elapsed = time.time() - start_time
        avg_time = elapsed / 10
        
        logger.info(f"记忆银行读取性能: 平均 {avg_time:.4f} 秒/次")
        self.assertLess(avg_time, 1.0, "读取大文件平均时间应小于1秒")
    
    def test_search_performance(self):
        """测试记忆搜索性能"""
        service_test = MCPServiceTest()
        
        # 准备多个测试文件
        for i in range(5):
            content = f"""# 测试文件 {i}
            
这是测试文件 {i} 的内容。
包含一些关键词如：性能测试、并发、响应时间、延迟等。
文件编号: {i}
创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            service_test._call_mcp("create_memory_file", {
                "file_path": f"perf_test_{i}.md",
                "content": content
            })
        
        # 性能测试
        start_time = time.time()
        for _ in range(5):
            service_test._call_mcp("search_memory", {
                "query": "性能测试 响应时间",
                "top_k": 3
            })
        
        elapsed = time.time() - start_time
        avg_time = elapsed / 5
        
        logger.info(f"记忆搜索性能: 平均 {avg_time:.4f} 秒/次")
        self.assertLess(avg_time, 2.0, "记忆搜索平均时间应小于2秒")

# 并发测试
class MCPConcurrencyTest(unittest.TestCase):
    """MCP服务并发测试类"""
    
    async def _async_call_mcp(self, tool_name, params):
        """异步调用MCP服务工具"""
        url = f"{MCP_SERVICE_URL}/tools/{tool_name}"
        session = None
        try:
            import aiohttp
            session = aiohttp.ClientSession()
            async with session.post(url, json=params) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return f"请求失败，状态码: {response.status}"
        except Exception as e:
            return f"错误: {str(e)}"
        finally:
            if session:
                await session.close()
    
    async def _run_concurrent_tasks(self, tool_name, params_list, concurrency=5):
        """运行并发任务"""
        tasks = []
        for i in range(min(concurrency, len(params_list))):
            tasks.append(self._async_call_mcp(tool_name, params_list[i]))
        
        results = await asyncio.gather(*tasks)
        return results
    
    def test_concurrent_memory_read(self):
        """测试并发记忆读取"""
        # 准备参数
        params_list = [
            {"file_path": "projectbrief.md"},
            {"file_path": "productContext.md"},
            {"file_path": "systemPatterns.md"},
            {"file_path": "techContext.md"},
            {"file_path": "activeContext.md"}
        ]
        
        # 运行并发测试
        results = asyncio.run(self._run_concurrent_tasks("read_memory", params_list))
        
        # 验证结果
        for result in results:
            self.assertNotIn("错误", result)
            self.assertGreater(len(result), 10)
    
    def test_concurrent_task_creation(self):
        """测试并发任务创建"""
        # 准备参数
        params_list = [
            {"description": "并发测试任务1", "priority": "high"},
            {"description": "并发测试任务2", "priority": "medium"},
            {"description": "并发测试任务3", "priority": "low"},
            {"description": "并发测试任务4", "priority": "medium"},
            {"description": "并发测试任务5", "priority": "high"}
        ]
        
        # 运行并发测试
        results = asyncio.run(self._run_concurrent_tasks("create_task", params_list))
        
        # 验证结果
        for result in results:
            if "错误" not in result:
                task_result = json.loads(result)
                self.assertIn("task_id", task_result)
                self.assertIn("status", task_result)

def run_tests():
    """运行测试"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests() 