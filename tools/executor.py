#!/usr/bin/env python3
"""
Executor智能体

Executor负责执行Planner分配的任务，实现具体功能，进行测试和验证，并提供执行反馈。
"""

import os
import sys
import json
import uuid
import logging
import datetime
import time
import threading
import queue
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

# 添加父级目录到sys.path，确保能找到依赖模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 导入通信管理器
try:
    from tools.communication_manager import CommunicationManager, QoSLevel, Priority
except ImportError:
    # 尝试相对导入
    try:
        from .communication_manager import CommunicationManager, QoSLevel, Priority
    except ImportError:
        # 尝试直接导入
        from communication_manager import CommunicationManager, QoSLevel, Priority

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("executor")

class Task:
    """任务数据结构，与Planner中的Task定义保持一致"""
    
    def __init__(self, task_id: str, description: str, priority: str = "medium", 
                 deadline: Optional[str] = None, parent_id: Optional[str] = None,
                 status: str = "pending"):
        self.task_id = task_id
        self.description = description
        self.priority = priority  # high, medium, low
        self.deadline = deadline
        self.parent_id = parent_id
        self.status = status  # pending, assigned, running, completed, failed
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at
        self.assigned_to = None
        self.subtasks: List[str] = []
        self.dependencies: List[str] = []
        self.resources: List[str] = []
        self.result = None
        self.metadata: Dict[str, Any] = {}
        self.instructions: List[str] = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建任务对象"""
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            priority=data.get("priority", "medium"),
            deadline=data.get("deadline"),
            parent_id=data.get("parent_id"),
            status=data.get("status", "pending")
        )
        task.created_at = data.get("created_at", task.created_at)
        task.updated_at = data.get("updated_at", task.updated_at)
        task.assigned_to = data.get("assigned_to")
        task.subtasks = data.get("subtasks", [])
        task.dependencies = data.get("dependencies", [])
        task.resources = data.get("resources", [])
        task.result = data.get("result")
        task.metadata = data.get("metadata", {})
        task.instructions = data.get("instructions", [])
        return task
    
    def to_dict(self) -> Dict[str, Any]:
        """将任务转换为字典表示"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "priority": self.priority,
            "deadline": self.deadline,
            "parent_id": self.parent_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "assigned_to": self.assigned_to,
            "subtasks": self.subtasks,
            "dependencies": self.dependencies,
            "resources": self.resources,
            "result": self.result,
            "metadata": self.metadata,
            "instructions": self.instructions
        }
    
    def __str__(self) -> str:
        return f"Task({self.task_id}, {self.description}, {self.status})"

class TaskExecutor:
    """任务执行器，负责实际执行特定类型的任务"""
    
    def __init__(self, name: str):
        self.name = name
        self.executor_id = f"executor-{name}"
        self.capabilities: List[str] = []
    
    def can_execute(self, task: Task) -> bool:
        """检查是否能够执行特定任务"""
        # 默认实现：检查任务描述是否包含能力关键词
        for capability in self.capabilities:
            if capability.lower() in task.description.lower():
                return True
        return False
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """执行任务并返回结果"""
        # 基类中的默认实现
        logger.info(f"{self.name} 执行任务: {task.description}")
        return {
            "status": "completed",
            "message": f"任务 {task.task_id} 由 {self.name} 完成",
            "result": None
        }

class CodeExecutor(TaskExecutor):
    """代码执行器，用于执行编码相关任务"""
    
    def __init__(self):
        super().__init__("code")
        self.capabilities = ["编码", "开发", "实现", "编程", "代码"]
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """执行编码任务"""
        logger.info(f"代码执行器处理任务: {task.description}")
        
        # 模拟编码过程
        time.sleep(1)  # 模拟工作时间
        
        return {
            "status": "completed",
            "message": f"已完成代码实现: {task.description}",
            "result": {
                "code_files": ["module1.py", "module2.py"],
                "code_quality": "良好",
                "tests_passed": True
            }
        }

