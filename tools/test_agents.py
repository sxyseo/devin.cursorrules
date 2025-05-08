#!/usr/bin/env python3
"""
多智能体协作框架测试脚本

用于测试Planner和Executor智能体之间的通信和协作功能，
包括任务分配、执行、状态更新和错误处理。
"""

import os
import sys
import time
import logging
import argparse
import json
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path

# 导入智能体和通信模块
try:
    from communication_manager import CommunicationManager, QoSLevel, Priority
    from planner import Planner
    from executor import Executor
except ImportError:
    # 添加tools目录到路径
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from tools.communication_manager import CommunicationManager, QoSLevel, Priority
    from tools.planner import Planner
    from tools.executor import Executor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("test_agents")

# 测试配置
TEST_CONFIG = {
    "planner_id": "planner-test",
    "executor_id": "executor-test",
    "test_task_description": "测试任务：实现多智能体通信系统",
    "complex_task_description": "开发一个完整的多智能体框架，包含记忆管理、通信协议和错误处理机制",
    "test_timeout": 30  # 测试超时时间（秒）
}

def setup_agents() -> tuple:
    """
    设置测试环境，创建Planner和Executor实例
    
    Returns:
        tuple: (planner, executor) - 创建的Planner和Executor实例
    """
    logger.info("开始设置测试环境...")
    
    # 创建Planner实例，防止在__init__中调用_register_message_handlers
    # 保存原始方法
    original_register = Planner._register_message_handlers
    
    # 临时替换为空方法
    Planner._register_message_handlers = lambda self: None
    
    try:
        # 创建Planner实例
        planner = Planner(TEST_CONFIG["planner_id"])
        
        # 恢复原始方法
        Planner._register_message_handlers = original_register
        
        # 创建Executor实例
        executor = Executor(TEST_CONFIG["executor_id"])
        
        # 为Planner和Executor添加通信管理器属性（如果尚未存在）
        if not hasattr(planner, 'comm_manager'):
            planner.comm_manager = CommunicationManager(planner.planner_id, "planner")
        
        if not hasattr(executor, 'comm_manager'):
            executor.comm_manager = CommunicationManager(executor.executor_id, "executor")
        
        # 为Executor添加_save_state方法（如果不存在）
        if not hasattr(executor, '_save_state'):
            def save_state(self):
                """保存执行器状态"""
                try:
                    state_file = f"{self.executor_id}_state.json"
                    state = {
                        "executor_id": self.executor_id,
                        "pending_tasks": getattr(self, "pending_tasks", {}),
                        "completed_tasks": getattr(self, "completed_tasks", {})
                    }
                    with open(state_file, 'w') as f:
                        json.dump(state, f)
                except Exception as e:
                    logger.warning(f"保存状态失败: {e}")
            
            # 将方法绑定到executor实例
            import types
            executor._save_state = types.MethodType(save_state, executor)
        
        # 添加自定义的状态请求处理器
        def handle_status_request(payload):
            logger.info(f"收到状态请求: {payload}")
            request_id = payload.get("request_id", str(uuid.uuid4()))
            origin_id = payload.get("origin", {}).get("id", "unknown")
            
            # 准备响应
            status = {
                "status": "running",
                "timestamp": time.time()
            }
            
            # 发送响应
            response = {
                "type": "status_response",
                "request_id": request_id,
                "status": status,
                "timestamp": time.time()
            }
            
            if origin_id != "unknown" and hasattr(planner.comm_manager, "send_message"):
                planner.comm_manager.send_message(
                    destination=origin_id,
                    payload=response,
                    qos=QoSLevel.LEVEL_1,
                    priority=Priority.MEDIUM
                )
            
            return status
        
        # 注册安全的消息处理器
        # 仅注册必要的处理器，避免调用内置方法
        handlers = {
            "create_task": planner._handle_create_task if hasattr(planner, "_handle_create_task") else None,
            "update_task": planner._handle_update_task if hasattr(planner, "_handle_update_task") else None,
            "task_completed": planner._handle_task_completed if hasattr(planner, "_handle_task_completed") else None,
            "task_failed": planner._handle_task_failed if hasattr(planner, "_handle_task_failed") else None,
            "request_plan": planner._handle_request_plan if hasattr(planner, "_handle_request_plan") else None,
            "status_request": handle_status_request  # 使用自定义的处理器
        }
        
        # 只注册存在的处理器
        for msg_type, handler in handlers.items():
            if handler and hasattr(planner.comm_manager, "register_handler"):
                planner.comm_manager.register_handler(msg_type, handler)
        
        # 为Executor添加处理test_message的处理器
        def handle_test_message(payload):
            logger.info(f"Executor收到测试消息: {payload}")
            return {"status": "received", "message": "测试消息已接收"}
        
        # 注册测试消息处理器到Executor
        if hasattr(executor.comm_manager, "register_handler"):
            executor.comm_manager.register_handler("test_message", handle_test_message)
        
        # 建立相互的路由
        planner.comm_manager.add_route(executor.executor_id, executor.comm_manager)
        executor.comm_manager.add_route(planner.planner_id, planner.comm_manager)
        
        # 为Planner添加Executor
        planner.add_executor(executor.executor_id, executor.comm_manager)
        
        # 为Executor添加Planner（如果该方法存在）
        if hasattr(executor, 'add_planner'):
            executor.add_planner(planner.planner_id, planner.comm_manager)
        
        # 启动智能体
        planner.start()
        executor.start()
        
        logger.info(f"测试环境设置完成: Planner({planner.planner_id}) 和 Executor({executor.executor_id}) 已创建并启动")
        
        return planner, executor
    except Exception as e:
        # 确保恢复原始方法
        Planner._register_message_handlers = original_register
        logger.error(f"设置测试环境时出错: {str(e)}")
        raise

