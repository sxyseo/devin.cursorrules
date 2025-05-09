#!/usr/bin/env python3
"""
通信管理器

实现智能体间的可靠消息传递，包括消息路由、重试机制和消息确认。
提供结构化消息格式，支持不同的QoS级别和消息优先级。
"""

import os
import sys
import json
import uuid
import time
import logging
import datetime
import threading
import queue
import hashlib
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("communication")

class QoSLevel(Enum):
    """服务质量等级"""
    LEVEL_1 = 1  # 至少一次交付，可能重复
    LEVEL_2 = 2  # 恰好一次交付，不会重复
    LEVEL_3 = 3  # 恰好一次交付，有序，不会重复

class Priority(Enum):
    """消息优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"      # 等待发送
    SENT = "sent"            # 已发送，等待确认
    DELIVERED = "delivered"  # 已送达
    FAILED = "failed"        # 发送失败
    EXPIRED = "expired"      # 已过期

class Message:
    """结构化消息格式"""
    
    def __init__(self, 
                 message_id: str,
                 origin: Dict[str, Any],
                 destination: str,
                 payload: Dict[str, Any],
                 qos: QoSLevel = QoSLevel.LEVEL_1,
                 priority: Priority = Priority.MEDIUM,
                 metadata: Optional[Dict[str, Any]] = None):
        self.message_id = message_id
        self.timestamp = datetime.datetime.now().isoformat()
        self.origin = origin
        self.destination = destination
        self.qos = qos
        self.payload = payload
        self.priority = priority
        self.metadata = metadata or {}
        
        # 为消息生成上下文哈希，用于验证消息完整性
        context_str = json.dumps(self.payload, sort_keys=True)
        self.context_hash = hashlib.sha3_256(context_str.encode()).hexdigest()
        
        # 消息传递状态
        self.status = MessageStatus.PENDING
        self.retry_count = 0
        self.last_sent = None
        self.delivered_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典表示"""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "origin": self.origin,
            "destination": self.destination,
            "qos": self.qos.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "context_hash": self.context_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息对象"""
        msg = cls(
            message_id=data["message_id"],
            origin=data["origin"],
            destination=data["destination"],
            payload=data["payload"],
            qos=QoSLevel(data["qos"]),
            priority=Priority(data["priority"]),
            metadata=data.get("metadata", {})
        )
        msg.timestamp = data.get("timestamp", msg.timestamp)
        msg.context_hash = data.get("context_hash", msg.context_hash)
        return msg
    
    def verify_integrity(self) -> bool:
        """验证消息完整性"""
        context_str = json.dumps(self.payload, sort_keys=True)
        computed_hash = hashlib.sha3_256(context_str.encode()).hexdigest()
        return computed_hash == self.context_hash

class CommunicationManager:
    """智能体通信管理器"""
    
    def __init__(self, agent_id: str, agent_type: str, max_retries: int = 3, 
                 retry_delay: float = 1.0, message_timeout: float = 60.0):
        """初始化通信管理器
        
        Args:
            agent_id: 智能体ID
            agent_type: 智能体类型 (planner/executor)
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            message_timeout: 消息超时时间（秒）
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.message_timeout = message_timeout
        
        # 消息队列和处理器
        self.outgoing_queue = queue.PriorityQueue()  # 优先级队列
        self.incoming_queue = queue.Queue()
        self.pending_messages: Dict[str, Message] = {}  # 等待确认的消息
        
        # 消息处理器字典
        self.message_handlers: Dict[str, Callable] = {}
        
        # 线程控制
        self.shutdown_flag = threading.Event()
        self.outgoing_thread = None
        self.incoming_thread = None
        
        # 消息路由
        self.route_table: Dict[str, Any] = {}
        
        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "delivery_failures": 0,
            "retries": 0,
            "avg_delivery_time": 0.0
        }
        
        logger.info(f"通信管理器初始化完成，智能体ID: {agent_id}, 类型: {agent_type}")
    
    def start(self) -> None:
        """启动通信管理器"""
        if self.outgoing_thread is not None and self.outgoing_thread.is_alive():
            logger.warning("通信管理器已经在运行中")
            return
        
        self.shutdown_flag.clear()
        
        # 启动发送线程
        self.outgoing_thread = threading.Thread(target=self._process_outgoing)
        self.outgoing_thread.daemon = True
        self.outgoing_thread.start()
        
        # 启动接收线程
        self.incoming_thread = threading.Thread(target=self._process_incoming)
        self.incoming_thread.daemon = True
        self.incoming_thread.start()
        
        logger.info(f"通信管理器启动完成，智能体ID: {self.agent_id}")
    
    def stop(self) -> None:
        """停止通信管理器"""
        if (self.outgoing_thread is None or not self.outgoing_thread.is_alive()) and \
           (self.incoming_thread is None or not self.incoming_thread.is_alive()):
            logger.warning("通信管理器没有在运行")
            return
        
        self.shutdown_flag.set()
        
        if self.outgoing_thread is not None and self.outgoing_thread.is_alive():
            self.outgoing_thread.join(timeout=5.0)
            if self.outgoing_thread.is_alive():
                logger.warning("发送线程未能正常停止")
        
        if self.incoming_thread is not None and self.incoming_thread.is_alive():
            self.incoming_thread.join(timeout=5.0)
            if self.incoming_thread.is_alive():
                logger.warning("接收线程未能正常停止")
        
        logger.info(f"通信管理器已停止，智能体ID: {self.agent_id}")
    
    def send_message(self, destination: str, payload: Dict[str, Any], 
                    qos: QoSLevel = QoSLevel.LEVEL_1, 
                    priority: Priority = Priority.MEDIUM,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """发送消息
        
        Args:
            destination: 目标智能体ID
            payload: 消息内容
            qos: 服务质量等级
            priority: 消息优先级
            metadata: 元数据
            
        Returns:
            消息ID
        """
        message_id = str(uuid.uuid4())
        
        # 构建发送者信息
        origin = {
            "role": self.agent_type,
            "id": self.agent_id,
            "version": "1.0",
            "context": "task_context",
            "priority": priority.value
        }
        
        # 创建消息对象
        message = Message(
            message_id=message_id,
            origin=origin,
            destination=destination,
            payload=payload,
            qos=qos,
            priority=priority,
            metadata=metadata
        )
        
        # 如果是QoS级别2或3，添加到待确认消息字典
        if qos in [QoSLevel.LEVEL_2, QoSLevel.LEVEL_3]:
            self.pending_messages[message_id] = message
        
        # 计算消息的优先级值（用于优先级队列）
        priority_value = self._calculate_priority(message)
        
        # 添加到发送队列
        self.outgoing_queue.put((priority_value, message))
        
        logger.debug(f"消息 {message_id} 已添加到发送队列")
        return message_id
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type] = handler
        logger.debug(f"已注册消息处理器: {message_type}")
    
    def _calculate_priority(self, message: Message) -> int:
        """计算消息优先级值（数值越小优先级越高）"""
        priority_map = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 10,
            Priority.MEDIUM: 20,
            Priority.LOW: 30
        }
        base_priority = priority_map.get(message.priority, 20)
        
        # 考虑重试次数，增加重试消息的优先级
        retry_boost = min(5, message.retry_count)
        
        # 考虑消息的等待时间
        wait_time = 0
        if message.last_sent:
            wait_time = min(10, int((time.time() - message.last_sent) / 10))
        
        return base_priority - retry_boost - wait_time
    
    def _process_outgoing(self) -> None:
        """处理发送队列中的消息"""
        while not self.shutdown_flag.is_set():
            try:
                # 获取优先级最高的消息
                _, message = self.outgoing_queue.get(timeout=1.0)
                
                # 发送消息
                success = self._send_message_to_agent(message)
                
                if success:
                    # 更新消息状态
                    message.status = MessageStatus.SENT
                    message.last_sent = time.time()
                    message.retry_count += 1
                    
                    # 更新统计信息
                    self.stats["messages_sent"] += 1
                    
                    # 如果是QoS级别1，直接认为已送达
                    if message.qos == QoSLevel.LEVEL_1:
                        logger.debug(f"消息 {message.message_id} 已发送(QoS1)")
                    else:
                        logger.debug(f"消息 {message.message_id} 已发送，等待确认")
                        # 如果超过最大重试次数还未收到确认，将在超时检查中标记为失败
                else:
                    # 发送失败，重新入队
                    if message.retry_count < self.max_retries:
                        # 使用指数退避策略
                        delay = self.retry_delay * (2 ** message.retry_count)
                        logger.warning(f"消息 {message.message_id} 发送失败，将在 {delay:.2f} 秒后重试")
                        
                        # 更新统计信息
                        self.stats["retries"] += 1
                        
                        # 重新计算优先级并重新入队
                        time.sleep(delay)
                        priority_value = self._calculate_priority(message)
                        self.outgoing_queue.put((priority_value, message))
                    else:
                        logger.error(f"消息 {message.message_id} 发送失败，已达到最大重试次数")
                        message.status = MessageStatus.FAILED
                        
                        # 更新统计信息
                        self.stats["delivery_failures"] += 1
                        
                        # 如果是QoS级别2或3，从待确认消息中移除
                        if message.qos in [QoSLevel.LEVEL_2, QoSLevel.LEVEL_3]:
                            self.pending_messages.pop(message.message_id, None)
                
                self.outgoing_queue.task_done()
                
                # 检查超时的消息
                self._check_message_timeouts()
                
            except queue.Empty:
                # 定期检查超时的消息
                self._check_message_timeouts()
                continue
            except Exception as e:
                logger.error(f"处理发送消息时出错: {e}")
    
    def _check_message_timeouts(self) -> None:
        """检查超时的待确认消息"""
        current_time = time.time()
        timed_out_messages = []
        
        for message_id, message in self.pending_messages.items():
            if message.status == MessageStatus.SENT and message.last_sent is not None:
                elapsed = current_time - message.last_sent
                if elapsed > self.message_timeout:
                    if message.retry_count < self.max_retries:
                        # 重新入队进行重试
                        logger.warning(f"消息 {message_id} 确认超时，重新入队重试")
                        priority_value = self._calculate_priority(message)
                        self.outgoing_queue.put((priority_value, message))
                    else:
                        # 达到最大重试次数，标记为失败
                        logger.error(f"消息 {message_id} 确认超时，已达到最大重试次数")
                        message.status = MessageStatus.EXPIRED
                        timed_out_messages.append(message_id)
                        
                        # 更新统计信息
                        self.stats["delivery_failures"] += 1
        
        # 从待确认消息中移除超时消息
        for message_id in timed_out_messages:
            self.pending_messages.pop(message_id, None)
    
    def _process_incoming(self) -> None:
        """处理接收队列中的消息"""
        while not self.shutdown_flag.is_set():
            try:
                # 从接收队列获取消息
                message_dict = self.incoming_queue.get(timeout=1.0)
                
                try:
                    # 解析消息
                    message = Message.from_dict(message_dict)
                    
                    # 验证消息完整性
                    if not message.verify_integrity():
                        logger.warning(f"消息 {message.message_id} 完整性验证失败，丢弃")
                        continue
                    
                    # 更新统计信息
                    self.stats["messages_received"] += 1
                    
                    # 如果是确认消息，处理确认
                    if message.payload.get("type") == "ack":
                        self._handle_ack(message)
                    else:
                        # 发送确认消息（如果需要）
                        if message.qos in [QoSLevel.LEVEL_2, QoSLevel.LEVEL_3]:
                            self._send_ack(message)
                        
                        # 分发消息到对应的处理器
                        self._dispatch_message(message)
                    
                except Exception as e:
                    logger.error(f"处理接收消息时出错: {e}")
                
                self.incoming_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"接收消息线程出错: {e}")
    
    def _handle_ack(self, message: Message) -> None:
        """处理确认消息"""
        original_id = message.payload.get("original_id")
        if original_id in self.pending_messages:
            original = self.pending_messages[original_id]
            original.status = MessageStatus.DELIVERED
            original.delivered_at = time.time()
            
            # 计算送达时间
            if original.last_sent is not None:
                delivery_time = original.delivered_at - original.last_sent
                # 更新平均送达时间（简单移动平均）
                self.stats["avg_delivery_time"] = (
                    0.9 * self.stats["avg_delivery_time"] + 0.1 * delivery_time
                    if self.stats["messages_sent"] > 1
                    else delivery_time
                )
            
            # 从待确认消息中移除
            self.pending_messages.pop(original_id)
            
            logger.debug(f"收到消息 {original_id} 的确认")
    
    def _send_ack(self, message: Message) -> None:
        """发送确认消息"""
        ack_payload = {
            "type": "ack",
            "original_id": message.message_id,
            "status": "delivered"
        }
        
        # 发送确认消息
        self.send_message(
            destination=message.origin["id"],
            payload=ack_payload,
            qos=QoSLevel.LEVEL_1,  # 确认消息使用QoS1即可
            priority=Priority.HIGH  # 确认消息优先级高
        )
    
    def _dispatch_message(self, message: Message) -> None:
        """将消息分发到对应的处理器"""
        message_type = message.payload.get("type")
        if message_type in self.message_handlers:
            try:
                # 调用对应的处理器
                self.message_handlers[message_type](message.payload)
            except Exception as e:
                logger.error(f"调用消息处理器时出错: {message_type}, {e}")
        else:
            logger.warning(f"未找到消息类型的处理器: {message_type}")
    
    def _send_message_to_agent(self, message: Message) -> bool:
        """发送消息到目标智能体
        
        这里实现具体的消息发送逻辑，可能是通过HTTP、ZeroMQ等通信机制
        在这个示例实现中，我们假设智能体在同一进程内，通过内存队列通信
        """
        try:
            # 获取目标智能体的消息队列
            target_agent = self.route_table.get(message.destination)
            if target_agent is None:
                logger.error(f"未找到目标智能体: {message.destination}")
                return False
            
            # 将消息放入目标智能体的接收队列
            message_dict = message.to_dict()
            target_agent.incoming_queue.put(message_dict)
            
            return True
        except Exception as e:
            logger.error(f"发送消息到智能体时出错: {e}")
            return False
    
    def receive_message(self, message_dict: Dict[str, Any]) -> None:
        """接收消息（由外部调用）
        
        Args:
            message_dict: 消息字典
        """
        self.incoming_queue.put(message_dict)
    
    def add_route(self, agent_id: str, agent_comm) -> None:
        """添加路由
        
        Args:
            agent_id: 目标智能体ID
            agent_comm: 目标智能体的通信管理器
        """
        self.route_table[agent_id] = agent_comm
        logger.info(f"添加路由: {self.agent_id} -> {agent_id}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计信息"""
        return self.stats

def create_communication_pair():
    """创建一对通信管理器，用于测试"""
    planner_comm = CommunicationManager("planner-main", "planner")
    executor_comm = CommunicationManager("executor-main", "executor")
    
    # 添加互相的路由
    planner_comm.add_route("executor-main", executor_comm)
    executor_comm.add_route("planner-main", planner_comm)
    
    return planner_comm, executor_comm

if __name__ == "__main__":
    # 测试代码
    planner_comm, executor_comm = create_communication_pair()
    
    # 启动通信管理器
    planner_comm.start()
    executor_comm.start()
    
    # 注册消息处理器
    def handle_task(payload):
        print(f"Executor收到任务: {payload}")
    
    def handle_result(payload):
        print(f"Planner收到结果: {payload}")
    
    executor_comm.register_handler("task_assignment", handle_task)
    planner_comm.register_handler("task_result", handle_result)
    
    # 发送测试消息
    planner_comm.send_message(
        destination="executor-main",
        payload={
            "type": "task_assignment",
            "task_id": "task-1",
            "description": "测试任务"
        },
        qos=QoSLevel.LEVEL_2
    )
    
    # 等待一段时间
    time.sleep(2)
    
    # 停止通信管理器
    planner_comm.stop()
    executor_comm.stop() 