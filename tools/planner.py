#!/usr/bin/env python3
"""
Planner智能体

Planner负责高级任务分析、规划和资源调度，使用分层决策架构实现任务分解和资源评估。
"""

import os
import sys
import json
import uuid
import logging
import datetime
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import time
import threading
import queue
import argparse

# 添加父级目录到sys.path，确保能找到依赖模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 导入通信管理器
try:
    from tools.communication_manager import CommunicationManager, QoSLevel, Priority
except ImportError:
    # 尝试相对导入（当tools是当前目录时）
    try:
        from .communication_manager import CommunicationManager, QoSLevel, Priority
    except ImportError:
        # 最后尝试直接导入（当前目录下的模块）
        from communication_manager import CommunicationManager, QoSLevel, Priority

# 导入记忆管理模块（实际系统中使用）
try:
    from tools.memory_manager import read_memory
    from tools.memory_index import MemoryIndex
    memory_available = True
except ImportError:
    # 尝试相对导入
    try:
        from .memory_manager import read_memory
        from .memory_index import MemoryIndex
        memory_available = True
    except ImportError:
        # 尝试直接导入
        try:
            from memory_manager import read_memory
            from memory_index import MemoryIndex
            memory_available = True
        except ImportError:
            memory_available = False
            print("记忆管理模块不可用，将使用模拟实现")

# 导入LLM
try:
    from tools.plan_exec_llm import query_planner_llm
    llm_available = True
except ImportError:
    # 尝试相对导入
    try:
        from .plan_exec_llm import query_planner_llm
        llm_available = True
    except ImportError:
        # 尝试直接导入
        try:
            from plan_exec_llm import query_planner_llm
            llm_available = True
        except ImportError:
            llm_available = False
            print("规划LLM不可用，将使用模拟响应")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("planner")

