#!/usr/bin/env python3
"""
跨平台测试工具 - 增强版

用于测试Cursor客户端与MCP服务通信的基本功能，专注于连接建立和简单消息传递。
增强的测试流程，支持断言验证和更多测试场景。
"""

import os
import sys
import json
import platform
import logging
import asyncio
import argparse
from pathlib import Path
import time
import uuid
import traceback
import tempfile

# 获取项目根目录
current_dir = Path(__file__).parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("test_cross_platform")

# 导入被测试模块
try:
    from tools.cursor_connect import CursorClient
    from tools.mcp_service import MCPService
except ImportError as e:
    logger.error(f"导入错误: {e}")
    logger.error("请确保当前目录是项目根目录")
    sys.exit(1)

# 测试配置
TEST_PORT = 8766
TEST_TIMEOUT = 30  # 秒

class TestResults:
    """测试结果收集器"""
    
    def __init__(self):
        self.success = True
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def add_result(self, test_name, passed, message=None, error=None):
        """添加测试结果"""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message
        }
        
        if error:
            result["error"] = str(error)
        
        self.results.append(result)
        self.total += 1
        
        if passed:
            self.passed += 1
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.failed += 1
            self.success = False
            error_msg = f"❌ {test_name}: {message}"
            if error:
                error_msg += f" - 错误: {error}"
            logger.error(error_msg)
    
    def summary(self):
        """获取测试结果摘要"""
        return {
            "success": self.success,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": f"{(self.passed / self.total * 100) if self.total > 0 else 0:.2f}%",
            "results": self.results
        }