class TestExecutor(TaskExecutor):
    """测试执行器，用于执行测试相关任务"""
    
    def __init__(self):
        super().__init__("test")
        self.capabilities = ["测试", "验证", "质量", "QA"]
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """执行测试任务"""
        logger.info(f"测试执行器处理任务: {task.description}")
        
        # 模拟测试过程
        time.sleep(1.5)  # 模拟工作时间
        
        return {
            "status": "completed",
            "message": f"已完成测试: {task.description}",
            "result": {
                "test_cases": 15,
                "passed": 14,
                "failed": 1,
                "coverage": "92%"
            }
        }

class DocExecutor(TaskExecutor):
    """文档执行器，用于执行文档相关任务"""
    
    def __init__(self):
        super().__init__("doc")
        self.capabilities = ["文档", "报告", "wiki", "说明"]
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """执行文档任务"""
        logger.info(f"文档执行器处理任务: {task.description}")
        
        # 模拟文档编写过程
        time.sleep(0.8)  # 模拟工作时间
        
        return {
            "status": "completed",
            "message": f"已完成文档: {task.description}",
            "result": {
                "doc_files": ["README.md", "API.md"],
                "word_count": 1200,
                "quality": "高"
            }
        }

class GenericExecutor(TaskExecutor):
    """通用执行器，可以处理未分类的常规任务"""
    
    def __init__(self):
        super().__init__("generic")
        self.capabilities = []  # 空列表表示可以尝试处理任何任务
    
    def can_execute(self, task: Task) -> bool:
        """通用执行器可以尝试执行任何任务"""
        return True
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """执行通用任务"""
        logger.info(f"通用执行器处理任务: {task.description}")
        
        # 模拟任务执行
        time.sleep(1)  # 模拟工作时间
        
        return {
            "status": "completed",
            "message": f"已完成通用任务: {task.description}",
            "result": {
                "details": "任务已按要求完成"
            }
        }