class Task:
    """表示一个任务的数据结构"""
    
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
            "metadata": self.metadata
        }
    
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
        return task
    
    def add_subtask(self, subtask_id: str) -> None:
        """添加子任务"""
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)
            self.updated_at = datetime.datetime.now().isoformat()
    
    def add_dependency(self, task_id: str) -> None:
        """添加依赖任务"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
            self.updated_at = datetime.datetime.now().isoformat()
    
    def update_status(self, status: str) -> None:
        """更新任务状态"""
        self.status = status
        self.updated_at = datetime.datetime.now().isoformat()
    
    def assign(self, executor_id: str) -> None:
        """分配任务给执行者"""
        self.assigned_to = executor_id
        self.status = "assigned"
        self.updated_at = datetime.datetime.now().isoformat()
    
    def set_result(self, result: Any) -> None:
        """设置任务结果"""
        self.result = result
        self.status = "completed"
        self.updated_at = datetime.datetime.now().isoformat()
    
    def __str__(self) -> str:
        return f"Task({self.task_id}, {self.description}, {self.status})"

class Planner:
    """Planner智能体实现"""
    
    def __init__(self, planner_id: str = "planner-main", llm_provider: str = "siliconflow"):
        """初始化Planner
        
        Args:
            planner_id: Planner的唯一标识符
            llm_provider: 使用的LLM提供商，默认为siliconflow
        """
        self.planner_id = planner_id
        self.llm_provider = llm_provider
        self.task_store: Dict[str, Task] = {}
        self.message_queue = queue.Queue()
        self.shutdown_flag = threading.Event()
        self.processing_thread = None
        self.version = "1.0.0"
        
        # 创建通信管理器
        self.comm_manager = CommunicationManager(planner_id, "planner")
        
        # 注册消息处理器
        self._register_message_handlers()
        
        # 创建三个层次的决策引擎
        self.strategic_engine = StrategicEngine(self)
        self.tactical_engine = TacticalEngine(self)
        self.operational_engine = OperationalEngine(self)
        
        # 初始化状态持久化
        self.state_file = f"{planner_id}_state.json"
        self._load_state()
        
        logger.info(f"Planner {planner_id} 初始化完成，使用LLM提供商: {llm_provider}")
    
    def _register_message_handlers(self) -> None:
        """注册消息处理器"""
        self.comm_manager.register_handler("create_task", self._handle_create_task)
        self.comm_manager.register_handler("update_task", self._handle_update_task)
        self.comm_manager.register_handler("task_completed", self._handle_task_completed)
        self.comm_manager.register_handler("task_failed", self._handle_task_failed)
        self.comm_manager.register_handler("request_plan", self._handle_request_plan)
        self.comm_manager.register_handler("status_request", self._handle_status_request)
    
    def _save_state(self) -> None:
        """保存Planner状态到文件"""
        try:
            state = {
                "planner_id": self.planner_id,
                "version": self.version,
                "llm_provider": self.llm_provider,
                "tasks": {task_id: task.to_dict() for task_id, task in self.task_store.items()},
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"已保存Planner状态到: {self.state_file}")
        except Exception as e:
            logger.error(f"保存状态时出错: {e}")
    
    def _load_state(self) -> bool:
        """从文件加载Planner状态"""
        try:
            if not os.path.exists(self.state_file):
                logger.info(f"状态文件不存在: {self.state_file}")
                return False
                
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # 验证状态
            if state.get("planner_id") != self.planner_id:
                logger.warning(f"状态文件中的planner_id与当前不符: {state.get('planner_id')} != {self.planner_id}")
                return False
            
            # 加载任务
            for task_dict in state.get("tasks", {}).values():
                task = Task.from_dict(task_dict)
                self.task_store[task.task_id] = task
            
            logger.info(f"已从 {self.state_file} 加载状态，包含 {len(self.task_store)} 个任务")
            return True
        except Exception as e:
            logger.error(f"加载状态时出错: {e}")
            return False
    
    def start(self) -> None:
        """启动Planner处理线程和通信管理器"""
        # 启动通信管理器
        self.comm_manager.start()
        
        if self.processing_thread is not None and self.processing_thread.is_alive():
            logger.warning("Planner已经在运行中")
            return
        
        self.shutdown_flag.clear()
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info(f"Planner {self.planner_id} 已启动")
    
    def stop(self) -> None:
        """停止Planner处理线程和通信管理器"""
        # 停止通信管理器
        self.comm_manager.stop()
        
        if self.processing_thread is None or not self.processing_thread.is_alive():
            logger.warning("Planner没有在运行")
            return
        
        self.shutdown_flag.set()
        self.processing_thread.join(timeout=5.0)
        if self.processing_thread.is_alive():
            logger.warning("Planner处理线程未能正常停止")
        else:
            logger.info(f"Planner {self.planner_id} 已停止")
        
        # 保存状态
        self._save_state()

    def add_executor(self, executor_id: str, executor_comm) -> None:
        """添加执行器到路由表
        
        Args:
            executor_id: 执行器ID
            executor_comm: 执行器通信管理器
        """
        self.comm_manager.add_route(executor_id, executor_comm)
        logger.info(f"已添加执行器: {executor_id}")

    def _process_messages(self) -> None:
        """处理消息队列中的消息"""
        while not self.shutdown_flag.is_set():
            try:
                message = self.message_queue.get(timeout=1.0)
                self._handle_message(message)
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理单个消息"""
        message_type = message.get("type")
        
        if message_type == "create_task":
            self._handle_create_task(message)
        elif message_type == "update_task":
            self._handle_update_task(message)
        elif message_type == "task_completed":
            self._handle_task_completed(message)
        elif message_type == "task_failed":
            self._handle_task_failed(message)
        elif message_type == "request_plan":
            self._handle_request_plan(message)
        elif message_type == "status_request":
            self._handle_status_request(message)
        else:
            logger.warning(f"未知消息类型: {message_type}")
    
    def _handle_create_task(self, message: Dict[str, Any]) -> None:
        """处理创建任务消息"""
        description = message.get("description", "")
        priority = message.get("priority", "medium")
        deadline = message.get("deadline")
        parent_id = message.get("parent_id")
        
        task_id = self.create_task(description, priority, deadline, parent_id)
        
        # 如果有回调，发送创建成功消息
        callback = message.get("callback")
        if callback:
            self._send_message(callback, {
                "type": "task_created",
                "task_id": task_id,
                "status": "success"
            })
    
    def _handle_update_task(self, message: Dict[str, Any]) -> None:
        """处理更新任务消息"""
        task_id = message.get("task_id")
        status = message.get("status")
        result = message.get("result")
        
        if task_id not in self.task_store:
            logger.warning(f"更新不存在的任务: {task_id}")
            return
        
        task = self.task_store[task_id]
        if status:
            task.update_status(status)
        
        if result is not None:
            task.set_result(result)
    
    def _handle_task_completed(self, message: Dict[str, Any]) -> None:
        """处理任务完成消息"""
        task_id = message.get("task_id")
        result = message.get("result")
        
        if task_id not in self.task_store:
            logger.warning(f"标记不存在的任务为完成: {task_id}")
            return
        
        task = self.task_store[task_id]
        task.set_result(result)
        
        # 检查父任务是否完成
        if task.parent_id and task.parent_id in self.task_store:
            parent_task = self.task_store[task.parent_id]
            all_subtasks_completed = True
            
            for subtask_id in parent_task.subtasks:
                if subtask_id in self.task_store:
                    subtask = self.task_store[subtask_id]
                    if subtask.status != "completed":
                        all_subtasks_completed = False
                        break
            
            if all_subtasks_completed:
                parent_task.update_status("completed")
                logger.info(f"所有子任务已完成，父任务 {parent_task.task_id} 标记为完成")
    
    def _handle_task_failed(self, message: Dict[str, Any]) -> None:
        """处理任务失败消息"""
        task_id = message.get("task_id")
        error = message.get("error", "未知错误")
        
        if task_id not in self.task_store:
            logger.warning(f"标记不存在的任务为失败: {task_id}")
            return
        
        task = self.task_store[task_id]
        task.update_status("failed")
        task.metadata["error"] = error
        
        # 触发失败处理策略
        self._handle_task_failure(task)
    
    def _handle_request_plan(self, message: Dict[str, Any]) -> None:
        """处理请求规划消息"""
        goal = message.get("goal", "")
        constraints = message.get("constraints", [])
        resources = message.get("resources", [])
        deadline = message.get("deadline")
        callback = message.get("callback")
        
        # 创建主任务
        main_task_id = self.create_task(goal, "high", deadline)
        
        # 生成规划
        plan = self.generate_plan(main_task_id, constraints, resources)
        
        # 如果有回调，发送规划完成消息
        if callback:
            self._send_message(callback, {
                "type": "plan_created",
                "task_id": main_task_id,
                "plan": plan,
                "status": "success"
            })
    
    def _handle_task_failure(self, task: Task) -> None:
        """处理任务失败的策略"""
        # 自动重试策略
        retry_count = task.metadata.get("retry_count", 0)
        max_retries = task.metadata.get("max_retries", 3)
        
        if retry_count < max_retries:
            # 增加重试计数
            task.metadata["retry_count"] = retry_count + 1
            task.update_status("pending")
            
            # 重新分配任务
            if task.assigned_to:
                self.assign_task(task.task_id, task.assigned_to)
            
            logger.info(f"任务 {task.task_id} 失败，自动重试 ({retry_count + 1}/{max_retries})")
        else:
            logger.warning(f"任务 {task.task_id} 失败，已达到最大重试次数 {max_retries}")
            
            # 通知父任务失败
            if task.parent_id and task.parent_id in self.task_store:
                parent_task = self.task_store[task.parent_id]
                parent_task.metadata["failed_subtasks"] = parent_task.metadata.get("failed_subtasks", []) + [task.task_id]
                
                # 决定父任务是否失败
                critical_subtask = task.metadata.get("critical", False)
                if critical_subtask:
                    parent_task.update_status("failed")
                    parent_task.metadata["error"] = f"关键子任务 {task.task_id} 失败"
                    logger.warning(f"关键子任务 {task.task_id} 失败，父任务 {parent_task.task_id} 标记为失败")
    
    def _send_message(self, receiver: str, message: Dict[str, Any]) -> None:
        """发送消息到接收者
        
        实际实现中，这将使用消息队列或事件系统向其他组件发送消息。
        在此示例中，仅记录消息。
        """
        message["sender"] = self.planner_id
        message["timestamp"] = datetime.datetime.now().isoformat()
        message["message_id"] = str(uuid.uuid4())
        
        logger.info(f"发送消息到 {receiver}: {message}")
        # 实际发送逻辑在这里实现
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """将消息放入队列中处理"""
        self.message_queue.put(message)
    
    def create_task(self, description: str, priority: str = "medium", 
                   deadline: Optional[str] = None, parent_id: Optional[str] = None) -> str:
        """创建一个新任务
        
        Args:
            description: 任务描述
            priority: 优先级 (high, medium, low)
            deadline: 截止时间
            parent_id: 父任务ID
            
        Returns:
            新创建的任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, description, priority, deadline, parent_id)
        self.task_store[task_id] = task
        
        # 如果有父任务，将此任务添加为子任务
        if parent_id and parent_id in self.task_store:
            parent_task = self.task_store[parent_id]
            parent_task.add_subtask(task_id)
        
        logger.info(f"创建任务: {task}")
        return task_id
    
    def assign_task(self, task_id: str, executor_id: str) -> bool:
        """分配任务给执行器
        
        Args:
            task_id: 任务ID
            executor_id: 执行器ID
            
        Returns:
            分配是否成功
        """
        # 查找任务
        task = self.get_task(task_id)
        if task is None:
            logger.warning(f"找不到要分配的任务: {task_id}")
            return False
        
        # 如果任务已经完成或失败，不再分配
        if task.status in ["completed", "failed"]:
            logger.warning(f"任务 {task_id} 状态为 {task.status}，不能重新分配")
            return False
        
        # 分配任务
        task.assign(executor_id)
        
        # 保存状态
        self._save_state()
        
        # 准备任务分配消息
        task_dict = task.to_dict()
        
        # 如果有子任务，不直接发送子任务内容
        if task.subtasks:
            task_dict["has_subtasks"] = True
        
        # 使用操作引擎生成执行指令
        instructions = []
        if task.metadata.get("schedule"):
            operational_plan = self.operational_engine.generate_instructions(
                task.metadata["schedule"]
            )
            if operational_plan and "instructions" in operational_plan:
                instructions = operational_plan["instructions"]
        
        # 发送任务分配消息
        assignment_message = {
            "type": "task_assignment",
            "task": task_dict,
            "instructions": instructions
        }
        
        # 使用通信管理器发送消息
        self.comm_manager.send_message(
            destination=executor_id,
            payload=assignment_message,
            qos=QoSLevel.LEVEL_2,  # 使用可靠传输
            priority=Priority.HIGH if task.priority == "high" else Priority.MEDIUM
        )
        
        logger.info(f"已将任务 {task_id} 分配给执行器 {executor_id}")
        return True
    
    def generate_plan(self, main_task_id: str, constraints: List[str] = [], 
                     resources: List[str] = []) -> Dict[str, Any]:
        """为主任务生成执行计划
        
        Args:
            main_task_id: 主任务ID
            constraints: 约束条件列表
            resources: 可用资源列表
            
        Returns:
            执行计划
        """
        # 查找主任务
        main_task = self.get_task(main_task_id)
        if main_task is None:
            logger.warning(f"找不到主任务: {main_task_id}")
            return {"error": "找不到主任务"}
        
        # 如果任务尚未分解，先进行分析
        if not main_task.subtasks:
            self._analyze_task(main_task_id)
            # 重新获取任务（可能已更新）
            main_task = self.get_task(main_task_id)
        
        # 为子任务生成时间表
        schedule = self.tactical_engine.schedule_tasks(main_task.subtasks, resources)
        
        # 更新任务的元数据
        main_task.metadata["schedule"] = schedule
        main_task.resources = resources
        
        # 使用操作引擎生成详细执行指令
        operational_plan = self.operational_engine.generate_instructions(schedule)
        
        # 保存状态
        self._save_state()
        
        # 构建完整计划
        plan = {
            "task_id": main_task_id,
            "description": main_task.description,
            "subtasks": len(main_task.subtasks),
            "schedule": schedule,
            "instructions": operational_plan.get("instructions", []),
            "estimated_completion_time": operational_plan.get("estimated_completion_time"),
            "resource_allocation": operational_plan.get("resource_allocation", {})
        }
        
        logger.info(f"已为任务 {main_task_id} 生成执行计划")
        return plan
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象，如果不存在则返回None
        """
        return self.task_store.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """获取所有任务
        
        Returns:
            任务ID到任务对象的映射
        """
        return self.task_store.copy()
    
    def query_tasks(self, status: Optional[str] = None, priority: Optional[str] = None) -> List[Task]:
        """查询任务
        
        Args:
            status: 任务状态（可选）
            priority: 任务优先级（可选）
            
        Returns:
            符合条件的任务列表
        """
        results = []
        
        for task in self.task_store.values():
            # 检查状态
            if status is not None and task.status != status:
                continue
            
            # 检查优先级
            if priority is not None and task.priority != priority:
                continue
            
            # 符合所有条件，添加到结果中
            results.append(task)
        
        return results
    
    def _analyze_task(self, task_id: str) -> bool:
        """分析任务并创建子任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            分析是否成功
        """
        # 获取任务
        task = self.get_task(task_id)
        if task is None:
            logger.warning(f"找不到要分析的任务: {task_id}")
            return False
        
        # 如果任务已经有子任务，跳过分析
        if task.subtasks:
            logger.info(f"任务 {task_id} 已有子任务，跳过分析")
            return True
            
        # 记录开始分析
        logger.info(f"开始分析任务: {task.description}")
        
        try:
            # 使用LLM进行任务分解（如果可用）
            subtask_descriptions = []
            
            if llm_available:
                # 构建提示
                prompt = f"""
                任务描述: {task.description}
                
                请将此任务分解为5个或更少的子任务，每个子任务应该是自包含、明确的工作单元。
                考虑任务的依赖关系，确保子任务按照合理的顺序排列。
                
                输出格式:
                [
                  "子任务1描述",
                  "子任务2描述",
                  ...
                ]
                """
                
                # 调用LLM
                response = query_planner_llm(prompt, self.llm_provider)
                
                # 解析响应
                try:
                    # 尝试直接解析完整的JSON
                    subtask_descriptions = json.loads(response)
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试提取方括号内的内容
                    import re
                    match = re.search(r'\[(.*?)\]', response, re.DOTALL)
                    if match:
                        # 将提取的内容格式化为JSON数组
                        items_str = match.group(1)
                        # 分割并清理引号
                        items = [item.strip().strip('"\'') for item in items_str.split('",')]
                        subtask_descriptions = [item for item in items if item]
            
            # 如果LLM不可用或没有返回结果，使用战略引擎进行分解
            if not subtask_descriptions:
                logger.info("使用战略引擎分解任务")
                subtask_descriptions = self.strategic_engine.decompose_goal(task.description)
            
            # 创建子任务
            for description in subtask_descriptions:
                # 跳过空描述
                if not description.strip():
                    continue
                    
                # 创建子任务
                subtask_id = self.create_task(description, task.priority, task.deadline, task.task_id)
                logger.info(f"创建子任务: {subtask_id} - {description[:50]}...")
            
            # 保存状态
            self._save_state()
            
            logger.info(f"任务 {task_id} 分析完成，创建了 {len(task.subtasks)} 个子任务")
            return True
            
        except Exception as e:
            logger.error(f"分析任务 {task_id} 时出错: {e}")
            return False

    def _handle_status_request(self, message):
        """处理状态请求"""
        return {
            "status": "ok",
            "planner_id": self.planner_id,
            "is_running": self.is_running(),
            "pending_tasks": len(self.pending_tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks)
        }

    def is_running(self) -> bool:
        """检查Planner是否正在运行"""
        return (self.processing_thread is not None and 
                self.processing_thread.is_alive() and 
                not self.shutdown_flag.is_set())