async def run_basic_tests(host="localhost", port=TEST_PORT):
    """运行基本测试套件"""
    results = TestResults()
    temp_dir = None
    service = None
    client = None
    
    try:
        # 步骤1: 系统信息检查
        logger.info("========== 跨平台客户端连接测试 ==========")
        logger.info(f"平台: {platform.system()} {platform.release()}")
        logger.info(f"Python版本: {platform.python_version()}")
        
        # 创建临时目录
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name)
        logger.info(f"临时目录: {temp_path}")
        
        # 步骤2: 启动MCP服务
        logger.info("步骤1: 启动MCP服务...")
        service = MCPService(host=host, port=port, mock_mode=True)
        await service.start()
        results.add_result("MCP服务启动", True, f"MCP服务已启动，监听: {host}:{port}")
        
        # 等待服务完全启动
        await asyncio.sleep(1)
        
        # 步骤3: 创建客户端并连接
        logger.info("步骤2: 创建客户端并连接...")
        agent_id = f"test-{str(uuid.uuid4())[:8]}"
        client = CursorClient(
            host=host,
            port=port,
            agent_type="test",
            agent_id=agent_id
        )
        
        # 尝试连接
        try:
            await asyncio.wait_for(client.connect(), timeout=10)
            results.add_result("客户端连接", True, f"客户端连接成功，ID: {client.client_id}")
            connected = True
        except Exception as e:
            results.add_result("客户端连接", False, "客户端连接失败", e)
            connected = False
        
        # 如果连接成功，继续测试
        if connected:
            # 步骤4: 发送消息
            logger.info("步骤3: 发送消息...")
            try:
                message_content = {
                    "message_type": "test_message",
                    "data": {
                        "platform": platform.system(),
                        "timestamp": time.time(),
                        "uuid": str(uuid.uuid4())
                    }
                }
                
                # 发送消息
                result = await asyncio.wait_for(
                    client.send_message("executor-mock", message_content),
                    timeout=5
                )
                
                results.add_result("消息发送", result, "消息发送成功" if result else "消息发送失败")
            except Exception as e:
                results.add_result("消息发送", False, "消息发送出错", e)
            
            # 步骤5: 创建任务
            logger.info("步骤4: 创建任务...")
            try:
                task_desc = f"测试任务 - {platform.system()} - {time.time()}"
                response = await asyncio.wait_for(
                    client.create_task(description=task_desc, priority="medium"),
                    timeout=5
                )
                
                task_id = response.get("task_id")
                if task_id:
                    results.add_result("任务创建", True, f"任务创建成功，ID: {task_id}")
                    
                    # 查询任务状态
                    try:
                        status = await asyncio.wait_for(
                            client.query_task(task_id),
                            timeout=5
                        )
                        
                        if status and status.get("task_id") == task_id:
                            results.add_result("任务查询", True, f"任务查询成功，状态: {status.get('status')}")
                        else:
                            results.add_result("任务查询", False, "任务查询返回无效数据")
                    except Exception as e:
                        results.add_result("任务查询", False, "任务查询出错", e)
                else:
                    results.add_result("任务创建", False, "任务ID无效")
            except Exception as e:
                results.add_result("任务创建", False, "任务创建出错", e)
        
        # 步骤6: 文件操作测试
        logger.info("步骤5: 文件操作测试...")
        try:
            # 创建测试文件
            test_file = temp_path / f"test_{platform.system().lower()}_{int(time.time())}.txt"
            test_content = f"平台: {platform.system()}\n时间戳: {time.time()}\n测试ID: {uuid.uuid4()}"
            
            # 写入文件
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_content)
            
            # 验证文件存在
            if test_file.exists():
                results.add_result("文件创建", True, f"文件创建成功: {test_file}")
                
                # 读取文件
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if content == test_content:
                    results.add_result("文件读取", True, "文件内容正确")
                else:
                    results.add_result("文件读取", False, "文件内容不匹配")
                
                # 删除文件
                test_file.unlink()
                results.add_result("文件删除", True, "文件删除成功")
            else:
                results.add_result("文件创建", False, "文件不存在")
        except Exception as e:
            results.add_result("文件操作", False, "文件操作出错", e)
        
        # 步骤7: 环境变量测试
        logger.info("步骤6: 环境变量测试...")
        try:
            # 设置环境变量
            var_name = f"TEST_VAR_{uuid.uuid4().hex[:8]}"
            var_value = f"test_value_{platform.system()}_{time.time()}"
            
            os.environ[var_name] = var_value
            
            # 验证环境变量
            if os.environ.get(var_name) == var_value:
                results.add_result("环境变量设置", True, f"环境变量 {var_name} 设置成功")
                
                # 删除环境变量
                del os.environ[var_name]
                
                if var_name not in os.environ:
                    results.add_result("环境变量删除", True, "环境变量删除成功")
                else:
                    results.add_result("环境变量删除", False, "环境变量删除失败")
            else:
                results.add_result("环境变量设置", False, "环境变量值不匹配")
        except Exception as e:
            results.add_result("环境变量测试", False, "环境变量测试出错", e)
        
        return results
    
    finally:
        # 清理资源
        logger.info("清理资源...")
        
        # 断开客户端连接
        if client and client.connected:
            try:
                await client.disconnect()
                logger.info("客户端已断开连接")
            except Exception as e:
                logger.error(f"断开客户端连接时出错: {e}")
        
        # 停止服务
        if service:
            try:
                await service.stop()
                logger.info("MCP服务已停止")
            except Exception as e:
                logger.error(f"停止MCP服务时出错: {e}")
        
        # 清理临时目录
        if temp_dir:
            try:
                temp_dir.cleanup()
                logger.info("临时目录已清理")
            except Exception as e:
                logger.error(f"清理临时目录时出错: {e}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Cursor客户端跨平台测试工具")
    parser.add_argument("--host", default="localhost", help="MCP服务主机地址")
    parser.add_argument("--port", type=int, default=TEST_PORT, help="MCP服务端口")
    parser.add_argument("--timeout", type=int, default=TEST_TIMEOUT, help="测试超时时间（秒）")
    args = parser.parse_args()
    
    try:
        # 运行基本测试
        results = await asyncio.wait_for(
            run_basic_tests(host=args.host, port=args.port),
            timeout=args.timeout
        )
        
        # 输出测试摘要
        summary = results.summary()
        logger.info("\n========== 测试结果摘要 ==========")
        logger.info(f"总测试数: {summary['total']}")
        logger.info(f"通过数量: {summary['passed']}")
        logger.info(f"失败数量: {summary['failed']}")
        logger.info(f"成功率: {summary['success_rate']}")
        logger.info("===================================")
        
        return 0 if summary['success'] else 1
    
    except asyncio.TimeoutError:
        logger.error(f"测试超时 ({args.timeout}秒)")
        return 1
    except Exception as e:
        logger.critical(f"测试过程中发生严重错误: {e}")
        logger.critical(traceback.format_exc())
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"测试过程中发生严重错误: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1) 