#!/usr/bin/env python3
"""
多通道协议(MCP)服务

为Cursor提供多智能体调用接口，支持不同智能体间的通信和协作。
实现基于WebSocket的实时通信，支持双向消息传递和事件广播。
"""

import os
import sys
import json
import uuid
import logging
import datetime
import threading
import asyncio
import websockets
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

# 添加工具目录到系统路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 导入通信管理器和智能体
try:
    from communication_manager import CommunicationManager, QoSLevel, Priority
    from planner import Planner
    from executor import Executor
    modules_available = True
except ImportError as e:
    modules_available = False
    print(f"智能体模块导入错误: {e}")
    print("将使用模拟模式运行MCP服务")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("mcp_service")

class MCPService:
    """多通道协议服务，提供WebSocket接口供Cursor调用"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, mock_mode: bool = not modules_available):
        """初始化MCP服务
        
        Args:
            host: 服务主机地址
            port: 服务端口
            mock_mode: 是否使用模拟模式
        """
        self.host = host
        self.port = port
        self.clients = {}  # 连接的客户端
        self.agents = {}   # 注册的智能体
        self.running = False
        self.server = None
        self.mock_mode = mock_mode
        
        # 创建事件总线
        self.event_bus = EventBus()
        
        # 注册事件处理器
        self._register_event_handlers()
        
        logger.info(f"MCP服务初始化完成，监听地址: {host}:{port}, 模拟模式: {mock_mode}")
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        self.event_bus.subscribe("agent.registered", self._handle_agent_registered)
        self.event_bus.subscribe("agent.unregistered", self._handle_agent_unregistered)
        self.event_bus.subscribe("task.created", self._handle_task_created)
        self.event_bus.subscribe("task.completed", self._handle_task_completed)
        self.event_bus.subscribe("task.failed", self._handle_task_failed)
    
    async def start(self):
        """启动MCP服务"""
        if self.running:
            logger.warning("MCP服务已经在运行")
            return
        
        self.running = True
        
        # 启动WebSocket服务器
        self.server = await websockets.serve(
            self._handle_connection, 
            self.host, 
            self.port
        )
        
        logger.info(f"MCP服务已启动，监听: {self.host}:{self.port}")
    
    async def stop(self):
        """停止MCP服务"""
        if not self.running:
            logger.warning("MCP服务未在运行")
            return
        
        self.running = False
        
        # 关闭所有客户端连接
        for client_id, client in self.clients.items():
            try:
                await client["websocket"].close()
            except Exception as e:
                logger.error(f"关闭客户端 {client_id} 连接时出错: {e}")
        
        # 关闭WebSocket服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 停止所有智能体
        if not self.mock_mode:
            for agent_id, agent in self.agents.items():
                agent.stop()
        
        logger.info("MCP服务已停止")
    
    async def _handle_connection(self, websocket, path):
        """处理新的WebSocket连接"""
        client_id = str(uuid.uuid4())
        client_info = {
            "websocket": websocket,
            "connected_at": datetime.datetime.now().isoformat(),
            "last_activity": datetime.datetime.now().isoformat(),
            "agent_id": None
        }
        
        self.clients[client_id] = client_info
        logger.info(f"新客户端连接: {client_id}")
        
        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                "type": "welcome",
                "client_id": client_id,
                "message": "欢迎连接到MCP服务",
                "timestamp": datetime.datetime.now().isoformat()
            }))
            
            async for message in websocket:
                try:
                    # 更新最后活动时间
                    client_info["last_activity"] = datetime.datetime.now().isoformat()
                    
                    # 解析消息
                    data = json.loads(message)
                    await self._process_message(client_id, data)
                except json.JSONDecodeError:
                    logger.error(f"从客户端 {client_id} 收到无效JSON")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": "无效的JSON格式",
                        "timestamp": datetime.datetime.now().isoformat()
                    }))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端 {client_id} 断开连接")
        finally:
            # 移除客户端
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def _process_message(self, client_id: str, message: Dict[str, Any]):
        """处理从客户端收到的消息"""
        message_type = message.get("type")
        
        if message_type == "register":
            # 客户端注册为智能体
            await self._handle_register(client_id, message)
        elif message_type == "create_task":
            # 创建新任务
            await self._handle_create_task(client_id, message)
        elif message_type == "query_task":
            # 查询任务状态
            await self._handle_query_task(client_id, message)
        elif message_type == "agent_message":
            # 智能体间消息
            await self._handle_agent_message(client_id, message)
        elif message_type == "heartbeat":
            # 心跳消息
            await self._handle_heartbeat(client_id, message)
        else:
            # 未知消息类型
            logger.warning(f"收到未知消息类型: {message_type} 来自客户端 {client_id}")
            await self._send_to_client(client_id, {
                "type": "error",
                "error": f"未知消息类型: {message_type}",
                "timestamp": datetime.datetime.now().isoformat()
            })
    
    async def _handle_register(self, client_id: str, message: Dict[str, Any]):
        """处理客户端注册为智能体"""
        agent_type = message.get("agent_type")
        agent_id = message.get("agent_id", f"{agent_type}-{str(uuid.uuid4())[:8]}")
        
        # 更新客户端信息
        self.clients[client_id]["agent_id"] = agent_id
        
        if self.mock_mode:
            # 模拟模式下，只记录注册信息
            logger.info(f"模拟模式: 客户端 {client_id} 注册为 {agent_type}: {agent_id}")
            
            # 发布事件
            self.event_bus.publish("agent.registered", {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "client_id": client_id
            })
            
            # 发送确认消息
            await self._send_to_client(client_id, {
                "type": "registered",
                "agent_id": agent_id,
                "agent_type": agent_type,
                "message": f"模拟模式: 已成功注册为 {agent_type}",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 创建或获取智能体
        if agent_type == "planner":
            # 创建Planner
            planner = Planner(agent_id)
            planner.start()
            self.agents[agent_id] = planner
            
            # 发布事件
            self.event_bus.publish("agent.registered", {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "client_id": client_id
            })
            
            logger.info(f"客户端 {client_id} 注册为Planner: {agent_id}")
        elif agent_type == "executor":
            # 创建Executor
            executor = Executor(agent_id)
            executor.start()
            self.agents[agent_id] = executor
            
            # 发布事件
            self.event_bus.publish("agent.registered", {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "client_id": client_id
            })
            
            logger.info(f"客户端 {client_id} 注册为Executor: {agent_id}")
        else:
            # 未知智能体类型
            await self._send_to_client(client_id, {
                "type": "error",
                "error": f"未知智能体类型: {agent_type}",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 发送确认消息
        await self._send_to_client(client_id, {
            "type": "registered",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "message": f"已成功注册为 {agent_type}",
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    async def _handle_create_task(self, client_id: str, message: Dict[str, Any]):
        """处理创建任务请求"""
        # 检查客户端是否已注册
        agent_id = self.clients[client_id].get("agent_id")
        if not agent_id:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": "未注册的客户端无法创建任务",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 获取任务信息
        description = message.get("description")
        priority = message.get("priority", "medium")
        deadline = message.get("deadline")
        
        if self.mock_mode:
            # 模拟模式下，生成一个任务ID并返回
            task_id = f"task-{str(uuid.uuid4())[:8]}"
            logger.info(f"模拟模式: 客户端 {client_id} 创建任务: {task_id} - {description}")
            
            # 发布事件
            self.event_bus.publish("task.created", {
                "task_id": task_id,
                "description": description,
                "creator_id": agent_id
            })
            
            # 发送确认消息
            await self._send_to_client(client_id, {
                "type": "task_created",
                "task_id": task_id,
                "message": f"模拟模式: 任务已创建: {description}",
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # 模拟任务执行
            asyncio.create_task(self._simulate_task_execution(task_id, description))
            return
        
        # 找到Planner
        planner = None
        for aid, agent in self.agents.items():
            if isinstance(agent, Planner):
                planner = agent
                break
        
        if not planner:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": "系统中没有可用的Planner",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 创建任务
        task_id = planner.create_task(
            description=description,
            priority=priority,
            deadline=deadline
        )
        
        # 发布事件
        self.event_bus.publish("task.created", {
            "task_id": task_id,
            "description": description,
            "creator_id": agent_id
        })
        
        # 发送确认消息
        await self._send_to_client(client_id, {
            "type": "task_created",
            "task_id": task_id,
            "message": f"任务已创建: {description}",
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        logger.info(f"客户端 {client_id} 创建任务: {task_id}")
    
    async def _simulate_task_execution(self, task_id: str, description: str):
        """模拟任务执行过程"""
        # 等待3-8秒模拟执行时间
        execution_time = 3 + (hash(task_id) % 5)
        logger.info(f"模拟模式: 任务 {task_id} 开始执行，预计用时 {execution_time} 秒")
        
        await asyncio.sleep(execution_time)
        
        # 随机决定任务成功或失败
        if hash(task_id) % 10 == 0:
            # 模拟任务失败
            logger.info(f"模拟模式: 任务 {task_id} 执行失败")
            
            # 发布事件
            self.event_bus.publish("task.failed", {
                "task_id": task_id,
                "error": "模拟的执行错误"
            })
        else:
            # 模拟任务成功
            logger.info(f"模拟模式: 任务 {task_id} 执行成功")
            
            # 生成模拟结果
            result = {
                "status": "completed",
                "message": f"任务 {task_id} 已完成: {description}",
                "execution_time": execution_time,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # 发布事件
            self.event_bus.publish("task.completed", {
                "task_id": task_id,
                "result": result
            })
    
    async def _handle_query_task(self, client_id: str, message: Dict[str, Any]):
        """处理查询任务状态请求"""
        task_id = message.get("task_id")
        
        if self.mock_mode:
            # 模拟模式下，返回模拟的任务状态
            # 基于任务ID生成一个伪随机状态
            hash_val = hash(task_id)
            status_options = ["pending", "assigned", "running", "completed", "failed"]
            status = status_options[hash_val % len(status_options)]
            
            # 创建模拟结果
            result = None
            if status == "completed":
                result = {
                    "status": "completed",
                    "message": f"任务 {task_id} 已完成",
                    "execution_time": 3 + (hash_val % 5),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            
            # 发送任务状态
            await self._send_to_client(client_id, {
                "type": "task_status",
                "task_id": task_id,
                "status": status,
                "description": f"模拟任务 {task_id}",
                "assigned_to": "executor-mock" if status != "pending" else None,
                "created_at": (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "result": result,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            logger.info(f"模拟模式: 客户端 {client_id} 查询任务 {task_id} 状态: {status}")
            return
        
        # 找到Planner
        planner = None
        for aid, agent in self.agents.items():
            if isinstance(agent, Planner):
                planner = agent
                break
        
        if not planner:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": "系统中没有可用的Planner",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 查询任务
        task = planner.get_task(task_id)
        
        if not task:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": f"找不到任务: {task_id}",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 发送任务状态
        await self._send_to_client(client_id, {
            "type": "task_status",
            "task_id": task_id,
            "status": task.status,
            "description": task.description,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "result": task.result,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    async def _handle_agent_message(self, client_id: str, message: Dict[str, Any]):
        """处理智能体间的消息"""
        sender_id = self.clients[client_id].get("agent_id")
        if not sender_id:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": "未注册的客户端无法发送消息",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        target_id = message.get("target_id")
        content = message.get("content")
        
        if self.mock_mode:
            # 模拟模式下，只记录消息传递
            logger.info(f"模拟模式: 收到来自 {sender_id} 到 {target_id} 的消息")
            
            # 发送确认消息
            await self._send_to_client(client_id, {
                "type": "message_sent",
                "target_id": target_id,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # 模拟接收方收到消息
            for cid, client in self.clients.items():
                if client.get("agent_id") == target_id:
                    await self._send_to_client(cid, {
                        "type": "message",
                        "sender_id": sender_id,
                        "content": content,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    break
            return
        
        # 检查目标智能体是否存在
        if target_id not in self.agents:
            await self._send_to_client(client_id, {
                "type": "error",
                "error": f"目标智能体不存在: {target_id}",
                "timestamp": datetime.datetime.now().isoformat()
            })
            return
        
        # 构造消息
        agent_message = {
            "type": "message",
            "sender_id": sender_id,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 发送消息到目标智能体
        self.agents[target_id].send_message(agent_message)
        
        # 发送确认消息
        await self._send_to_client(client_id, {
            "type": "message_sent",
            "target_id": target_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    async def _handle_heartbeat(self, client_id: str, message: Dict[str, Any]):
        """处理心跳消息"""
        await self._send_to_client(client_id, {
            "type": "heartbeat_ack",
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """发送消息到客户端"""
        if client_id not in self.clients:
            logger.warning(f"尝试发送消息到不存在的客户端: {client_id}")
            return
        
        try:
            await self.clients[client_id]["websocket"].send(json.dumps(message))
        except Exception as e:
            logger.error(f"发送消息到客户端 {client_id} 时出错: {e}")
    
    def _handle_agent_registered(self, data: Dict[str, Any]):
        """处理智能体注册事件"""
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        
        if self.mock_mode:
            logger.info(f"模拟模式: 智能体 {agent_id} ({agent_type}) 已注册")
            return
        
        # 为Planner和Executor建立连接
        if agent_type == "executor":
            # 找到Planner并建立连接
            for aid, agent in self.agents.items():
                if isinstance(agent, Planner):
                    # 获取Executor和Planner
                    executor = self.agents[agent_id]
                    planner = agent
                    
                    # 建立双向连接
                    executor.add_planner(planner.planner_id, planner.comm_manager)
                    planner.add_executor(executor.executor_id, executor.comm_manager)
                    
                    logger.info(f"建立连接: Planner {planner.planner_id} <-> Executor {executor.executor_id}")
                    break
    
    def _handle_agent_unregistered(self, data: Dict[str, Any]):
        """处理智能体注销事件"""
        agent_id = data.get("agent_id")
        logger.info(f"智能体注销: {agent_id}")
    
    def _handle_task_created(self, data: Dict[str, Any]):
        """处理任务创建事件"""
        # 向所有连接的客户端广播任务创建通知
        message = {
            "type": "notification",
            "event": "task_created",
            "task_id": data.get("task_id"),
            "description": data.get("description"),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        asyncio.create_task(self._broadcast(message))
    
    def _handle_task_completed(self, data: Dict[str, Any]):
        """处理任务完成事件"""
        # 向所有连接的客户端广播任务完成通知
        message = {
            "type": "notification",
            "event": "task_completed",
            "task_id": data.get("task_id"),
            "result": data.get("result"),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        asyncio.create_task(self._broadcast(message))
    
    def _handle_task_failed(self, data: Dict[str, Any]):
        """处理任务失败事件"""
        # 向所有连接的客户端广播任务失败通知
        message = {
            "type": "notification",
            "event": "task_failed",
            "task_id": data.get("task_id"),
            "error": data.get("error"),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        asyncio.create_task(self._broadcast(message))
    
    async def _broadcast(self, message: Dict[str, Any]):
        """广播消息到所有客户端"""
        for client_id, client in self.clients.items():
            try:
                await client["websocket"].send(json.dumps(message))
            except Exception as e:
                logger.error(f"广播消息到客户端 {client_id} 时出错: {e}")

class EventBus:
    """事件总线，用于事件发布和订阅"""
    
    def __init__(self):
        """初始化事件总线"""
        self.subscribers = {}  # 事件订阅者
    
    def subscribe(self, event: str, callback: Callable):
        """订阅事件
        
        Args:
            event: 事件名称
            callback: 回调函数，接收事件数据作为参数
        """
        if event not in self.subscribers:
            self.subscribers[event] = []
        
        if callback not in self.subscribers[event]:
            self.subscribers[event].append(callback)
    
    def unsubscribe(self, event: str, callback: Callable):
        """取消订阅事件
        
        Args:
            event: 事件名称
            callback: 要取消的回调函数
        """
        if event in self.subscribers and callback in self.subscribers[event]:
            self.subscribers[event].remove(callback)
    
    def publish(self, event: str, data: Dict[str, Any]):
        """发布事件
        
        Args:
            event: 事件名称
            data: 事件数据
        """
        if event in self.subscribers:
            for callback in self.subscribers[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"执行事件 {event} 的回调时出错: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务 - 多通道协议服务")
    parser.add_argument("--host", default="localhost", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8765, help="服务端口")
    parser.add_argument("--mock", action="store_true", help="使用模拟模式")
    args = parser.parse_args()
    
    if args.mock or not modules_available:
        print("将使用模拟模式运行MCP服务")
    
    # 启动异步服务
    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        print("\n接收到中断信号，服务已停止")

async def _async_main(args):
    """异步主函数"""
    # 创建MCP服务
    service = MCPService(host=args.host, port=args.port, mock_mode=args.mock or not modules_available)
    
    # 启动服务
    await service.start()
    
    try:
        # 保持服务运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止服务...")
    finally:
        # 停止服务
        await service.stop()

if __name__ == "__main__":
    main() 