def teardown_agents(planner: Planner, executor: Executor) -> None:
    """
    清理测试环境，停止Planner和Executor
    
    Args:
        planner: Planner实例
        executor: Executor实例
    """
    logger.info("正在清理测试环境...")
    
    # 停止智能体
    try:
        if hasattr(planner, 'stop'):
            planner.stop()
    except Exception as e:
        logger.warning(f"停止Planner时出错: {e}")
    
    try:
        if hasattr(executor, 'stop'):
            executor.stop()
    except Exception as e:
        logger.warning(f"停止Executor时出错: {e}")
    
    # 删除状态文件
    try:
        planner_state_file = f"{planner.planner_id}_state.json"
        if os.path.exists(planner_state_file):
            os.remove(planner_state_file)
            logger.info(f"已删除Planner状态文件: {planner_state_file}")
        
        executor_state_file = f"{executor.executor_id}_state.json"
        if os.path.exists(executor_state_file):
            os.remove(executor_state_file)
            logger.info(f"已删除Executor状态文件: {executor_state_file}")
    except Exception as e:
        logger.warning(f"清理状态文件时出错: {e}")
    
    logger.info("测试环境清理完成")

def test_communication(planner: Planner, executor: Executor) -> bool:
    """
    测试智能体之间的通信系统，特别是QoS和消息确认
    
    Args:
        planner: Planner实例
        executor: Executor实例
        
    Returns:
        bool: 测试是否成功
    """
    logger.info("开始测试通信系统...")
    
    try:
        # 测试不同QoS级别的消息传递
        qos_levels = [QoSLevel.LEVEL_1, QoSLevel.LEVEL_2, QoSLevel.LEVEL_3]
        for qos in qos_levels:
            # 构建测试消息
            test_payload = {
                "type": "test_message",
                "content": f"测试QoS级别 {qos.value}",
                "timestamp": time.time()
            }
            
            # 发送消息
            message_id = planner.comm_manager.send_message(
                destination=executor.executor_id,
                payload=test_payload,
                qos=qos,
                priority=Priority.MEDIUM
            )
            
            logger.info(f"发送测试消息 {message_id}，QoS级别: {qos.value}")
            
            # 给一些时间让消息处理
            time.sleep(1)
            
            # 检查消息是否被确认（QoS 2和3）
            if qos in [QoSLevel.LEVEL_2, QoSLevel.LEVEL_3]:
                # 检查是否已从待确认消息中移除
                confirmed = message_id not in planner.comm_manager.pending_messages
                logger.info(f"QoS级别 {qos.value} 消息确认状态: {'已确认' if confirmed else '未确认'}")
                
                if not confirmed:
                    logger.error(f"QoS级别 {qos.value} 的消息没有被确认")
                    return False
        
        # 测试状态持久化
        logger.info("测试状态持久化...")
        
        # 创建一个测试任务
        task_id = planner.create_task("测试状态持久化任务", "medium")
        logger.info(f"创建测试任务: {task_id}")
        
        # 保存状态
        if hasattr(planner, '_save_state'):
            planner._save_state()
        
        # 检查状态文件是否存在
        state_file = f"{planner.planner_id}_state.json"
        if not os.path.exists(state_file):
            logger.error(f"状态文件不存在: {state_file}")
            return False
        
        # 创建新的Planner实例但不初始化处理器
        # 使用与setup_agents相同的技术
        original_register = Planner._register_message_handlers
        Planner._register_message_handlers = lambda self: None
        
        try:
            # 创建临时Planner
            temp_planner = Planner(planner.planner_id)
            
            # 恢复原始方法
            Planner._register_message_handlers = original_register
            
            # 手动加载状态（如果_load_state方法存在）
            if hasattr(temp_planner, '_load_state'):
                temp_planner._load_state()
                
                # 检查任务是否存在于加载的状态中
                if task_id not in temp_planner.task_store:
                    logger.error(f"加载的状态中找不到任务: {task_id}")
                    return False
                
                logger.info("状态持久化测试通过")
            else:
                logger.warning("Planner没有_load_state方法，跳过状态加载测试")
        except Exception as e:
            # 确保恢复原始方法
            Planner._register_message_handlers = original_register
            logger.error(f"测试状态持久化时出错: {e}")
            return False
        
        # 通信测试成功
        logger.info("通信系统测试通过")
        return True
    except Exception as e:
        logger.error(f"测试通信系统过程中出错: {e}")
        return False

