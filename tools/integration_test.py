#!/usr/bin/env python3
"""
MCP服务集成测试脚本

测试MCP服务的WebSocket接口和HTTP接口功能。
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import subprocess
import requests
import websockets
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('integration_test')

# 添加父目录到系统路径以便导入工具模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 服务地址
HTTP_SERVICE_URL = os.environ.get("MCP_HTTP_URL", "http://localhost:8000")
WS_SERVICE_URL = os.environ.get("MCP_WS_URL", "ws://localhost:8765")

# 服务进程
server_process = None

class IntegrationTest:
    """MCP服务集成测试"""
    
    def __init__(self, http_url=HTTP_SERVICE_URL, ws_url=WS_SERVICE_URL):
        """初始化测试类
        
        Args:
            http_url: HTTP接口URL
            ws_url: WebSocket接口URL
        """
        self.http_url = http_url
        self.ws_url = ws_url
        self.success_count = 0
        self.failure_count = 0
        self.skipped_count = 0
        self.tests = []  # 测试结果记录
    
    async def start_server(self):
        """启动MCP服务器"""
        global server_process
        
        # 检查服务是否已经在运行
        try:
            response = requests.get(f"{self.http_url}/health", timeout=2)
            if response.status_code == 200:
                logger.info("MCP服务已在运行")
                return True
        except requests.RequestException:
            logger.info("MCP服务未运行，尝试启动...")
        
        # 启动服务
        try:
            server_cmd = [sys.executable, "-m", "multi_agent_mcp", "--host", "0.0.0.0"]
            server_process = subprocess.Popen(
                server_cmd,
                cwd=str(parent_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待服务启动
            for _ in range(30):  # 最多等待30秒
                try:
                    response = requests.get(f"{self.http_url}/health", timeout=2)
                    if response.status_code == 200:
                        logger.info("MCP服务已成功启动")
                        return True
                except requests.RequestException:
                    pass
                await asyncio.sleep(1)
            
            logger.error("MCP服务启动超时")
            return False
        except Exception as e:
            logger.error(f"启动MCP服务时出错: {e}")
            return False
    
    async def stop_server(self):
        """停止MCP服务器"""
        global server_process
        
        if server_process:
            logger.info("正在停止MCP服务...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            server_process = None
            logger.info("MCP服务已停止")
    
    def run_test(self, test_func, name=None):
        """运行单个测试
        
        Args:
            test_func: 测试函数
            name: 测试名称
        """
        test_name = name or test_func.__name__
        logger.info(f"开始测试: {test_name}")
        
        start_time = time.time()
        try:
            result = test_func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            logger.error(f"测试 {test_name} 失败: {e}")
        
        elapsed = time.time() - start_time
        
        # 记录测试结果
        test_result = {
            "name": test_name,
            "success": success,
            "error": error,
            "elapsed": elapsed
        }
        self.tests.append(test_result)
        
        # 更新计数
        if success:
            self.success_count += 1
            logger.info(f"测试 {test_name} 成功! 耗时: {elapsed:.4f}秒")
        else:
            self.failure_count += 1
            logger.error(f"测试 {test_name} 失败! 耗时: {elapsed:.4f}秒")
        
        return success
    
    async def run_async_test(self, test_func, name=None):
        """运行异步测试
        
        Args:
            test_func: 异步测试函数
            name: 测试名称
        """
        test_name = name or test_func.__name__
        logger.info(f"开始异步测试: {test_name}")
        
        start_time = time.time()
        try:
            result = await test_func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            logger.error(f"异步测试 {test_name} 失败: {e}")
        
        elapsed = time.time() - start_time
        
        # 记录测试结果
        test_result = {
            "name": test_name,
            "success": success,
            "error": error,
            "elapsed": elapsed
        }
        self.tests.append(test_result)
        
        # 更新计数
        if success:
            self.success_count += 1
            logger.info(f"异步测试 {test_name} 成功! 耗时: {elapsed:.4f}秒")
        else:
            self.failure_count += 1
            logger.error(f"异步测试 {test_name} 失败! 耗时: {elapsed:.4f}秒")
        
        return success
    
    def test_http_health(self):
        """测试HTTP健康检查接口"""
        response = requests.get(f"{self.http_url}/health")
        assert response.status_code == 200, f"健康检查失败，状态码: {response.status_code}"
        
        data = response.json()
        assert "status" in data, "健康检查响应缺少status字段"
        assert "components" in data, "健康检查响应缺少components字段"
        
        return True
    
    def test_http_list_tools(self):
        """测试HTTP工具列表接口"""
        response = requests.get(f"{self.http_url}/tools")
        assert response.status_code == 200, f"获取工具列表失败，状态码: {response.status_code}"
        
        data = response.json()
        assert "tools" in data, "工具列表响应缺少tools字段"
        assert isinstance(data["tools"], list), "tools字段不是列表"
        assert len(data["tools"]) > 0, "工具列表为空"
        
        # 检查工具项
        tool = data["tools"][0]
        assert "name" in tool, "工具项缺少name字段"
        assert "description" in tool, "工具项缺少description字段"
        assert "parameters" in tool, "工具项缺少parameters字段"
        
        return True
    
    def test_http_memory_operations(self):
        """测试HTTP记忆银行操作"""
        # 创建测试文件
        test_file = f"test_http_{int(time.time())}.md"
        test_content = f"# HTTP测试文件\n\n这是通过HTTP接口创建的测试文件。\n创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 创建文件
        response = requests.post(
            f"{self.http_url}/tools/create_memory_file",
            json={"file_path": test_file, "content": test_content}
        )
        assert response.status_code == 200, f"创建文件失败，状态码: {response.status_code}"
        assert "已成功创建" in response.text, f"创建文件响应不符合预期: {response.text}"
        
        # 读取文件
        response = requests.post(
            f"{self.http_url}/tools/read_memory",
            json={"file_path": test_file}
        )
        assert response.status_code == 200, f"读取文件失败，状态码: {response.status_code}"
        assert "HTTP测试文件" in response.text, f"读取文件内容不符合预期: {response.text}"
        
        # 更新文件
        updated_content = test_content + "\n\n更新时间: " + time.strftime('%Y-%m-%d %H:%M:%S')
        response = requests.post(
            f"{self.http_url}/tools/update_memory",
            json={"file_path": test_file, "content": updated_content}
        )
        assert response.status_code == 200, f"更新文件失败，状态码: {response.status_code}"
        assert "已成功更新" in response.text, f"更新文件响应不符合预期: {response.text}"
        
        # 列出文件
        response = requests.post(
            f"{self.http_url}/tools/list_memory_files",
            json={}
        )
        assert response.status_code == 200, f"列出文件失败，状态码: {response.status_code}"
        files = json.loads(response.text)
        assert isinstance(files, list), "文件列表不是列表"
        assert test_file in files, f"文件列表中找不到测试文件 {test_file}"
        
        return True
    
    def test_http_task_operations(self):
        """测试HTTP任务管理操作"""
        # 创建任务
        task_desc = f"HTTP测试任务 {time.strftime('%Y%m%d%H%M%S')}"
        response = requests.post(
            f"{self.http_url}/tools/create_task",
            json={"description": task_desc, "priority": "medium"}
        )
        assert response.status_code == 200, f"创建任务失败，状态码: {response.status_code}"
        
        result = json.loads(response.text)
        assert "task_id" in result, "创建任务响应缺少task_id字段"
        assert "status" in result, "创建任务响应缺少status字段"
        
        task_id = result["task_id"]
        
        # 获取任务状态
        response = requests.post(
            f"{self.http_url}/tools/get_task_status",
            json={"task_id": task_id}
        )
        assert response.status_code == 200, f"获取任务状态失败，状态码: {response.status_code}"
        
        task_status = json.loads(response.text)
        if "error" not in task_status:
            assert "id" in task_status, "任务状态缺少id字段"
            assert "description" in task_status, "任务状态缺少description字段"
            assert task_status["description"] == task_desc, f"任务描述不符合预期: {task_status['description']}"
        
        # 列出所有任务
        response = requests.post(
            f"{self.http_url}/tools/list_tasks",
            json={}
        )
        assert response.status_code == 200, f"列出任务失败，状态码: {response.status_code}"
        
        tasks = json.loads(response.text)
        assert isinstance(tasks, list), "任务列表不是列表"
        
        return True
    
    def test_http_analyze_task(self):
        """测试HTTP任务分析操作"""
        response = requests.post(
            f"{self.http_url}/tools/analyze_task",
            json={"task_description": "创建一个简单的待办事项应用，包含添加、删除和标记完成功能"}
        )
        assert response.status_code == 200, f"分析任务失败，状态码: {response.status_code}"
        
        result = json.loads(response.text)
        assert "title" in result, "任务分析结果缺少title字段"
        assert "description" in result, "任务分析结果缺少description字段"
        assert "subtasks" in result, "任务分析结果缺少subtasks字段"
        assert isinstance(result["subtasks"], list), "subtasks不是列表"
        assert len(result["subtasks"]) > 0, "子任务列表为空"
        
        return True
    
    async def test_ws_connection(self):
        """测试WebSocket连接"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # 接收欢迎消息
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome)
                
                assert "type" in welcome_data, "欢迎消息缺少type字段"
                assert welcome_data["type"] == "welcome", f"欢迎消息类型不符合预期: {welcome_data['type']}"
                assert "client_id" in welcome_data, "欢迎消息缺少client_id字段"
                
                return True
        except asyncio.TimeoutError:
            raise Exception("WebSocket连接超时")
        except Exception as e:
            raise Exception(f"WebSocket连接失败: {e}")
    
    async def test_ws_agent_registration(self):
        """测试WebSocket智能体注册"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # 接收欢迎消息
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                # 发送注册消息
                register_msg = {
                    "type": "register",
                    "agent_type": "planner",
                    "agent_id": f"test-planner-{int(time.time())}"
                }
                await websocket.send(json.dumps(register_msg))
                
                # 接收注册确认
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                assert "type" in response_data, "注册响应缺少type字段"
                assert response_data["type"] == "registered", f"注册响应类型不符合预期: {response_data['type']}"
                assert "agent_id" in response_data, "注册响应缺少agent_id字段"
                assert "agent_type" in response_data, "注册响应缺少agent_type字段"
                
                return True
        except asyncio.TimeoutError:
            raise Exception("WebSocket注册超时")
        except Exception as e:
            raise Exception(f"WebSocket注册失败: {e}")
    
    async def test_ws_create_task(self):
        """测试WebSocket创建任务"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # 接收欢迎消息
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                # 发送注册消息
                register_msg = {
                    "type": "register",
                    "agent_type": "planner",
                    "agent_id": f"test-planner-{int(time.time())}"
                }
                await websocket.send(json.dumps(register_msg))
                
                # 接收注册确认
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                # 发送创建任务消息
                create_task_msg = {
                    "type": "create_task",
                    "description": f"WebSocket测试任务 {time.strftime('%Y%m%d%H%M%S')}",
                    "priority": "medium"
                }
                await websocket.send(json.dumps(create_task_msg))
                
                # 接收任务创建确认
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                assert "type" in response_data, "任务创建响应缺少type字段"
                assert response_data["type"] == "task_created", f"任务创建响应类型不符合预期: {response_data['type']}"
                assert "task_id" in response_data, "任务创建响应缺少task_id字段"
                
                # 可能还会收到任务创建通知
                try:
                    notification = await asyncio.wait_for(websocket.recv(), timeout=2)
                    notification_data = json.loads(notification)
                    assert "type" in notification_data, "通知缺少type字段"
                    assert notification_data["type"] == "notification", f"通知类型不符合预期: {notification_data['type']}"
                except asyncio.TimeoutError:
                    # 忽略通知超时
                    pass
                
                return True
        except asyncio.TimeoutError:
            raise Exception("WebSocket任务创建超时")
        except Exception as e:
            raise Exception(f"WebSocket任务创建失败: {e}")
    
    async def test_ws_agent_message(self):
        """测试WebSocket智能体间消息传递"""
        try:
            # 创建两个WebSocket连接
            async with websockets.connect(self.ws_url) as ws1, \
                       websockets.connect(self.ws_url) as ws2:
                # 接收欢迎消息
                welcome1 = await asyncio.wait_for(ws1.recv(), timeout=5)
                welcome2 = await asyncio.wait_for(ws2.recv(), timeout=5)
                
                welcome1_data = json.loads(welcome1)
                welcome2_data = json.loads(welcome2)
                
                # 发送注册消息
                agent1_id = f"test-planner-{int(time.time())}"
                register_msg1 = {
                    "type": "register",
                    "agent_type": "planner",
                    "agent_id": agent1_id
                }
                await ws1.send(json.dumps(register_msg1))
                
                agent2_id = f"test-executor-{int(time.time())}"
                register_msg2 = {
                    "type": "register",
                    "agent_type": "executor",
                    "agent_id": agent2_id
                }
                await ws2.send(json.dumps(register_msg2))
                
                # 接收注册确认
                response1 = await asyncio.wait_for(ws1.recv(), timeout=5)
                response2 = await asyncio.wait_for(ws2.recv(), timeout=5)
                
                # 发送消息
                message = f"测试消息 {time.strftime('%Y%m%d%H%M%S')}"
                agent_msg = {
                    "type": "agent_message",
                    "target_id": agent2_id,
                    "content": message
                }
                await ws1.send(json.dumps(agent_msg))
                
                # 接收消息发送确认
                send_confirm = await asyncio.wait_for(ws1.recv(), timeout=5)
                send_confirm_data = json.loads(send_confirm)
                
                assert "type" in send_confirm_data, "消息发送确认缺少type字段"
                assert send_confirm_data["type"] == "message_sent", f"消息发送确认类型不符合预期: {send_confirm_data['type']}"
                
                # 接收消息
                received_msg = await asyncio.wait_for(ws2.recv(), timeout=5)
                received_msg_data = json.loads(received_msg)
                
                assert "type" in received_msg_data, "接收的消息缺少type字段"
                assert received_msg_data["type"] == "message", f"接收的消息类型不符合预期: {received_msg_data['type']}"
                assert "sender_id" in received_msg_data, "接收的消息缺少sender_id字段"
                assert received_msg_data["sender_id"] == agent1_id, f"消息发送者ID不符合预期: {received_msg_data['sender_id']}"
                assert "content" in received_msg_data, "接收的消息缺少content字段"
                assert received_msg_data["content"] == message, f"消息内容不符合预期: {received_msg_data['content']}"
                
                return True
        except asyncio.TimeoutError:
            raise Exception("WebSocket消息传递超时")
        except Exception as e:
            raise Exception(f"WebSocket消息传递失败: {e}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始集成测试...")
        
        # 启动服务器
        if not await self.start_server():
            logger.error("无法启动MCP服务，测试中止")
            return False
        
        # HTTP接口测试
        logger.info("开始HTTP接口测试...")
        http_tests = [
            self.test_http_health,
            self.test_http_list_tools,
            self.test_http_memory_operations,
            self.test_http_task_operations,
            self.test_http_analyze_task
        ]
        
        for test in http_tests:
            self.run_test(test)
        
        # WebSocket接口测试
        logger.info("开始WebSocket接口测试...")
        ws_tests = [
            self.test_ws_connection,
            self.test_ws_agent_registration,
            self.test_ws_create_task,
            self.test_ws_agent_message
        ]
        
        for test in ws_tests:
            await self.run_async_test(test)
        
        # 输出测试结果
        total = self.success_count + self.failure_count + self.skipped_count
        logger.info("测试完成!")
        logger.info(f"总计: {total} 测试")
        logger.info(f"成功: {self.success_count} 测试")
        logger.info(f"失败: {self.failure_count} 测试")
        logger.info(f"跳过: {self.skipped_count} 测试")
        
        # 输出详细测试结果
        logger.info("详细测试结果:")
        for i, test in enumerate(self.tests):
            status = "成功" if test["success"] else "失败"
            error = f" - {test['error']}" if not test["success"] and test["error"] else ""
            logger.info(f"{i+1}. {test['name']}: {status} (耗时: {test['elapsed']:.4f}秒){error}")
        
        return self.failure_count == 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务集成测试")
    parser.add_argument("--http-url", default=HTTP_SERVICE_URL, help="HTTP接口URL")
    parser.add_argument("--ws-url", default=WS_SERVICE_URL, help="WebSocket接口URL")
    parser.add_argument("--no-server", action="store_true", help="不启动服务器，假设服务已在运行")
    args = parser.parse_args()
    
    # 创建测试实例
    test = IntegrationTest(http_url=args.http_url, ws_url=args.ws_url)
    
    try:
        # 运行测试
        success = asyncio.run(test.run_all_tests())
        
        # 退出码
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 1
    finally:
        # 如果我们启动了服务器，停止它
        if not args.no_server and server_process:
            asyncio.run(test.stop_server())

if __name__ == "__main__":
    sys.exit(main()) 