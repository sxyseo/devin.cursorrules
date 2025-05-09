#!/usr/bin/env python3
"""
Cursor连接客户端

连接到MCP服务的客户端实现，提供Cursor的多智能体调用功能。
支持与MCP服务的WebSocket通信，并提供对话界面。
"""

import os
import sys
import json
import uuid
import logging
import asyncio
import websockets
import argparse
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("cursor_connect")

class CursorClient:
    """Cursor连接客户端，提供与MCP服务的通信功能"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, 
                 agent_type: str = "cursor", agent_id: Optional[str] = None):
        """初始化Cursor客户端
        
        Args:
            host: MCP服务主机地址
            port: MCP服务端口
            agent_type: 智能体类型，默认为cursor
            agent_id: 智能体ID，如果不提供则自动生成
        """
        self.host = host
        self.port = port
        self.agent_type = agent_type
        self.agent_id = agent_id or f"{agent_type}-{str(uuid.uuid4())[:8]}"
        self.client_id = None
        self.websocket = None
        self.connected = False
        self.message_queue = asyncio.Queue()
        self.response_callbacks = {}
        self.notification_handlers = []
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.heartbeat_task = None
        self.receive_task = None
        self.process_task = None
        
        logger.info(f"Cursor客户端初始化完成，智能体ID: {self.agent_id}")
    
    async def connect(self):
        """连接到MCP服务"""
        if self.connected:
            logger.warning("已经连接到MCP服务")
            return
        
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"已连接到MCP服务: {uri}")
            
            # 初始化消息队列
            self.message_queue = asyncio.Queue()
            
            # 直接接收欢迎消息
            try:
                welcome_raw = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                welcome_message = json.loads(welcome_raw)
                
                if welcome_message.get("type") == "welcome":
                    self.client_id = welcome_message.get("client_id")
                    self.connected = True
                    logger.info(f"已获取客户端ID: {self.client_id}")
                    
                    # 注册为智能体
                    await self._register()
                    
                    # 接收注册确认消息
                    register_raw = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                    register_message = json.loads(register_raw)
                    
                    if register_message.get("type") == "registered":
                        logger.info(f"已成功注册为智能体: {self.agent_id}")
                        
                        # 启动接收和处理任务
                        self.receive_task = asyncio.create_task(self._receive_messages())
                        self.process_task = asyncio.create_task(self._process_messages())
                        
                        # 启动心跳任务
                        self.heartbeat_task = asyncio.create_task(self._send_heartbeat())
                    else:
                        logger.warning(f"未收到注册确认，而是: {register_message.get('type')}")
                        # 仍然继续执行
                        self.receive_task = asyncio.create_task(self._receive_messages())
                        self.process_task = asyncio.create_task(self._process_messages())
                        self.heartbeat_task = asyncio.create_task(self._send_heartbeat())
                else:
                    logger.error(f"未收到欢迎消息，而是: {welcome_message.get('type')}")
                    await self.disconnect()
                    raise RuntimeError(f"连接失败：未收到欢迎消息，而是 {welcome_message.get('type')}")
            except asyncio.TimeoutError:
                logger.error("等待欢迎或注册消息超时")
                await self.disconnect()
                raise RuntimeError("连接超时：未收到必要的消息")
            except json.JSONDecodeError as e:
                logger.error(f"消息解析错误: {e}")
                await self.disconnect()
                raise RuntimeError("连接失败：消息格式无效")
        except Exception as e:
            logger.error(f"连接到MCP服务时出错: {e}")
            if hasattr(e, '__traceback__'):
                logger.error(traceback.format_exc())
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            raise
    
    async def disconnect(self):
        """断开与MCP服务的连接"""
        if not self.connected and not self.websocket:
            logger.warning("未连接到MCP服务")
            return
        
        self.connected = False
        
        # 取消心跳任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"取消心跳任务时出错: {e}")
            self.heartbeat_task = None
        
        # 取消接收任务
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"取消接收任务时出错: {e}")
            self.receive_task = None
        
        # 取消处理任务
        if self.process_task:
            self.process_task.cancel()
            try:
                await self.process_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"取消处理任务时出错: {e}")
            self.process_task = None
        
        # 关闭WebSocket连接
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {e}")
            self.websocket = None
        
        logger.info("已断开与MCP服务的连接")
    
    async def _register(self):
        """注册为智能体"""
        register_message = {
            "type": "register",
            "agent_type": self.agent_type,
            "agent_id": self.agent_id
        }
        
        await self.websocket.send(json.dumps(register_message))
        logger.info(f"已发送注册消息，智能体类型: {self.agent_type}, ID: {self.agent_id}")
    
    async def _receive_messages(self):
        """接收消息任务"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.message_queue.put(data)
                except json.JSONDecodeError:
                    logger.error(f"收到无效的JSON消息: {message[:100]}...")
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"WebSocket连接已关闭: {e}")
            self.connected = False
        except asyncio.CancelledError:
            logger.info("接收消息任务已取消")
            raise
        except Exception as e:
            logger.error(f"接收消息时出错: {e}")
            logger.error(traceback.format_exc())
            self.connected = False
    
    async def _process_messages(self):
        """处理消息任务"""
        while True:
            try:
                message = await self.message_queue.get()
                message_type = message.get("type")
                
                logger.debug(f"收到消息类型: {message_type}")
                
                # 检查是否有欢迎消息回调
                if hasattr(self, '_welcome_callback') and message_type == "welcome":
                    self._welcome_callback(message)
                    continue
                
                # 检查是否有注册确认回调
                if hasattr(self, '_registration_callback') and message_type == "registered":
                    self._registration_callback(message)
                    continue
                
                if message_type == "welcome":
                    # 欢迎消息已经在connect方法中处理
                    pass
                elif message_type == "registered":
                    # 注册确认
                    logger.info(f"已成功注册为智能体: {message.get('agent_id')}")
                elif message_type == "task_created":
                    # 任务创建确认
                    task_id = message.get("task_id")
                    logger.info(f"任务已创建: {task_id}")
                    
                    # 调用回调
                    for callback_id, callback in list(self.response_callbacks.items()):
                        if callback_id.startswith("task_created_"):
                            callback(message)
                            del self.response_callbacks[callback_id]
                            break
                elif message_type == "task_status":
                    # 任务状态
                    task_id = message.get("task_id")
                    status = message.get("status")
                    logger.info(f"任务状态: {task_id} - {status}")
                    
                    # 调用回调
                    callback_id = f"task_status_{task_id}"
                    if callback_id in self.response_callbacks:
                        self.response_callbacks[callback_id](message)
                        del self.response_callbacks[callback_id]
                elif message_type == "message":
                    # 来自其他智能体的消息
                    sender_id = message.get("sender_id")
                    content = message.get("content")
                    logger.info(f"收到来自 {sender_id} 的消息: {content}")
                elif message_type == "notification":
                    # 通知
                    event = message.get("event")
                    logger.info(f"收到通知: {event}")
                    
                    # 调用所有通知处理器
                    for handler in self.notification_handlers:
                        handler(message)
                elif message_type == "error":
                    # 错误消息
                    error = message.get("error")
                    logger.error(f"收到错误: {error}")
                elif message_type == "heartbeat_ack":
                    # 心跳确认
                    logger.debug("收到心跳确认")
                else:
                    # 未知消息类型
                    logger.warning(f"收到未知消息类型: {message_type}")
                
                # 标记消息已处理
                self.message_queue.task_done()
            except asyncio.CancelledError:
                logger.info("消息处理任务已取消")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
    
    async def _send_heartbeat(self):
        """发送心跳消息任务"""
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.connected and self.websocket:
                    await self.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "agent_id": self.agent_id
                    }))
                    logger.debug("已发送心跳消息")
            except asyncio.CancelledError:
                logger.info("心跳任务已取消")
                break
            except Exception as e:
                logger.error(f"发送心跳消息时出错: {e}")
                await asyncio.sleep(5)  # 出错后等待一段时间再重试
    
    async def create_task(self, description: str, priority: str = "medium", 
                         deadline: Optional[str] = None) -> Dict[str, Any]:
        """创建任务
        
        Args:
            description: 任务描述
            priority: 任务优先级，可以是"high"、"medium"或"low"
            deadline: 任务截止时间，ISO8601格式
        
        Returns:
            任务创建结果
        """
        if not self.connected:
            raise RuntimeError("未连接到MCP服务")
        
        # 创建任务消息
        task_message = {
            "type": "create_task",
            "description": description,
            "priority": priority,
            "deadline": deadline
        }
        
        # 创建Future对象用于等待响应
        future = asyncio.Future()
        
        # 创建回调函数
        def callback(response):
            if not future.done():
                future.set_result(response)
        
        # 生成唯一回调ID
        callback_id = f"task_created_{str(uuid.uuid4())}"
        self.response_callbacks[callback_id] = callback
        
        # 发送消息
        await self.websocket.send(json.dumps(task_message))
        logger.info(f"已发送任务创建请求: {description}")
        
        # 等待响应
        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            logger.info(f"已收到任务创建响应")
            return response
        except asyncio.TimeoutError:
            # 移除回调
            if callback_id in self.response_callbacks:
                del self.response_callbacks[callback_id]
            
            raise TimeoutError("创建任务超时")
    
    async def query_task(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        if not self.connected:
            raise RuntimeError("未连接到MCP服务")
        
        # 创建查询消息
        query_message = {
            "type": "query_task",
            "task_id": task_id
        }
        
        # 创建Future对象用于等待响应
        future = asyncio.Future()
        
        # 创建回调函数
        def callback(response):
            if not future.done():
                future.set_result(response)
        
        # 注册回调
        callback_id = f"task_status_{task_id}"
        self.response_callbacks[callback_id] = callback
        
        # 发送消息
        await self.websocket.send(json.dumps(query_message))
        logger.info(f"已发送任务查询请求: {task_id}")
        
        # 等待响应
        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            logger.info(f"已收到任务查询响应")
            return response
        except asyncio.TimeoutError:
            # 移除回调
            if callback_id in self.response_callbacks:
                del self.response_callbacks[callback_id]
            
            raise TimeoutError(f"查询任务 {task_id} 超时")
    
    async def send_message(self, target_id: str, content: Dict[str, Any]) -> bool:
        """发送消息到其他智能体
        
        Args:
            target_id: 目标智能体ID
            content: 消息内容
        
        Returns:
            是否发送成功
        """
        if not self.connected:
            raise RuntimeError("未连接到MCP服务")
        
        # 创建消息
        agent_message = {
            "type": "agent_message",
            "target_id": target_id,
            "content": content
        }
        
        # 发送消息
        await self.websocket.send(json.dumps(agent_message))
        return True
    
    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """添加通知处理器
        
        Args:
            handler: 处理通知的回调函数
        """
        if handler not in self.notification_handlers:
            self.notification_handlers.append(handler)
    
    def remove_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """移除通知处理器
        
        Args:
            handler: 要移除的处理器
        """
        if handler in self.notification_handlers:
            self.notification_handlers.remove(handler)

class CursorApp:
    """基于控制台的Cursor应用，提供交互式界面"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """初始化Cursor应用
        
        Args:
            host: MCP服务主机地址
            port: MCP服务端口
        """
        self.client = CursorClient(host=host, port=port)
        self.running = False
        self.current_task_id = None
    
    async def start(self):
        """启动应用"""
        print("Cursor智能体客户端")
        print("====================")
        print(f"正在连接到MCP服务: {self.client.host}:{self.client.port}")
        
        try:
            await self.client.connect()
            self.running = True
            
            # 添加通知处理器
            self.client.add_notification_handler(self._handle_notification)
            
            # 显示主菜单
            await self._main_loop()
        except Exception as e:
            print(f"启动应用时出错: {e}")
        finally:
            await self.client.disconnect()
    
    async def _main_loop(self):
        """主循环"""
        while self.running:
            print("\n主菜单:")
            print("1. 创建任务")
            print("2. 查询任务状态")
            print("3. 发送消息到其他智能体")
            print("4. 退出")
            
            choice = input("请选择操作 [1-4]: ").strip()
            
            if choice == "1":
                await self._create_task()
            elif choice == "2":
                await self._query_task()
            elif choice == "3":
                await self._send_message()
            elif choice == "4":
                self.running = False
                print("正在退出...")
            else:
                print("无效选择，请重试")
    
    async def _create_task(self):
        """创建任务"""
        print("\n创建新任务")
        print("============")
        
        description = input("任务描述: ").strip()
        if not description:
            print("任务描述不能为空")
            return
        
        priority_map = {"1": "high", "2": "medium", "3": "low"}
        priority_input = input("任务优先级 [1-高, 2-中, 3-低，默认中]: ").strip()
        priority = priority_map.get(priority_input, "medium")
        
        deadline_input = input("任务截止时间 (ISO8601格式，留空表示无截止时间): ").strip()
        deadline = deadline_input if deadline_input else None
        
        try:
            print("正在创建任务...")
            response = await self.client.create_task(description, priority, deadline)
            
            if "task_id" in response:
                self.current_task_id = response["task_id"]
                print(f"任务已创建！ID: {self.current_task_id}")
                print(f"消息: {response.get('message', '')}")
            else:
                print("创建任务失败")
        except Exception as e:
            print(f"创建任务时出错: {e}")
    
    async def _query_task(self):
        """查询任务状态"""
        print("\n查询任务状态")
        print("==============")
        
        task_id = input(f"任务ID (当前: {self.current_task_id or '无'}): ").strip()
        if not task_id:
            if not self.current_task_id:
                print("任务ID不能为空")
                return
            task_id = self.current_task_id
        
        try:
            print(f"正在查询任务 {task_id} 的状态...")
            response = await self.client.query_task(task_id)
            
            if "task_id" in response:
                print("\n任务详情:")
                print(f"ID: {response['task_id']}")
                print(f"描述: {response.get('description', '无')}")
                print(f"状态: {response.get('status', '未知')}")
                print(f"分配给: {response.get('assigned_to', '无')}")
                print(f"创建时间: {response.get('created_at', '未知')}")
                print(f"更新时间: {response.get('updated_at', '未知')}")
                
                if response.get('result'):
                    print("\n任务结果:")
                    print(json.dumps(response['result'], indent=2, ensure_ascii=False))
            else:
                print("查询任务失败")
        except Exception as e:
            print(f"查询任务时出错: {e}")
    
    async def _send_message(self):
        """发送消息到其他智能体"""
        print("\n发送消息")
        print("==========")
        
        target_id = input("目标智能体ID: ").strip()
        if not target_id:
            print("目标智能体ID不能为空")
            return
        
        message_type = input("消息类型: ").strip()
        if not message_type:
            print("消息类型不能为空")
            return
        
        message_content = input("消息内容 (JSON格式): ").strip()
        if not message_content:
            print("消息内容不能为空")
            return
        
        try:
            content_obj = json.loads(message_content)
        except json.JSONDecodeError:
            print("无效的JSON格式")
            return
        
        content = {
            "message_type": message_type,
            "data": content_obj
        }
        
        try:
            print(f"正在发送消息到 {target_id}...")
            success = await self.client.send_message(target_id, content)
            
            if success:
                print("消息已发送")
            else:
                print("发送消息失败")
        except Exception as e:
            print(f"发送消息时出错: {e}")
    
    def _handle_notification(self, notification: Dict[str, Any]):
        """处理通知"""
        event = notification.get("event")
        if event == "task_created":
            task_id = notification.get("task_id")
            description = notification.get("description")
            print(f"\n[通知] 任务已创建: {task_id} - {description}")
        elif event == "task_completed":
            task_id = notification.get("task_id")
            print(f"\n[通知] 任务已完成: {task_id}")
            if notification.get("result"):
                print(f"结果: {json.dumps(notification['result'], ensure_ascii=False)}")
        elif event == "task_failed":
            task_id = notification.get("task_id")
            error = notification.get("error")
            print(f"\n[通知] 任务失败: {task_id} - {error}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Cursor连接客户端")
    parser.add_argument("--host", default="localhost", help="MCP服务主机地址")
    parser.add_argument("--port", type=int, default=8765, help="MCP服务端口")
    parser.add_argument("--interactive", action="store_true", help="启动交互式应用")
    args = parser.parse_args()
    
    # 运行异步函数
    try:
        if args.interactive:
            # 启动交互式应用
            app = CursorApp(host=args.host, port=args.port)
            asyncio.run(app.start())
        else:
            # 作为客户端库使用
            asyncio.run(_run_client(args.host, args.port))
    except KeyboardInterrupt:
        print("\n接收到中断信号，客户端已停止")

async def _run_client(host, port):
    """运行客户端"""
    client = CursorClient(host=host, port=port)
    await client.connect()
    
    try:
        print(f"客户端已连接，智能体ID: {client.agent_id}")
        print("按Ctrl+C退出...")
        
        # 保持客户端运行，直到用户中断
        while True:
            await asyncio.sleep(1)
    finally:
        await client.disconnect()

if __name__ == "__main__":
    main() 