def test_simple_task(planner: Planner, executor: Executor) -> bool:
    """
    测试简单任务的创建、分配和执行
    
    Args:
        planner: Planner实例
        executor: Executor实例
        
    Returns:
        bool: 测试是否成功
    """
    logger.info("开始测试简单任务...")
    
    try:
        # 创建简单任务
        task_id = planner.create_task(TEST_CONFIG["test_task_description"], "high")
        logger.info(f"已创建任务: {task_id}")
        
        # 分配任务给执行器
        success = planner.assign_task(task_id, executor.executor_id)
        logger.info(f"任务分配: {'成功' if success else '失败'}")
        
        if not success:
            return False
        
        # 等待任务完成
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < TEST_CONFIG["test_timeout"]:
            # 检查任务状态
            task = planner.get_task(task_id)
            if task and task.status == "completed":
                completed = True
                break
            
            logger.info(f"等待任务完成，当前状态: {task.status if task else 'unknown'}")
            time.sleep(1)
        
        if completed:
            logger.info(f"任务 {task_id} 已完成")
            logger.info(f"任务结果: {task.result}")
            return True
        else:
            logger.error(f"任务 {task_id} 未在规定时间内完成")
            return False
    except Exception as e:
        logger.error(f"测试简单任务过程中出错: {e}")
        return False

def test_complex_task(planner: Planner, executor: Executor) -> bool:
    """
    测试复杂任务的分解、规划和执行
    
    Args:
        planner: Planner实例
        executor: Executor实例
        
    Returns:
        bool: 测试是否成功
    """
    logger.info("开始测试复杂任务...")
    
    try:
        # 创建复杂任务
        main_task_id = planner.create_task(TEST_CONFIG["complex_task_description"], "high")
        logger.info(f"已创建主任务: {main_task_id}")
        
        # 生成任务规划
        plan = planner.generate_plan(main_task_id, ["跨平台兼容", "高效记忆管理"], ["executor-test"])
        logger.info(f"已生成任务规划，包含 {plan.get('subtasks', 0)} 个子任务")
        
        # 获取主任务
        main_task = planner.get_task(main_task_id)
        
        # 检查子任务生成情况
        if not main_task or not main_task.subtasks:
            logger.error("子任务生成失败")
            return False
        
        logger.info(f"已生成 {len(main_task.subtasks)} 个子任务")
        
        # 分配子任务给执行器
        assigned_count = 0
        for subtask_id in main_task.subtasks:
            success = planner.assign_task(subtask_id, executor.executor_id)
            if success:
                assigned_count += 1
        
        logger.info(f"已分配 {assigned_count}/{len(main_task.subtasks)} 个子任务")
        
        # 等待子任务完成
        start_time = time.time()
        completed_subtasks = 0
        
        while time.time() - start_time < TEST_CONFIG["test_timeout"] * 2:  # 复杂任务给双倍时间
            # 检查子任务状态
            completed_subtasks = 0
            for subtask_id in main_task.subtasks:
                subtask = planner.get_task(subtask_id)
                if subtask and subtask.status == "completed":
                    completed_subtasks += 1
            
            if completed_subtasks == len(main_task.subtasks):
                break
            
            logger.info(f"子任务完成进度: {completed_subtasks}/{len(main_task.subtasks)}")
            time.sleep(2)
        
        # 检查主任务是否完成
        main_task = planner.get_task(main_task_id)
        
        if main_task and main_task.status == "completed":
            logger.info(f"主任务 {main_task_id} 已完成")
            return True
        else:
            logger.info(f"子任务完成: {completed_subtasks}/{len(main_task.subtasks)}")
            logger.error(f"主任务未完成，当前状态: {main_task.status if main_task else 'unknown'}")
            return False
    except Exception as e:
        logger.error(f"测试复杂任务过程中出错: {e}")
        return False

