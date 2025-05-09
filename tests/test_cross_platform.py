#!/usr/bin/env python3
"""
跨平台测试 - Cursor客户端与MCP服务通信

测试Cursor客户端与MCP服务的通信功能，确保在不同操作系统平台上都能正常工作。
测试范围包括连接建立、消息发送接收、任务创建与状态查询等功能。
"""

import os
import sys
import json
import asyncio
import unittest
import tempfile
import platform
import logging
import time
import uuid
import threading
from pathlib import Path

# 获取项目根目录
current_dir = Path(__file__).parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 导入被测试模块
from tools.cursor_connect import CursorClient, CursorApp
from tools.mcp_service import MCPService
from tools.communication_manager import CommunicationManager, QoSLevel, Priority

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("test_cross_platform")

class TestCursorClientMCPIntegration(unittest.TestCase):
    """测试Cursor客户端与MCP服务的集成"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 记录当前操作系统信息
        cls.os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
        
        logger.info(f"测试运行环境: {json.dumps(cls.os_info, ensure_ascii=False)}")
        
        # 创建临时目录用于测试文件
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.temp_dir.name)
        
        # 设置测试服务端口
        cls.service_port = 8766  # 使用非标准端口避免冲突
        
        # 启动MCP服务
        cls.service = None
        cls.service_task = None
        cls.event_loop = asyncio.new_event_loop()
        
        def start_service():
            asyncio.set_event_loop(cls.event_loop)
            cls.service = MCPService(host="localhost", port=cls.service_port, mock_mode=True)
            cls.service_task = cls.event_loop.create_task(cls.service.start())
            cls.event_loop.run_forever()
        
        cls.service_thread = threading.Thread(target=start_service)
        cls.service_thread.daemon = True
        cls.service_thread.start()
        
        # 等待服务启动
        time.sleep(1)
        
        logger.info(f"测试MCP服务已启动，端口: {cls.service_port}")
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 停止服务
        if cls.service and cls.event_loop:
            async def stop_service():
                await cls.service.stop()
                cls.event_loop.stop()
            
            future = asyncio.run_coroutine_threadsafe(stop_service(), cls.event_loop)
            future.result(timeout=5)
        
        # 等待服务线程退出
        if cls.service_thread and cls.service_thread.is_alive():
            cls.service_thread.join(timeout=5)
        
        # 删除临时目录
        cls.temp_dir.cleanup()
        
        logger.info("测试资源已清理")
    
    def setUp(self):
        """测试方法初始化"""
        # 创建新的事件循环用于测试
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 创建Cursor客户端
        self.client = None
    
    def tearDown(self):
        """测试方法清理"""
        # 断开客户端连接
        if self.client and self.client.connected:
            self.loop.run_until_complete(self.client.disconnect())
        
        # 关闭事件循环
        self.loop.close()
    
    def test_client_connection(self):
        """测试客户端连接"""
        self.client = CursorClient(
            host="localhost", 
            port=self.service_port,
            agent_type="test",
            agent_id=f"test-{str(uuid.uuid4())[:8]}"
        )
        
        # 连接到服务
        self.loop.run_until_complete(self.client.connect())
        
        # 检查连接状态
        self.assertTrue(self.client.connected, "客户端应成功连接到MCP服务")
        self.assertIsNotNone(self.client.client_id, "客户端应该收到客户端ID")
        
        # 断开连接
        self.loop.run_until_complete(self.client.disconnect())
        self.assertFalse(self.client.connected, "客户端应成功断开连接")
        
        logger.info(f"客户端连接测试通过 - {self.os_info['system']}")
    
    def test_task_creation(self):
        """测试任务创建"""
        self.client = CursorClient(
            host="localhost", 
            port=self.service_port,
            agent_type="test",
            agent_id=f"test-{str(uuid.uuid4())[:8]}"
        )
        
        # 连接到服务
        self.loop.run_until_complete(self.client.connect())
        
        # 创建任务
        task_description = f"测试任务 - {platform.system()} - {time.time()}"
        response = self.loop.run_until_complete(
            self.client.create_task(
                description=task_description,
                priority="medium"
            )
        )
        
        # 检查任务创建响应
        self.assertIn("task_id", response, "响应中应包含任务ID")
        task_id = response["task_id"]
        self.assertTrue(task_id, "任务ID不应为空")
        
        # 查询任务状态
        task_status = self.loop.run_until_complete(self.client.query_task(task_id))
        
        # 检查任务状态响应
        self.assertEqual(task_status["task_id"], task_id, "任务ID应匹配")
        self.assertIn("status", task_status, "响应应包含任务状态")
        
        logger.info(f"任务创建测试通过 - {self.os_info['system']} - 任务ID: {task_id}")
    
    def test_message_sending(self):
        """测试消息发送"""
        self.client = CursorClient(
            host="localhost", 
            port=self.service_port,
            agent_type="test",
            agent_id=f"test-{str(uuid.uuid4())[:8]}"
        )
        
        # 连接到服务
        self.loop.run_until_complete(self.client.connect())
        
        # 发送消息
        target_id = "executor-mock"
        content = {
            "message_type": "test_message",
            "data": {
                "platform": platform.system(),
                "timestamp": time.time(),
                "test_id": str(uuid.uuid4())
            }
        }
        
        result = self.loop.run_until_complete(
            self.client.send_message(target_id, content)
        )
        
        # 检查发送结果
        self.assertTrue(result, "消息应成功发送")
        
        logger.info(f"消息发送测试通过 - {self.os_info['system']}")
    
    def test_file_paths(self):
        """测试文件路径处理的跨平台兼容性"""
        # 创建测试文件
        test_filename = f"test_file_{str(uuid.uuid4())[:8]}.json"
        test_filepath = self.temp_path / test_filename
        
        # 写入测试数据
        test_data = {
            "client_id": f"test-{str(uuid.uuid4())[:8]}",
            "platform": platform.system(),
            "timestamp": time.time()
        }
        
        with open(test_filepath, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        # 检查文件是否成功创建
        self.assertTrue(test_filepath.exists(), "测试文件应成功创建")
        
        # 读取文件内容
        with open(test_filepath, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        
        # 检查内容
        self.assertEqual(loaded_data["client_id"], test_data["client_id"], "文件内容应正确保存")
        self.assertEqual(loaded_data["platform"], platform.system(), "平台信息应正确")
        
        logger.info(f"文件路径测试通过 - {self.os_info['system']} - {test_filepath}")
    
    def test_environment_variables(self):
        """测试环境变量处理"""
        # 设置测试环境变量
        test_var_name = f"TEST_VAR_{str(uuid.uuid4())[:8]}"
        test_var_value = f"test_value_{platform.system()}_{time.time()}"
        
        os.environ[test_var_name] = test_var_value
        
        # 检查环境变量是否正确设置
        self.assertEqual(os.environ.get(test_var_name), test_var_value, "环境变量应正确设置")
        
        # 清除测试环境变量
        del os.environ[test_var_name]
        
        # 检查环境变量是否已清除
        self.assertIsNone(os.environ.get(test_var_name), "环境变量应成功清除")
        
        logger.info(f"环境变量测试通过 - {self.os_info['system']}")

def platform_specific_tests():
    """平台特定测试"""
    system = platform.system()
    logger.info(f"运行平台特定测试 - {system}")
    
    if system == "Windows":
        # Windows特定测试
        TestCursorClientMCPIntegration.windows_specific_tests()
    elif system == "Darwin":
        # macOS特定测试
        TestCursorClientMCPIntegration.macos_specific_tests()
    elif system == "Linux":
        # Linux特定测试
        TestCursorClientMCPIntegration.linux_specific_tests()
    else:
        logger.warning(f"未知平台: {system}，跳过平台特定测试")

# 各平台特定测试
def windows_specific_tests():
    """Windows特定测试"""
    logger.info("运行Windows特定测试")
    # Windows特定的测试代码...

def macos_specific_tests():
    """macOS特定测试"""
    logger.info("运行macOS特定测试")
    # macOS特定的测试代码...

def linux_specific_tests():
    """Linux特定测试"""
    logger.info("运行Linux特定测试")
    # Linux特定的测试代码...

# 添加平台特定测试方法到测试类
setattr(TestCursorClientMCPIntegration, "windows_specific_tests", staticmethod(windows_specific_tests))
setattr(TestCursorClientMCPIntegration, "macos_specific_tests", staticmethod(macos_specific_tests))
setattr(TestCursorClientMCPIntegration, "linux_specific_tests", staticmethod(linux_specific_tests))

if __name__ == "__main__":
    logger.info(f"开始跨平台测试 - {platform.system()}")
    unittest.main() 