class Executor:
    """Executor智能体实现"""
    
    def __init__(self, executor_id: str = "executor-main"):
        """初始化Executor
        
        Args:
            executor_id: Executor的唯一标识符
        """
        self.executor_id = executor_id
        self.task_queue = queue.PriorityQueue()  # 优先级队列
        self.active_tasks: Dict[str, Task] = {}  # 正在处理的任务
        self.completed_tasks: Dict[str, Task] = {}  # 已完成的任务
        self.message_queue = queue.Queue()  # 消息队列
        self.shutdown_flag = threading.Event()
        self.processing_thread = None
        self.task_thread = None
        self.max_concurrent_tasks = 5
        self.version = "1.0.0"
        
        # 注册任务执行器
        self.executors: List[TaskExecutor] = [
            CodeExecutor(),
            TestExecutor(),
            DocExecutor(),
            GenericExecutor()  # 通用执行器放在最后
        ]
        
        logger.info(f"Executor {executor_id} 初始化完成")
    
    def start(self) -> None:
        """启动Executor处理线程和通信管理器"""
        # 启动通信管理器
        self.comm_manager.start()
        
        if (self.processing_thread is not None and self.processing_thread.is_alive()) or \
           (self.task_thread is not None and self.task_thread.is_alive()):
            logger.warning("Executor已经在运行中")
            return
        
        self.shutdown_flag.clear()
        
        # 启动消息处理线程
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # 启动任务执行线程
        self.task_thread = threading.Thread(target=self._process_tasks)
        self.task_thread.daemon = True
        self.task_thread.start()
        
        logger.info(f"Executor {self.executor_id} 已启动")
    
    def stop(self) -> None:
        """停止Executor处理线程和通信管理器"""
        # 停止通信管理器
        self.comm_manager.stop()
        
        if ((self.processing_thread is None or not self.processing_thread.is_alive()) and 
            (self.task_thread is None or not self.task_thread.is_alive())):
            logger.warning("Executor没有在运行")
            return
        
        self.shutdown_flag.set()
        
        # 等待处理线程结束
        if self.processing_thread is not None and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
            if self.processing_thread.is_alive():
                logger.warning("消息处理线程未能正常停止")
        
        # 等待任务线程结束
        if self.task_thread is not None and self.task_thread.is_alive():
            self.task_thread.join(timeout=5.0)
            if self.task_thread.is_alive():
                logger.warning("任务处理线程未能正常停止")
        
        logger.info(f"Executor {self.executor_id} 已停止")
        
        # 保存状态
        self._save_state()
    
    def add_planner(self, planner_id: str, planner_comm) -> None:
        """添加规划器到路由表
        
        Args:
            planner_id: 规划器ID
            planner_comm: 规划器通信管理器
        """
        self.comm_manager.add_route(planner_id, planner_comm)
        logger.info(f"已添加规划器: {planner_id}")
    
    def _calculate_task_priority(self, task: Task) -> int:
        """计算任务的优先级值（数值越小优先级越高）"""
        priority_map = {
            "high": 0,
            "medium": 10,
            "low": 20
        }
        base_priority = priority_map.get(task.priority, 10)
        
        # 考虑任务的等待时间
        wait_time = 0
        if task.created_at:
            # 转换ISO格式时间为时间戳
            created_time = datetime.datetime.fromisoformat(task.created_at).timestamp()
            wait_time = min(10, int((time.time() - created_time) / 3600))  # 每小时增加1点优先级，最多10点
        
        # 依赖任务数量也会影响优先级（依赖越少越先执行）
        dependency_factor = min(5, len(task.dependencies))
        
        return base_priority - wait_time + dependency_factor
    
    def _process_messages(self) -> None:
        """处理消息队列中的消息"""
        while not self.shutdown_flag.is_set():
            try:
                # 消息已由通信管理器处理和分发
                # 这里处理内部消息队列（如果有）
                message = self.message_queue.get(timeout=1.0)
                self._handle_internal_message(message)
                self.message_queue.task_done()
            except queue.Empty:
                # 定期保存状态
                self._save_state()
                continue
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
    
    def _handle_internal_message(self, message: Dict[str, Any]) -> None:
        """处理内部消息队列中的消息"""
        message_type = message.get("type")
        logger.debug(f"处理内部消息: {message_type}")
        
        # 处理内部消息类型
        if message_type == "task_progress":
            task_id = message.get("task_id")
            progress = message.get("progress", 0.0)
            message_text = message.get("message", "")
            self._send_progress_update(task_id, message_text, progress)
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理接收到的消息
        
        注意：这个方法已被通信管理器中的处理器注册替代，
        保留此方法是为了向后兼容
        """
        message_type = message.get("type")
        
        if message_type == "task_assignment":
            self._handle_task_assignment(message)
        elif message_type == "cancel_task":
            self._handle_cancel_task(message)
        elif message_type == "status_request":
            self._handle_status_request(message)
    
    def _handle_task_assignment(self, payload: Dict[str, Any]) -> None:
        """处理任务分配消息"""
        try:
            # 提取任务信息
            task_data = payload.get("task", {})
            instructions = payload.get("instructions", [])
            
            # 验证必要字段
            if not task_data or "task_id" not in task_data or "description" not in task_data:
                logger.error("任务分配消息缺少必要字段")
                return
            
            # 创建任务对象
            task = Task.from_dict(task_data)
            
            # 添加执行指令
            task.instructions = instructions
            
            # 添加到活动任务
            self.active_tasks[task.task_id] = task
            
            # 计算任务优先级并加入队列
            priority_value = self._calculate_task_priority(task)
            self.task_queue.put((priority_value, task.task_id))
            
            logger.info(f"已接收任务: {task.task_id}, {task.description[:50]}...")
            
            # 发送确认消息
            confirmation = {
                "type": "task_accepted",
                "task_id": task.task_id,
                "executor_id": self.executor_id,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # 找出消息来源并回复
            origin_id = payload.get("origin", {}).get("id", "unknown")
            if origin_id != "unknown":
                self.comm_manager.send_message(
                    destination=origin_id,
                    payload=confirmation,
                    qos=QoSLevel.LEVEL_2,
                    priority=Priority.HIGH
                )
            
            # 保存状态
            self._save_state()
            
        except Exception as e:
            logger.error(f"处理任务分配消息时出错: {e}")
    
    def _handle_cancel_task(self, payload: Dict[str, Any]) -> None:
        """处理取消任务消息"""
        task_id = payload.get("task_id")
        reason = payload.get("reason", "用户请求取消")
        
        if not task_id:
            logger.error("取消任务消息缺少task_id字段")
            return
        
        # 检查任务是否存在
        task = self.active_tasks.get(task_id)
        if task is None:
            logger.warning(f"要取消的任务不存在: {task_id}")
            
            # 发送取消确认
            response = {
                "type": "task_cancel_response",
                "task_id": task_id,
                "status": "not_found",
                "message": f"任务 {task_id} 不存在或已完成"
            }
        else:
            # 更新任务状态
            task.update_status("cancelled")
            task.result = {"cancelled": True, "reason": reason}
            
            # 将任务从活动任务移动到已完成任务
            self.completed_tasks[task_id] = task
            self.active_tasks.pop(task_id, None)
            
            logger.info(f"已取消任务: {task_id}, 原因: {reason}")
            
            # 发送取消确认
            response = {
                "type": "task_cancel_response",
                "task_id": task_id,
                "status": "cancelled",
                "message": f"任务 {task_id} 已取消"
            }
        
        # 找出消息来源并回复
        origin_id = payload.get("origin", {}).get("id", "unknown")
        if origin_id != "unknown":
            self.comm_manager.send_message(
                destination=origin_id,
                payload=response,
                qos=QoSLevel.LEVEL_1,
                priority=Priority.MEDIUM
            )
        
        # 保存状态
        self._save_state()
    
    def _handle_status_request(self, payload: Dict[str, Any]) -> None:
        """处理状态请求消息"""
        request_id = payload.get("request_id")
        task_id = payload.get("task_id")
        
        # 准备响应
        if task_id:
            # 查询特定任务状态
            task = self.active_tasks.get(task_id)
            if task is None:
                task = self.completed_tasks.get(task_id)
            
            if task is None:
                status = {"status": "not_found", "task_id": task_id}
            else:
                status = {
                    "task_id": task_id,
                    "status": task.status,
                    "updated_at": task.updated_at,
                    "result": task.result
                }
        else:
            # 查询整体状态
            active_count = len(self.active_tasks)
            completed_count = len(self.completed_tasks)
            queue_size = self.task_queue.qsize()
            
            status = {
                "active_tasks": active_count,
                "completed_tasks": completed_count,
                "queued_tasks": queue_size,
                "executor_id": self.executor_id,
                "executor_status": "running" if not self.shutdown_flag.is_set() else "stopping",
                "capabilities": [executor.name for executor in self.executors]
            }
        
        # 发送响应
        response = {
            "type": "status_response",
            "request_id": request_id,
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 找出消息来源并回复
        origin_id = payload.get("origin", {}).get("id", "unknown")
        if origin_id != "unknown":
            self.comm_manager.send_message(
                destination=origin_id,
                payload=response,
                qos=QoSLevel.LEVEL_1,
                priority=Priority.MEDIUM
            )
    
    def _process_tasks(self) -> None:
        """处理任务队列中的任务"""
        while not self.shutdown_flag.is_set():
            try:
                # 从任务队列获取优先级最高的任务
                _, task_id = self.task_queue.get(timeout=1.0)
                
                # 获取任务
                task = self.active_tasks.get(task_id)
                if task is None:
                    logger.warning(f"找不到任务: {task_id}")
                    self.task_queue.task_done()
                    continue
                
                # 如果任务状态不是待处理或已分配，跳过
                if task.status not in ["pending", "assigned"]:
                    logger.debug(f"跳过状态为 {task.status} 的任务: {task_id}")
                    self.task_queue.task_done()
                    continue
                
                # 执行任务
                try:
                    self._execute_task(task)
                except Exception as e:
                    logger.error(f"执行任务 {task_id} 时出错: {e}")
                    
                    # 更新任务状态为失败
                    task.update_status("failed")
                    task.result = {"error": str(e)}
                    
                    # 发送任务失败消息
                    self._send_task_failed(task, str(e))
                
                self.task_queue.task_done()
                
            except queue.Empty:
                # 任务队列为空，等待
                continue
            except Exception as e:
                logger.error(f"处理任务队列时出错: {e}")
    
    def _execute_task(self, task: Task) -> None:
        """执行任务"""
        logger.info(f"开始执行任务: {task.task_id}, {task.description[:50]}...")
        
        # 更新任务状态
        task.update_status("running")
        
        # 发送进度更新
        self._send_progress_update(task.task_id, "任务开始执行", 0.0)
        
        # 选择合适的执行器
        executor = self._select_executor(task)
        if executor is None:
            error_msg = f"找不到适合执行任务 {task.task_id} 的执行器"
            logger.error(error_msg)
            
            # 更新任务状态为失败
            task.update_status("failed")
            task.result = {"error": error_msg}
            
            # 发送任务失败消息
            self._send_task_failed(task, error_msg)
            return
        
        logger.info(f"使用 {executor.name} 执行器执行任务 {task.task_id}")
        
        # 发送进度更新
        self._send_progress_update(task.task_id, f"使用 {executor.name} 执行器执行中", 0.25)
        
        # 执行任务
        try:
            start_time = time.time()
            result = executor.execute(task)
            end_time = time.time()
            
            # 记录执行时间
            execution_time = end_time - start_time
            
            # 发送进度更新
            self._send_progress_update(task.task_id, "任务执行完成，处理结果", 0.75)
            
            # 处理执行结果
            if result.get("status") == "completed":
                # 更新任务状态和结果
                task.status = "completed"
                task.result = result.get("result")
                task.updated_at = datetime.datetime.now().isoformat()
                
                # 添加执行时间
                if task.metadata is None:
                    task.metadata = {}
                task.metadata["execution_time"] = execution_time
                
                # 将任务从活动任务移至已完成任务
                self.completed_tasks[task.task_id] = task
                self.active_tasks.pop(task.task_id, None)
                
                logger.info(f"任务 {task.task_id} 已完成，耗时: {execution_time:.2f}秒")
                
                # 发送任务完成消息
                self._send_task_completed(task)
            else:
                # 更新任务状态为失败
                task.update_status("failed")
                task.result = {"error": result.get("message", "未知错误")}
                
                logger.warning(f"任务 {task.task_id} 执行失败: {result.get('message', '未知错误')}")
                
                # 发送任务失败消息
                self._send_task_failed(task, result.get("message", "未知错误"))
            
            # 保存状态
            self._save_state()
            
        except Exception as e:
            logger.error(f"执行任务 {task.task_id} 时出错: {e}")
            
            # 更新任务状态为失败
            task.update_status("failed")
            task.result = {"error": str(e)}
            
            # 发送任务失败消息
            self._send_task_failed(task, str(e))
    
    def _select_executor(self, task: Task) -> Optional[TaskExecutor]:
        """为任务选择合适的执行器"""
        for executor in self.executors:
            if executor.can_execute(task):
                return executor
        return None
    
    def _send_progress_update(self, task_id: str, message: str, progress: float) -> None:
        """发送任务进度更新"""
        if not task_id:
            return
        
        task = self.active_tasks.get(task_id)
        if task is None:
            return
        
        # 准备进度更新消息
        update = {
            "type": "task_progress",
            "task_id": task_id,
            "executor_id": self.executor_id,
            "message": message,
            "progress": progress,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 发送给Planner（如果任务有分配者）
        if task.assigned_to:
            planner_id = task.assigned_to.split("-")[0] + "-main"  # 假设格式为"planner-xxx"
            self.comm_manager.send_message(
                destination=planner_id,
                payload=update,
                qos=QoSLevel.LEVEL_1,  # 进度更新使用QoS1即可
                priority=Priority.LOW
            )
    
    def _send_task_completed(self, task: Task) -> None:
        """发送任务完成消息"""
        if not task:
            return
        
        # 准备任务完成消息
        completion = {
            "type": "task_completed",
            "task_id": task.task_id,
            "executor_id": self.executor_id,
            "result": task.result,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 发送给Planner（如果任务有分配者）
        if task.assigned_to:
            planner_id = task.assigned_to.split("-")[0] + "-main"  # 假设格式为"planner-xxx"
            self.comm_manager.send_message(
                destination=planner_id,
                payload=completion,
                qos=QoSLevel.LEVEL_2,  # 任务完成消息需要可靠传输
                priority=Priority.HIGH
            )
    
    def _send_task_failed(self, task: Task, error: str) -> None:
        """发送任务失败消息"""
        if not task:
            return
        
        # 准备任务失败消息
        failure = {
            "type": "task_failed",
            "task_id": task.task_id,
            "executor_id": self.executor_id,
            "error": error,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 发送给Planner（如果任务有分配者）
        if task.assigned_to:
            planner_id = task.assigned_to.split("-")[0] + "-main"  # 假设格式为"planner-xxx"
            self.comm_manager.send_message(
                destination=planner_id,
                payload=failure,
                qos=QoSLevel.LEVEL_2,  # 任务失败消息需要可靠传输
                priority=Priority.HIGH
            )
    
    def _send_message(self, receiver: str, message: Dict[str, Any]) -> None:
        """发送消息到接收者
        
        注意：这个方法已被通信管理器的send_message方法替代，
        保留此方法是为了向后兼容
        """
        try:
            # 使用通信管理器发送消息
            qos = QoSLevel.LEVEL_1
            priority = Priority.MEDIUM
            
            if message.get("type") in ["task_completed", "task_failed"]:
                qos = QoSLevel.LEVEL_2
                priority = Priority.HIGH
            
            self.comm_manager.send_message(
                destination=receiver,
                payload=message,
                qos=qos,
                priority=priority
            )
        except Exception as e:
            logger.error(f"发送消息时出错: {e}")
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """将消息添加到内部消息队列（供外部调用）"""
        self.message_queue.put(message)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态，如果任务不存在则返回None
        """
        # 首先在活动任务中查找
        task = self.active_tasks.get(task_id)
        if task is None:
            # 在已完成任务中查找
            task = self.completed_tasks.get(task_id)
        
        if task is None:
            return None
        
        # 构建状态信息
        status = {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        
        # 如果任务已完成，添加结果
        if task.status in ["completed", "failed", "cancelled"]:
            status["result"] = task.result
        
        # 如果任务正在执行，添加执行器信息
        if task.status == "running" and "executor" in task.metadata:
            status["executor"] = task.metadata["executor"]
        
        return status
    
    def get_status(self) -> Dict[str, Any]:
        """获取Executor的整体状态"""
        active_count = len(self.active_tasks)
        completed_count = len(self.completed_tasks)
        queue_size = self.task_queue.qsize()
        
        # 计算执行统计信息
        completed_tasks = list(self.completed_tasks.values())
        failed_count = sum(1 for t in completed_tasks if t.status == "failed")
        cancelled_count = sum(1 for t in completed_tasks if t.status == "cancelled")
        success_count = sum(1 for t in completed_tasks if t.status == "completed")
        
        # 计算平均执行时间
        execution_times = [t.metadata.get("execution_time", 0) for t in completed_tasks 
                          if t.status == "completed" and "execution_time" in t.metadata]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # 构建状态信息
        status = {
            "executor_id": self.executor_id,
            "version": self.version,
            "status": "running" if not self.shutdown_flag.is_set() else "stopping",
            "tasks": {
                "active": active_count,
                "queued": queue_size,
                "completed": success_count,
                "failed": failed_count,
                "cancelled": cancelled_count,
                "total_processed": completed_count
            },
            "performance": {
                "avg_execution_time": avg_execution_time,
                "success_rate": success_count / completed_count if completed_count > 0 else 0
            },
            "capabilities": [executor.name for executor in self.executors],
            "communication_stats": self.comm_manager.get_stats(),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return status

    def _save_state(self) -> None:
        """保存Executor状态到文件"""
        try:
            state = {
                "executor_id": self.executor_id,
                "version": "1.0",
                "active_tasks": list(self.active_tasks.keys()),
                "task_queue": [task_id for _, task_id in list(self.task_queue.queue)],
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            state_file = f"{self.executor_id}_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"已保存Executor状态到: {state_file}")
        except Exception as e:
            logger.error(f"保存状态时出错: {e}")
    
    def _load_state(self) -> bool:
        """从文件加载Executor状态"""
        try:
            state_file = f"{self.executor_id}_state.json"
            if not os.path.exists(state_file):
                logger.info(f"状态文件不存在: {state_file}")
                return False
                
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info(f"已从 {state_file} 加载状态")
            return True
        except Exception as e:
            logger.error(f"加载状态时出错: {e}")
            return False

    def is_running(self) -> bool:
        """检查Executor是否正在运行"""
        return (self.processing_thread is not None and 
                self.processing_thread.is_alive() and 
                not self.shutdown_flag.is_set())

def main():
    """主函数，用于测试Executor功能"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Executor智能体")
    parser.add_argument("--id", default="executor-main", help="Executor ID")
    parser.add_argument("--test", action="store_true", help="运行测试")
    args = parser.parse_args()
    
    logger.info(f"启动Executor智能体，ID: {args.id}")
    
    # 创建Executor实例
    executor = Executor(args.id)
    
    if args.test:
        run_test(executor)
    else:
        try:
            # 启动Executor
            executor.start()
            
            # 保持程序运行
            print("Executor已启动。按Ctrl+C停止...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n接收到停止信号，正在停止Executor...")
            executor.stop()
            print("Executor已停止")

def run_test(executor: Executor):
    """运行测试功能"""
    print("----- 开始Executor测试 -----")
    
    # 启动Executor
    executor.start()
    
    # 创建测试任务
    test_task = Task(
        task_id="test-task-1",
        description="测试编码任务：实现用户登录功能",
        priority="high"
    )
    test_task.assign(executor.executor_id)
    test_task.instructions = ["测试指令1", "测试指令2"]
    
    # 添加到活动任务
    executor.active_tasks[test_task.task_id] = test_task
    
    # 将任务添加到队列
    priority_value = executor._calculate_task_priority(test_task)
    executor.task_queue.put((priority_value, test_task.task_id))
    
    print(f"已添加测试任务: {test_task.task_id}")
    
    # 等待任务执行完成
    max_wait = 10  # 最多等待10秒
    for _ in range(max_wait):
        status = executor.get_task_status(test_task.task_id)
        if status and status["status"] in ["completed", "failed"]:
            break
        time.sleep(1)
    
    # 输出任务状态
    status = executor.get_task_status(test_task.task_id)
    if status:
        print("\n任务执行结果:")
        print(f"状态: {status['status']}")
        if "result" in status:
            print(f"结果: {status['result']}")
    
    # 输出Executor状态
    executor_status = executor.get_status()
    print("\nExecutor状态:")
    print(f"活动任务数: {executor_status['tasks']['active']}")
    print(f"已完成任务数: {executor_status['tasks']['completed']}")
    print(f"平均执行时间: {executor_status['performance']['avg_execution_time']:.2f}秒")
    
    # 停止Executor
    executor.stop()
    print("\n----- Executor测试完成 -----")

if __name__ == "__main__":
    main() 