class StrategicEngine:
    """战略层决策引擎，负责目标分解和资源评估"""
    
    def __init__(self, planner: Planner):
        self.planner = planner
    
    def decompose_goal(self, goal: str, constraints: List[str] = []) -> List[str]:
        """将目标分解为子任务
        
        Args:
            goal: 总体目标描述
            constraints: 约束条件列表
            
        Returns:
            子任务描述列表
        """
        # 记录分解请求
        logger.info(f"分解目标: {goal}")
        logger.info(f"约束条件: {constraints}")
        
        try:
            # 尝试使用LLM进行任务分解（如果可用）
            if llm_available:
                # 构建详细的提示词
                constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "无特殊约束"
                
                prompt = f"""
                # 任务分解请求
                
                ## 任务目标
                {goal}
                
                ## 约束条件
                {constraints_text}
                
                ## 要求
                1. 请将此任务分解为5个或更少的具体子任务
                2. 子任务应该:
                   - 遵循合理的执行顺序
                   - 每个子任务应该是明确定义的工作单元
                   - 子任务之间应有适当的依赖关系
                3. 考虑所有约束条件
                
                ## 输出格式
                仅返回子任务列表的JSON数组，不要添加任何解释:
                [
                  "子任务1描述",
                  "子任务2描述",
                  ...
                ]
                """
                
                # 调用LLM
                response = query_planner_llm(prompt, self.planner.llm_provider)
                
                # 解析响应
                try:
                    # 尝试直接解析JSON
                    import json
                    subtasks = json.loads(response)
                    if isinstance(subtasks, list) and len(subtasks) > 0:
                        logger.info(f"LLM成功分解任务，生成{len(subtasks)}个子任务")
                        return subtasks
                except Exception as e:
                    logger.warning(f"解析LLM响应失败: {e}")
                    
                    # 尝试使用正则表达式提取JSON数组
                    try:
                        import re
                        # 匹配方括号包围的内容
                        match = re.search(r'\[(.*?)\]', response, re.DOTALL)
                        if match:
                            items_str = match.group(1)
                            # 分割项目（处理可能的不同引号格式）
                            items = re.findall(r'"([^"]*?)"|\'([^\']*?)\'', items_str)
                            # 从每个匹配的组中提取非空值
                            subtasks = [next(s for s in group if s) for group in items if any(group)]
                            if subtasks:
                                logger.info(f"从LLM响应中提取了{len(subtasks)}个子任务")
                                return subtasks
                    except Exception as e2:
                        logger.warning(f"提取任务列表失败: {e2}")
        
        except Exception as e:
            logger.error(f"调用LLM分解任务失败: {e}")
        
        # 如果LLM方法失败或不可用，使用基于规则的分解方法
        logger.info("使用基于规则的方法分解任务")
        
        # 增强的基于关键词的任务分解
        goal_lower = goal.lower()
        
        # 开发类任务
        if any(kw in goal_lower for kw in ["开发", "构建", "实现", "编程", "设计系统"]):
            return [
                "需求分析和功能定义",
                "系统架构和组件设计",
                "核心功能实现和接口开发",
                "单元测试和集成测试",
                "优化性能和文档编写"
            ]
        
        # 测试类任务
        elif any(kw in goal_lower for kw in ["测试", "验证", "质量保证", "qa"]):
            return [
                "测试需求分析和策略制定",
                "测试计划编写和用例设计",
                "环境搭建和自动化测试脚本开发",
                "执行测试和缺陷跟踪",
                "测试报告生成和结果分析"
            ]
        
        # 分析类任务
        elif any(kw in goal_lower for kw in ["分析", "研究", "调查", "评估"]):
            return [
                "信息收集和数据获取",
                "数据清理和初步分析",
                "深入分析和模式识别",
                "结果验证和假设检验",
                "报告编写和建议生成"
            ]
        
        # 优化类任务
        elif any(kw in goal_lower for kw in ["优化", "改进", "提升", "增强", "性能"]):
            return [
                "性能基准测试和瓶颈识别",
                "优化策略制定和方案设计",
                "算法和代码重构实现",
                "性能测试和对比分析",
                "文档更新和最佳实践总结"
            ]
        
        # 文档类任务
        elif any(kw in goal_lower for kw in ["文档", "文章", "报告", "写作"]):
            return [
                "内容规划和大纲设计",
                "核心内容编写和示例开发",
                "图表和可视化资料准备",
                "格式调整和内容审核",
                "最终校对和发布准备"
            ]
        
        # 集成类任务
        elif any(kw in goal_lower for kw in ["集成", "部署", "安装", "配置"]):
            return [
                "环境准备和依赖分析",
                "组件集成和接口调整",
                "配置优化和自动化脚本开发",
                "部署测试和验证",
                "监控设置和运维文档编写"
            ]
        
        # 管理类任务
        elif any(kw in goal_lower for kw in ["管理", "协调", "规划", "项目"]):
            return [
                "项目范围定义和需求收集",
                "任务分解和资源分配",
                "进度跟踪和风险管理",
                "团队协调和沟通",
                "结果验收和项目总结"
            ]
        
        # 默认通用任务分解
        else:
            return [
                "需求收集和资源准备",
                "方案设计和计划制定",
                "核心任务执行",
                "结果验证和改进",
                "文档完善和总结"
            ]