def test_error_handling(planner: Planner, executor: Executor) -> bool:
    """
    测试错误处理和恢复机制
    
    Args:
        planner: Planner实例
        executor: Executor实例
        
    Returns:
        bool: 测试是否成功
    """
    logger.info("开始测试错误处理...")
    
    try:
        # 创建一个包含"失败"关键词的任务，使其模拟失败
        task_id = planner.create_task("测试任务：模拟失败的任务", "medium")
        logger.info(f"已创建故意失败的任务: {task_id}")
        
        # 获取任务
        task = planner.get_task(task_id)
        if not task:
            logger.error("任务创建失败")
            return False
        
        # 设置任务元数据，限制重试次数
        task.metadata["max_retries"] = 2
        task.metadata["should_fail"] = True  # 标记为应该失败的任务
        
        # 分配任务给执行器
        success = planner.assign_task(task_id, executor.executor_id)
        logger.info(f"任务分配: {'成功' if success else '失败'}")
        
        if not success:
            return False
        
        # 等待任务重试和失败
        start_time = time.time()
        failed = False
        retry_count = 0
        
        while time.time() - start_time < TEST_CONFIG["test_timeout"]:
            # 检查任务状态
            task = planner.get_task(task_id)
            if not task:
                logger.warning("任务不存在")
                continue
                
            # 记录重试次数
            current_retry = task.metadata.get("retry_count", 0)
            if current_retry > retry_count:
                retry_count = current_retry
                logger.info(f"任务重试次数: {retry_count}")
            
            if task.status == "failed":
                failed = True
                break
            
            logger.info(f"等待任务失败，当前状态: {task.status}")
            time.sleep(1)
        
        if failed:
            logger.info(f"任务 {task_id} 按预期失败")
            logger.info(f"重试次数: {retry_count}, 期望次数: {task.metadata.get('max_retries', 0)}")
            
            # 验证重试次数是否符合预期
            expected_retries = task.metadata.get("max_retries", 0)
            if retry_count >= expected_retries:
                return True
            else:
                logger.error(f"重试次数不符合预期: {retry_count} < {expected_retries}")
                return False
        else:
            logger.error(f"任务 {task_id} 应该失败但没有")
            return False
    except Exception as e:
        logger.error(f"测试错误处理过程中出错: {e}")
        return False

def main():
    """主函数，解析命令行参数并运行测试"""
    parser = argparse.ArgumentParser(description="多智能体协作框架测试")
    parser.add_argument("--test", choices=["simple", "complex", "error", "comm", "all"], 
                      default="all", help="要运行的测试类型")
    args = parser.parse_args()
    
    logger.info("=== 多智能体协作框架测试开始 ===")
    
    # 设置测试环境
    try:
        planner, executor = setup_agents()
    except Exception as e:
        logger.error(f"设置测试环境时出错: {e}")
        return 1
    
    try:
        success = True
        
        # 根据参数运行不同的测试
        if args.test in ["simple", "all"]:
            simple_success = test_simple_task(planner, executor)
            logger.info(f"简单任务测试: {'通过' if simple_success else '失败'}")
            success = success and simple_success
        
        if args.test in ["complex", "all"]:
            complex_success = test_complex_task(planner, executor)
            logger.info(f"复杂任务测试: {'通过' if complex_success else '失败'}")
            success = success and complex_success
        
        if args.test in ["error", "all"]:
            error_success = test_error_handling(planner, executor)
            logger.info(f"错误处理测试: {'通过' if error_success else '失败'}")
            success = success and error_success
            
        if args.test in ["comm", "all"]:
            comm_success = test_communication(planner, executor)
            logger.info(f"通信系统测试: {'通过' if comm_success else '失败'}")
            success = success and comm_success
        
        # 输出总体测试结果
        if success:
            logger.info("=== 所有测试通过! ===")
        else:
            logger.error("=== 测试失败! ===")
        
    finally:
        # 清理测试环境
        try:
            teardown_agents(planner, executor)
        except Exception as e:
            logger.error(f"清理测试环境时出错: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 