class TacticalEngine:
    """战术层决策引擎，负责任务排序和调度"""
    
    def __init__(self, planner: Planner):
        self.planner = planner
    
    def schedule_tasks(self, tasks: List[str], resources: List[str] = []) -> Dict[str, Any]:
        """排序和调度任务
        
        Args:
            tasks: 任务描述列表
            resources: 可用资源列表
            
        Returns:
            任务调度计划
        """
        # 在实际实现中，这里会使用LLM分析任务间的依赖关系并分配资源
        # 以下是模拟实现
        logger.info(f"调度 {len(tasks)} 个任务")
        
        # 创建简单的调度计划
        schedule = []
        dependencies = {}
        estimated_duration = {}
        
        for i, task in enumerate(tasks):
            task_info = {
                "id": f"task_{i+1}",
                "description": task,
                "order": i+1,
                "priority": "high" if i == 0 else ("medium" if i < len(tasks) - 1 else "low")
            }
            
            # 添加依赖关系（除第一个任务外，每个任务依赖于前一个任务）
            if i > 0:
                dependencies[f"task_{i+1}"] = [f"task_{i}"]
            
            # 估算持续时间（随机模拟）
            estimated_duration[f"task_{i+1}"] = (i + 1) * 2  # 以小时为单位
            
            schedule.append(task_info)
        
        return {
            "schedule": schedule,
            "dependencies": dependencies,
            "estimated_duration": estimated_duration,
            "total_estimated_hours": sum(estimated_duration.values()),
            "critical_path": [f"task_{i+1}" for i in range(len(tasks))],
            "resources_allocation": self._allocate_resources(schedule, resources)
        }
    
    def _allocate_resources(self, schedule: List[Dict[str, Any]], resources: List[str]) -> Dict[str, List[str]]:
        """分配资源到任务
        
        Args:
            schedule: 任务调度计划
            resources: 可用资源列表
            
        Returns:
            任务ID到资源列表的映射
        """
        # 简单的资源分配策略
        allocation = {}
        
        if not resources:
            # 如果没有指定资源，使用默认资源
            resources = ["executor-1", "executor-2"]
        
        for i, task in enumerate(schedule):
            task_id = task["id"]
            # 轮流分配资源
            resource_idx = i % len(resources)
            allocation[task_id] = [resources[resource_idx]]
        
        return allocation

class OperationalEngine:
    """操作层决策引擎，负责生成具体指令"""
    
    def __init__(self, planner: Planner):
        self.planner = planner
    
    def generate_instructions(self, tactical_plan: Dict[str, Any]) -> Dict[str, Any]:
        """为任务生成具体执行指令
        
        Args:
            tactical_plan: 战术层生成的调度计划
            
        Returns:
            包含具体指令的执行计划
        """
        # 在实际实现中，这里会使用LLM生成详细的执行指令
        # 以下是模拟实现
        logger.info("生成任务执行指令")
        
        instructions = {}
        success_criteria = {}
        error_handling = {}
        
        for task in tactical_plan["schedule"]:
            task_id = task["id"]
            description = task["description"]
            
            # 生成模拟指令
            instructions[task_id] = [
                f"1. 准备执行任务：{description}",
                f"2. 收集必要资源和信息",
                f"3. 按照最佳实践执行任务",
                f"4. 记录执行过程和结果",
                f"5. 验证任务成果"
            ]
            
            # 生成成功标准
            success_criteria[task_id] = f"任务 '{description}' 成功完成的标准：目标实现，没有重大问题，文档完整"
            
            # 生成错误处理指南
            error_handling[task_id] = {
                "retry_strategy": "遇到临时错误时最多重试3次",
                "escalation_path": "持续失败时升级到Planner处理",
                "common_errors": ["资源不足", "环境配置错误", "依赖任务失败"],
                "recovery_steps": ["检查资源", "验证环境", "重新评估依赖关系"]
            }
        
        return {
            "instructions": instructions,
            "success_criteria": success_criteria,
            "error_handling": error_handling,
            "monitoring": {
                "check_points": ["25%", "50%", "75%", "100%"],
                "metrics": ["完成度", "质量指标", "资源使用率"]
            },
            "reporting": {
                "frequency": "每完成一个任务",
                "content": ["状态更新", "遇到的问题", "下一步计划"]
            }
        }

def main():
    """主函数，用于测试Planner功能"""
    parser = argparse.ArgumentParser(description="Planner智能体")
    parser.add_argument("--id", default="planner-main", help="Planner ID")
    parser.add_argument("--llm", default="siliconflow", help="LLM提供商")
    parser.add_argument("--test", action="store_true", help="运行测试")
    args = parser.parse_args()
    
    logger.info(f"启动Planner智能体，ID: {args.id}, LLM: {args.llm}")
    
    # 创建Planner实例
    planner = Planner(args.id, args.llm)
    
    if args.test:
        run_test(planner)
    else:
        try:
            # 启动Planner
            planner.start()
            
            # 保持程序运行
            print("Planner已启动。按Ctrl+C停止...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n接收到停止信号，正在停止Planner...")
            planner.stop()
            print("Planner已停止")

def run_test(planner: Planner):
    """运行测试功能"""
    print("----- 开始Planner测试 -----")
    
    # 启动Planner
    planner.start()
    
    # 测试1：创建简单任务
    print("\n1. 创建简单任务")
    task_id = planner.create_task("实现用户登录功能", "high")
    print(f"  创建的任务ID: {task_id}")
    
    # 等待任务分析完成
    time.sleep(2)
    
    # 测试2：查询任务详情
    print("\n2. 查询任务详情")
    task = planner.get_task(task_id)
    if task:
        print(f"  任务描述: {task.description}")
        print(f"  任务状态: {task.status}")
        print(f"  子任务数量: {len(task.subtasks)}")
    
    # 测试3：生成执行计划
    print("\n3. 生成执行计划")
    plan = planner.generate_plan(task_id, ["使用JWT认证", "支持第三方登录"])
    print(f"  计划包含 {plan.get('subtasks', 0)} 个子任务")
    print(f"  估计完成时间: {plan.get('estimated_completion_time', '未知')}")
    
    # 测试4：查询所有任务
    print("\n4. 查询所有任务")
    all_tasks = planner.get_all_tasks()
    print(f"  总任务数: {len(all_tasks)}")
    
    # 测试5：按状态查询任务
    print("\n5. 按状态查询任务")
    pending_tasks = planner.query_tasks(status="pending")
    print(f"  待处理任务数: {len(pending_tasks)}")
    
    # 停止Planner
    planner.stop()
    print("\n----- Planner测试完成 -----")

if __name__ == "__main__":
    main() 