#!/usr/bin/env python3
"""
多智能体MCP服务器

为Cursor提供增强型多智能体协作功能的MCP服务器。
集成了记忆银行、Planner、Executor等核心组件。
支持多种协议: stdio、SSE、HTTP 和 WebSocket。
"""

import os
import sys
import json
import asyncio
import logging
import datetime
import importlib
import traceback
import argparse
import threading
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, AsyncGenerator

# 添加父目录到系统路径以便导入工具模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 尝试导入FastMCP和FastAPI
try:
    # 导入MCP库
    from mcp.server.fastmcp import FastMCP
    
    HAS_FASTMCP = True
except ImportError as e:
    HAS_FASTMCP = False
    print(f"无法导入MCP依赖: {e}")

try:
    # 导入FastAPI
    from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from sse_starlette.sse import EventSourceResponse
    import uvicorn
    
    HAS_FASTAPI = True
except ImportError as e:
    HAS_FASTAPI = False
    print(f"无法导入FastAPI依赖: {e}，HTTP接口将不可用")

# 初始化模块可用性标志
MODULES = {
    "memory_manager": False,
    "memory_index": False,
    "memory_sync": False,
    "llm_api": False,
    "error_handler": False,
    "planner": False,
    "executor": False,
    "communication_manager": False
}

# 记忆银行路径
MEMORY_BANK_DIR = Path(parent_dir) / "memory-bank"

# 尝试导入各个模块
try:
    # 导入memory_manager模块
    from tools import memory_manager
    MODULES["memory_manager"] = True
except ImportError as e:
    print(f"导入memory_manager模块失败: {e}")

try:
    # 导入memory_index模块
    from tools import memory_index
    MODULES["memory_index"] = True
except ImportError as e:
    print(f"导入memory_index模块失败: {e}")

try:
    # 导入memory_sync模块
    from tools import memory_sync
    MODULES["memory_sync"] = True
except ImportError as e:
    print(f"导入memory_sync模块失败: {e}")

try:
    # 导入llm_api模块
    from tools.llm_api import query_llm, create_llm_client, mock_response
    MODULES["llm_api"] = True
except ImportError as e:
    print(f"导入llm_api模块失败: {e}")

try:
    # 导入error_handler模块
    from tools.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
    MODULES["error_handler"] = True
except ImportError as e:
    print(f"导入error_handler模块失败: {e}")

try:
    # 导入通信管理器
    from tools.communication_manager import CommunicationManager
    MODULES["communication_manager"] = True
except ImportError as e:
    print(f"导入communication_manager模块失败: {e}")

try:
    # 导入planner模块
    from tools.planner import Planner
    MODULES["planner"] = True
except ImportError as e:
    print(f"导入planner模块失败: {e}")

try:
    # 导入executor模块
    from tools.executor import Executor
    MODULES["executor"] = True
except ImportError as e:
    print(f"导入executor模块失败: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("multi_agent_mcp")

# 初始化MCP服务器
if HAS_FASTMCP:
    mcp = FastMCP("multi_agent_mcp")
else:
    # 创建模拟MCP对象
    class MockFastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = {}
        
        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator
        
        def run(self):
            print(f"模拟MCP服务器 {self.name} 启动")
    
    mcp = MockFastMCP("multi_agent_mcp")
    print("使用模拟MCP服务器")

# 全局变量
error_handler = None
planner = None
executor = None
tasks = {}
ENABLE_SIMULATION_MODE = True  # 默认启用模拟模式，确保基本功能可用
SIMULATION_RESPONSES = {
    "read_memory": lambda file_path: json.dumps({
        "status": "success", 
        "content": f"这是模拟的内容，用于示例。这是来自文件 {file_path} 的模拟内容。\n\n"
                   f"# {file_path.split('/')[-1].split('.')[0]} 示例文档\n\n"
                   f"这是一个用于演示记忆银行功能的示例文档。\n\n"
                   f"在实际使用时，您需要确保：\n"
                   f"1. 记忆银行目录已正确设置\n"
                   f"2. {file_path} 文件已创建并包含内容\n"
                   f"3. MCP服务器运行在非模拟模式下\n\n"
                   f"您还可以使用其他记忆银行工具：\n"
                   f"- list_memory_files：列出所有记忆文件\n"
                   f"- search_memory：搜索记忆内容\n"
                   f"- update_memory：更新记忆文件内容",
        "simulation": True
    }, ensure_ascii=False),
    "list_memory_files": lambda: json.dumps([
        "projectbrief.md",
        "productContext.md",
        "systemPatterns.md",
        "techContext.md",
        "activeContext.md",
        "progress.md",
        "extensions/api_docs.md",
        "extensions/feature_docs.md"
    ]),
    "search_memory": lambda query, top_k=5: json.dumps([
        {
            "file": "activeContext.md",
            "content": "当前工作重点是优化多智能体协作框架。",
            "similarity": 0.95
        },
        {
            "file": "systemPatterns.md",
            "content": "多智能体协作框架采用Planner-Executor模式。",
            "similarity": 0.85
        },
        {
            "file": "progress.md",
            "content": "已完成多智能体协作框架的基础功能。",
            "similarity": 0.75
        }
    ], ensure_ascii=False),
    "update_memory": lambda file_path, content: json.dumps({
        "status": "success",
        "message": f"文件 {file_path} 已成功更新",
        "simulation": True
    }),
    "create_task": lambda description, priority="medium": json.dumps({
        "task_id": f"task-{hash(description) % 1000}",
        "status": "created",
        "priority": priority,
        "description": description,
        "simulation": True
    }),
    "get_task_status": lambda task_id: json.dumps({
        "id": task_id,
        "status": "in_progress",
        "priority": "medium",
        "description": "模拟任务",
        "assigned_to": "executor-1",
        "created_at": "2025-05-09T00:00:00Z",
        "updated_at": "2025-05-09T00:10:00Z",
        "simulation": True
    }),
    "list_tasks": lambda: json.dumps([
        {
            "id": "task-1",
            "status": "completed",
            "priority": "high",
            "description": "建立基础框架",
            "assigned_to": "executor-1"
        },
        {
            "id": "task-2",
            "status": "in_progress",
            "priority": "medium",
            "description": "实现记忆管理",
            "assigned_to": "executor-2"
        },
        {
            "id": "task-3",
            "status": "pending",
            "priority": "low",
            "description": "优化性能",
            "assigned_to": None
        }
    ], ensure_ascii=False),
    "call_llm": lambda prompt, provider="openai", model=None: (
        f"这是对提示词 '{prompt}' 的模拟响应。\n\n"
        f"由于这是模拟模式，实际上没有调用任何LLM API。\n"
        f"在实际模式下，会调用 {provider} 的 {model or '默认模型'}。\n\n"
        f"如果您提到了服务器相关内容，这里是一些信息：\n"
        f"服务器使用FastMCP框架实现，与Cursor完全兼容，提供了丰富的工具功能，可以极大增强Cursor中Claude的能力。\n"
        f"通过这种方式，我们可以让Cursor具备持久化记忆、多智能体协作和强大的任务分解能力，更好地辅助复杂的开发工作。"
    ),
    "analyze_task": lambda task_description: json.dumps({
        "title": "任务分析",
        "description": task_description,
        "subtasks": [
            {"id": "1", "description": "子任务1: 研究问题域", "dependencies": []},
            {"id": "2", "description": "子任务2: 设计解决方案", "dependencies": ["1"]},
            {"id": "3", "description": "子任务3: 实现核心功能", "dependencies": ["1", "2"]},
            {"id": "4", "description": "子任务4: 测试和验证", "dependencies": ["3"]},
            {"id": "5", "description": "子任务5: 部署和监控", "dependencies": ["3", "4"]}
        ],
        "simulation": True
    }, ensure_ascii=False),
    "check_health": lambda: json.dumps({
        "status": "healthy",
        "components": {
            "memory_manager": "online",
            "memory_index": "online",
            "memory_sync": "online",
            "llm_api": "online",
            "planner": "online",
            "executor": "online",
            "error_handler": "online"
        },
        "version": "1.0.0",
        "simulation": True
    }, indent=2)
}

# 初始化HTTP API (如果FastAPI可用)
if HAS_FASTAPI:
    app = FastAPI(title="MCP服务API", description="多智能体MCP服务的HTTP API接口")
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app = None

# 初始化组件
def init_components():
    """初始化所有组件"""
    global error_handler, planner, executor, ENABLE_SIMULATION_MODE
    
    try:
        # 加载环境变量
        load_env_vars()
        
        # 如果需要关闭模拟模式，确保模拟模式被禁用
        ENABLE_SIMULATION_MODE = False
        logger.info("禁用模拟模式，使用实际组件")
        
        # 确保记忆银行目录存在
        MEMORY_BANK_DIR.mkdir(exist_ok=True)
        if not (MEMORY_BANK_DIR / "extensions").exists():
            (MEMORY_BANK_DIR / "extensions").mkdir(exist_ok=True)
        
        # 初始化错误处理器
        if MODULES["error_handler"]:
            error_handler = ErrorHandler()
            logger.info("错误处理器初始化完成")
        else:
            # 创建一个简单的错误处理器模拟
            class MockErrorHandler:
                def handle_error(self, error, category=None, severity=None, context=None):
                    logger.error(f"错误: {error}, 类别: {category}, 严重程度: {severity}, 上下文: {context}")
            error_handler = MockErrorHandler()
            logger.info("使用模拟错误处理器")
        
        # 初始化Planner和Executor
        if MODULES["planner"] and MODULES["executor"] and MODULES["communication_manager"]:
            try:
                # 创建通信管理器实例，确保两个组件使用各自的通信管理器
                from tools.communication_manager import CommunicationManager
                planner_comm = CommunicationManager("mcp-planner", "planner")
                executor_comm = CommunicationManager("mcp-executor", "executor")
                
                # 创建Planner和Executor实例，确保传入正确的通信管理器
                from tools.planner import Planner
                from tools.executor import Executor
                
                planner = Planner("mcp-planner")
                planner.comm_manager = planner_comm
                
                executor = Executor("mcp-executor")
                executor.comm_manager = executor_comm
                
                # 连接Planner和Executor
                planner.add_executor(executor.executor_id, executor.comm_manager)
                executor.add_planner(planner.planner_id, planner.comm_manager)
                
                # 启动智能体
                planner.start()
                executor.start()
                
                logger.info("Planner和Executor初始化并启动完成")
            except Exception as e:
                logger.error(f"启动Planner和Executor时出错: {e}")
                logger.error(traceback.format_exc())
                # 启动失败时使用模拟版本
                planner = None
                executor = None
                logger.info("使用模拟版本的Planner和Executor")
        else:
            planner = None
            executor = None
            logger.info("缺少智能体组件，使用模拟版本")
        
        # 打印模块可用性状态
        logger.info(f"模块可用性状态: {json.dumps(MODULES, indent=2)}")
        
        logger.info("所有组件初始化完成")
    except Exception as e:
        logger.error(f"初始化组件时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.INITIALIZATION if MODULES["error_handler"] else "INITIALIZATION", 
                severity=ErrorSeverity.HIGH if MODULES["error_handler"] else "HIGH", 
                context={"component": "init_components"}
            )

# 加载环境变量
def load_env_vars():
    """加载环境变量"""
    try:
        from dotenv import load_dotenv
        # 先尝试加载当前目录的.env文件
        load_dotenv()
        # 再尝试加载项目根目录的.env文件
        parent_env = Path(parent_dir) / ".env"
        if parent_env.exists():
            load_dotenv(dotenv_path=parent_env)
        # 最后尝试加载模块目录的.env文件
        module_env = Path(current_dir) / ".env"
        if module_env.exists():
            load_dotenv(dotenv_path=module_env)
        
        # 设置模拟模式
        global ENABLE_SIMULATION_MODE
        ENABLE_SIMULATION_MODE = os.getenv("ENABLE_SIMULATION_MODE", "true").lower() in ("true", "1", "yes")
        if ENABLE_SIMULATION_MODE:
            logger.info("启用模拟模式")
        
    except ImportError:
        logger.warning("无法导入python-dotenv，环境变量可能未正确加载")

# 记忆银行工具
@mcp.tool()
async def read_memory(file_path: str) -> str:
    """读取记忆银行中的文件内容
    
    Args:
        file_path: 要读取的文件路径，相对于记忆银行根目录
    
    Returns:
        文件内容字符串
    """
    try:
        # 如果启用了模拟模式，返回模拟数据
        if ENABLE_SIMULATION_MODE:
            return json.dumps({
                "status": "success",
                "content": f"这是模拟的内容，用于示例。这是来自文件 {file_path} 的模拟内容。\n\n"
                           f"# {file_path.split('/')[-1].split('.')[0]} 示例文档\n\n"
                           f"这是一个用于演示记忆银行功能的示例文档。\n\n"
                           f"在实际使用时，您需要确保：\n"
                           f"1. 记忆银行目录已正确设置\n"
                           f"2. {file_path} 文件已创建并包含内容\n"
                           f"3. MCP服务器运行在非模拟模式下\n\n"
                           f"您还可以使用其他记忆银行工具：\n"
                           f"- list_memory_files：列出所有记忆文件\n"
                           f"- search_memory：搜索记忆内容\n"
                           f"- update_memory：更新记忆文件内容",
                "simulation": True
            })
        
        if not MODULES["memory_manager"]:
            return json.dumps({
                "status": "error",
                "message": "记忆管理器模块不可用",
                "simulation": True
            })
        
        # 构建完整路径
        file_path = str(file_path).strip().lstrip("/")
        full_path = MEMORY_BANK_DIR / file_path
        
        # 检查文件是否存在
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}"
            })
        
        # 读取文件内容
        content = memory_manager.read_file(str(full_path))
        
        return json.dumps({
            "status": "success",
            "content": content
        })
    except Exception as e:
        error_msg = f"读取记忆文件时出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.FILE_OPERATION if MODULES["error_handler"] else "FILE_OPERATION", 
                severity=ErrorSeverity.MEDIUM if MODULES["error_handler"] else "MEDIUM", 
                context={"file_path": file_path}
            )
        
        return json.dumps({
            "status": "error",
            "message": error_msg
        })

@mcp.tool()
async def update_memory(file_path: str, content: str) -> str:
    """更新记忆银行中的文件内容
    
    Args:
        file_path: 要更新的文件路径，相对于记忆银行根目录
        content: 新的文件内容
    """
    logger.info(f"更新记忆文件: {file_path}")
    
    if not MODULES["memory_manager"]:
        return f"模拟模式: 文件 {file_path} 已成功更新。"
    
    try:
        success = memory_manager.update_memory_file(file_path, content)
        if success:
            return f"文件 {file_path} 已成功更新"
        else:
            return f"更新文件 {file_path} 失败"
    except Exception as e:
        logger.error(f"更新记忆文件时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.FILE_OPERATION, 
                severity=ErrorSeverity.MEDIUM,
                context={"file_path": file_path}
            )
        return f"更新文件时出错: {str(e)}"

@mcp.tool()
async def list_memory_files() -> str:
    """列出记忆银行中的所有文件"""
    logger.info("列出记忆银行文件")
    
    if not MODULES["memory_manager"]:
        mock_files = [
            "projectbrief.md",
            "productContext.md",
            "systemPatterns.md",
            "techContext.md",
            "activeContext.md",
            "progress.md",
            "extensions/api_docs.md",
            "extensions/feature_docs.md"
        ]
        return json.dumps(mock_files, indent=2)
    
    try:
        files = memory_manager.list_memory_files()
        return json.dumps(files, indent=2)
    except Exception as e:
        logger.error(f"列出记忆文件时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.FILE_OPERATION, 
                severity=ErrorSeverity.MEDIUM
            )
        return f"列出文件时出错: {str(e)}"

@mcp.tool()
async def search_memory(query: str, top_k: int = 5) -> str:
    """在记忆银行中进行语义搜索
    
    Args:
        query: 搜索查询
        top_k: 返回的结果数量
    """
    logger.info(f"搜索记忆: {query}")
    
    if not MODULES["memory_index"]:
        mock_results = [
            {
                "file": "activeContext.md",
                "content": "当前工作重点是优化多智能体协作框架。",
                "similarity": 0.95
            },
            {
                "file": "systemPatterns.md",
                "content": "多智能体协作框架采用Planner-Executor模式。",
                "similarity": 0.85
            },
            {
                "file": "progress.md",
                "content": "已完成多智能体协作框架的基础功能。",
                "similarity": 0.75
            }
        ]
        return json.dumps(mock_results, indent=2, ensure_ascii=False)
    
    try:
        results = memory_index.search(query, top_k=top_k)
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"搜索记忆时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.SEARCH, 
                severity=ErrorSeverity.MEDIUM,
                context={"query": query}
            )
        return f"搜索记忆时出错: {str(e)}"

@mcp.tool()
async def sync_memory() -> str:
    """同步记忆银行，创建快照"""
    logger.info("同步记忆银行")
    
    if not MODULES["memory_sync"]:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"模拟模式: 记忆银行已同步，快照: {timestamp}"
    
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        success = memory_sync.backup_memory_bank(timestamp)
        return f"记忆银行已同步，快照: {timestamp}" if success else "同步记忆银行失败"
    except Exception as e:
        logger.error(f"同步记忆银行时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.SYNC, 
                severity=ErrorSeverity.MEDIUM
            )
        return f"同步记忆银行时出错: {str(e)}"

@mcp.tool()
async def create_memory_file(file_path: str, content: Optional[str] = None) -> str:
    """创建新的记忆银行文件
    
    Args:
        file_path: 要创建的文件路径，相对于记忆银行根目录
        content: 文件内容，如果为None则使用默认模板
    """
    logger.info(f"创建记忆文件: {file_path}")
    
    if not MODULES["memory_manager"]:
        return f"模拟模式: 文件 {file_path} 已成功创建。"
    
    try:
        success = memory_manager.create_memory_file(file_path, template=content)
        return f"文件 {file_path} 已成功创建" if success else f"创建文件 {file_path} 失败"
    except Exception as e:
        logger.error(f"创建记忆文件时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.FILE_OPERATION, 
                severity=ErrorSeverity.MEDIUM,
                context={"file_path": file_path}
            )
        return f"创建文件时出错: {str(e)}"

# 任务管理工具
@mcp.tool()
async def create_task(description: str, priority: str = "medium") -> str:
    """创建新任务
    
    Args:
        description: 任务描述
        priority: 任务优先级 (high, medium, low)
    """
    logger.info(f"创建任务: {description}")
    
    # 如果启用模拟模式或planner模块不可用，使用模拟数据
    if ENABLE_SIMULATION_MODE or not MODULES["planner"]:
        return SIMULATION_RESPONSES["create_task"](description, priority)
    
    try:
        task_id = planner.create_task(description=description, priority=priority)
        return json.dumps({"task_id": task_id, "status": "created"})
    except Exception as e:
        logger.error(f"创建任务时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.TASK_MANAGEMENT, 
                severity=ErrorSeverity.MEDIUM,
                context={"description": description}
            )
        # 出错时返回模拟数据
        return SIMULATION_RESPONSES["create_task"](description, priority)

@mcp.tool()
async def get_task_status(task_id: str) -> str:
    """获取任务状态
    
    Args:
        task_id: 任务ID
    """
    logger.info(f"获取任务状态: {task_id}")
    
    # 如果启用模拟模式或planner模块不可用，使用模拟数据
    if ENABLE_SIMULATION_MODE or not MODULES["planner"]:
        return SIMULATION_RESPONSES["get_task_status"](task_id)
    
    try:
        task = planner.get_task(task_id)
        if task:
            task_data = {
                "id": task.task_id,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assigned_to": task.assigned_to,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            }
            
            # 添加结果（如果有）
            if hasattr(task, 'result') and task.result:
                task_data["result"] = task.result
                
            return json.dumps(task_data, ensure_ascii=False)
        return json.dumps({"error": "任务不存在"})
    except Exception as e:
        logger.error(f"获取任务状态时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.TASK_MANAGEMENT, 
                severity=ErrorSeverity.MEDIUM,
                context={"task_id": task_id}
            )
        # 出错时返回模拟数据
        return SIMULATION_RESPONSES["get_task_status"](task_id)

@mcp.tool()
async def list_tasks() -> str:
    """列出所有任务"""
    logger.info("列出所有任务")
    
    # 如果启用模拟模式或planner模块不可用，使用模拟数据
    if ENABLE_SIMULATION_MODE or not MODULES["planner"]:
        return SIMULATION_RESPONSES["list_tasks"]()
    
    try:
        all_tasks = planner.list_tasks()
        tasks_json = []
        for task in all_tasks:
            task_data = {
                "id": task.task_id,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assigned_to": task.assigned_to
            }
            tasks_json.append(task_data)
        return json.dumps(tasks_json, ensure_ascii=False)
    except Exception as e:
        logger.error(f"列出任务时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.TASK_MANAGEMENT, 
                severity=ErrorSeverity.MEDIUM
            )
        # 出错时返回模拟数据
        return SIMULATION_RESPONSES["list_tasks"]()

# LLM调用工具
@mcp.tool()
async def call_llm(prompt: str, provider: str = "openai", model: Optional[str] = None) -> str:
    """调用LLM模型
    
    Args:
        prompt: 提示词
        provider: 提供商 (openai, anthropic, deepseek, siliconflow, local)
        model: 模型名称（可选）
    """
    logger.info(f"调用LLM: 提供商={provider}, 模型={model}")
    
    # 如果启用模拟模式，直接使用模拟数据
    if ENABLE_SIMULATION_MODE:
        logger.info("使用模拟模式响应LLM请求")
        return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
    
    # 如果LLM API模块不可用，使用模拟数据
    if not MODULES["llm_api"]:
        logger.warning("LLM API模块不可用，使用模拟数据")
        return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
    
    try:
        # 尝试导入并使用LLM API
        try:
            from tools.llm_api import create_llm_client, query_llm
            
            # 如果指定使用mock提供商，直接返回模拟响应
            if provider.lower() == "mock":
                logger.info("使用mock提供商，返回模拟响应")
                return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
                
            # 创建客户端并查询LLM
            client = create_llm_client(provider)
            response = query_llm(prompt, client=client, provider=provider, model=model)
            if response and hasattr(response, "content"):
                return response.content
            else:
                logger.warning(f"LLM响应格式异常: {response}")
                raise ValueError("LLM响应格式异常")
        except ImportError as e:
            logger.error(f"导入LLM模块失败: {e}")
            return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
        except Exception as e:
            logger.error(f"调用LLM客户端时出错: {e}")
            # 使用模拟响应作为备选
            return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
    except Exception as e:
        logger.error(f"调用LLM时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.LLM_API, 
                severity=ErrorSeverity.MEDIUM,
                context={"provider": provider, "model": model}
            )
        # 出错时返回模拟数据
        return SIMULATION_RESPONSES["call_llm"](prompt, provider, model)

# 流式LLM调用工具
@mcp.tool()
async def stream_llm(prompt: str, provider: str = "openai", model: Optional[str] = None) -> str:
    """以流式方式调用LLM模型（注意：返回字符串'stream'表示需要使用流式API）
    
    Args:
        prompt: 提示词
        provider: 提供商 (openai, anthropic, deepseek, siliconflow, local)
        model: 模型名称（可选）
    """
    logger.info(f"MCP流式调用LLM: 提供商={provider}, 模型={model}")
    return "stream"  # 返回特殊值，表示这是一个流式调用，MCP应该使用流式API

# 流式LLM调用函数 (用于HTTP和WebSocket API)
async def call_llm_stream(prompt: str, provider: str = "openai", model: Optional[str] = None) -> AsyncGenerator[str, None]:
    """以流式方式调用LLM模型
    
    Args:
        prompt: 提示词
        provider: 提供商 (openai, anthropic, deepseek, siliconflow, local)
        model: 模型名称（可选）
    
    Yields:
        LLM模型生成的文本片段
    """
    logger.info(f"流式调用LLM: 提供商={provider}, 模型={model}")
    
    if ENABLE_SIMULATION_MODE or not MODULES["llm_api"]:
        # 模拟流式响应
        await asyncio.sleep(0.5)
        
        # 获取模拟响应
        content = SIMULATION_RESPONSES["call_llm"](prompt, provider, model)
        
        # 分段返回内容
        parts = content.split("\n\n")
        for part in parts:
            if part:
                await asyncio.sleep(0.3)
                yield part + "\n\n"
        return
    
    try:
        client = create_llm_client(provider)
        stream = query_llm(prompt, client=client, provider=provider, model=model, stream=True)
        
        # 根据不同提供商处理流式响应
        if provider == "openai":
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        elif provider == "anthropic":
            async for chunk in stream:
                if chunk.delta.text:
                    yield chunk.delta.text
        else:
            # 通用流式响应处理
            async for chunk in stream:
                if hasattr(chunk, 'content'):
                    yield chunk.content
                elif hasattr(chunk, 'text'):
                    yield chunk.text
                elif isinstance(chunk, str):
                    yield chunk
                elif isinstance(chunk, dict) and 'content' in chunk:
                    yield chunk['content']
                else:
                    # 尝试转换为字符串
                    try:
                        yield str(chunk)
                    except:
                        pass
    except Exception as e:
        logger.error(f"流式调用LLM时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.LLM_API, 
                severity=ErrorSeverity.MEDIUM,
                context={"provider": provider, "model": model, "stream": True}
            )
        yield f"调用LLM时出错: {str(e)}"

# 工具调用
@mcp.tool()
async def analyze_task(task_description: str) -> str:
    """使用强化LLM分析任务并生成子任务
    
    Args:
        task_description: 任务描述
    """
    logger.info(f"分析任务: {task_description}")
    
    if not (MODULES["planner"] and hasattr(planner, '_analyze_task')):
        return json.dumps({
            "title": "任务分析",
            "description": task_description,
            "subtasks": [
                {"id": "1", "description": "子任务1: 研究问题域", "dependencies": []},
                {"id": "2", "description": "子任务2: 设计解决方案", "dependencies": ["1"]},
                {"id": "3", "description": "子任务3: 实现核心功能", "dependencies": ["1", "2"]},
                {"id": "4", "description": "子任务4: 测试和验证", "dependencies": ["3"]},
                {"id": "5", "description": "子任务5: 部署和监控", "dependencies": ["3", "4"]}
            ]
        }, ensure_ascii=False)
    
    try:
        # 使用实际的任务分析功能
        result = planner._analyze_task(task_description)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"分析任务时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.TASK_ANALYSIS, 
                severity=ErrorSeverity.MEDIUM,
                context={"task_description": task_description}
            )
        # 出错时也返回模拟的任务分解，以维持API一致性
        return json.dumps({
            "title": "任务分析（出错后的模拟）",
            "description": task_description,
            "subtasks": [
                {"id": "1", "description": "子任务1: 研究问题域", "dependencies": []},
                {"id": "2", "description": "子任务2: 设计解决方案", "dependencies": ["1"]}
            ]
        }, ensure_ascii=False)

# 健康检查工具
@mcp.tool()
async def check_health() -> str:
    """检查系统健康状态"""
    logger.info("检查系统健康状态")
    
    health = {
        "status": "healthy",
        "components": {
            "memory_manager": "online" if MODULES["memory_manager"] else "offline",
            "memory_index": "online" if MODULES["memory_index"] else "offline",
            "memory_sync": "online" if MODULES["memory_sync"] else "offline",
            "llm_api": "online" if MODULES["llm_api"] else "offline",
            "planner": "online" if MODULES["planner"] and planner and hasattr(planner, "is_running") and planner.is_running() else "offline",
            "executor": "online" if MODULES["executor"] and executor and hasattr(executor, "is_running") and executor.is_running() else "offline",
            "error_handler": "online" if MODULES["error_handler"] else "offline"
        },
        "version": "1.0.0",
        "modules_available": MODULES
    }
    
    # 检查是否所有组件都在线
    if "offline" in health["components"].values():
        health["status"] = "degraded"
    
    return json.dumps(health, indent=2)

# HTTP API路由（如果FastAPI可用）
if app:
    @app.get("/")
    async def root():
        """获取API根路径信息"""
        return {
            "name": "多智能体MCP服务",
            "version": "1.0.0",
            "status": "运行中",
            "documentation": "/docs",
            "protocols": ["http", "ws", "sse", "streamableHttp"]
        }
    
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        health_result = await check_health()
        return json.loads(health_result)
    
    @app.post("/tools/{tool_name}")
    async def call_tool(tool_name: str, request: Request):
        """调用工具端点
        
        Args:
            tool_name: 要调用的工具名称
            request: HTTP请求，包含工具参数
        """
        # 检查工具是否存在
        if not hasattr(sys.modules[__name__], tool_name):
            raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
        
        # 获取工具函数
        tool_func = getattr(sys.modules[__name__], tool_name)
        
        # 获取请求参数
        try:
            # 读取请求体并确保正确处理UTF-8编码
            body = await request.body()
            text = body.decode('utf-8')
            params = json.loads(text)
            logger.debug(f"接收到工具 {tool_name} 的调用参数: {params}")
        except json.JSONDecodeError as e:
            logger.error(f"无法解析请求体为JSON: {e}")
            raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode解码错误: {e}")
            raise HTTPException(status_code=400, detail=f"编码错误: {str(e)}")
        
        try:
            # 调用工具
            result = await tool_func(**params)
            # 设置响应headers确保UTF-8编码
            headers = {"Content-Type": "application/json; charset=utf-8"}
            return Response(
                content=result.encode('utf-8') if isinstance(result, str) else result, 
                media_type="application/json" if tool_name == "check_health" else "text/plain", 
                headers=headers
            )
        except Exception as e:
            logger.error(f"通过HTTP API调用工具 {tool_name} 时出错: {e}")
            logger.error(traceback.format_exc())
            if error_handler:
                error_handler.handle_error(
                    e, 
                    category=ErrorCategory.API, 
                    severity=ErrorSeverity.MEDIUM,
                    context={"tool_name": tool_name, "params": params}
                )
            raise HTTPException(status_code=500, detail=f"工具调用失败: {str(e)}")
    
    @app.get("/tools")
    async def list_tools():
        """列出所有可用的工具"""
        try:
            # 简化方法，直接列出所有支持的工具API端点
            tools = [
                {
                    "name": "read_memory",
                    "description": "读取记忆银行中的文件",
                    "parameters": [
                        {"name": "file_path", "type": "str", "required": True}
                    ],
                    "endpoint": "/tools/read_memory"
                },
                {
                    "name": "update_memory",
                    "description": "更新记忆银行中的文件",
                    "parameters": [
                        {"name": "file_path", "type": "str", "required": True},
                        {"name": "content", "type": "str", "required": True}
                    ],
                    "endpoint": "/tools/update_memory"
                },
                {
                    "name": "list_memory_files",
                    "description": "列出记忆银行中的所有文件",
                    "parameters": [],
                    "endpoint": "/tools/list_memory_files"
                },
                {
                    "name": "search_memory",
                    "description": "在记忆银行中搜索内容",
                    "parameters": [
                        {"name": "query", "type": "str", "required": True},
                        {"name": "top_k", "type": "int", "required": False}
                    ],
                    "endpoint": "/tools/search_memory"
                },
                {
                    "name": "create_task",
                    "description": "创建新任务",
                    "parameters": [
                        {"name": "description", "type": "str", "required": True},
                        {"name": "priority", "type": "str", "required": False}
                    ],
                    "endpoint": "/tools/create_task"
                },
                {
                    "name": "get_task_status",
                    "description": "获取任务状态",
                    "parameters": [
                        {"name": "task_id", "type": "str", "required": True}
                    ],
                    "endpoint": "/tools/get_task_status"
                },
                {
                    "name": "list_tasks",
                    "description": "列出所有任务",
                    "parameters": [],
                    "endpoint": "/tools/list_tasks"
                },
                {
                    "name": "call_llm",
                    "description": "调用大语言模型",
                    "parameters": [
                        {"name": "prompt", "type": "str", "required": True},
                        {"name": "provider", "type": "str", "required": False},
                        {"name": "model", "type": "str", "required": False}
                    ],
                    "endpoint": "/tools/call_llm"
                },
                {
                    "name": "check_health",
                    "description": "检查系统健康状态",
                    "parameters": [],
                    "endpoint": "/tools/check_health"
                }
            ]
            
            return {
                "status": "success",
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            logger.error(f"列出工具时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"内部服务器错误: {str(e)}"}
            )
    
    @app.post("/stream/llm")
    async def stream_llm(request: Request):
        """流式调用LLM API端点
        
        Args:
            request: HTTP请求，包含LLM调用参数
        
        Returns:
            流式HTTP响应，返回LLM生成的文本片段
        """
        try:
            # 读取并解码请求体
            body = await request.body()
            params = json.loads(body.decode('utf-8'))
            logger.debug(f"接收到流式LLM请求参数: {params}")
            
            prompt = params.get("prompt")
            provider = params.get("provider", "openai")
            model = params.get("model")
            
            if not prompt:
                raise HTTPException(status_code=400, detail="缺少prompt参数")
            
            async def generate():
                async for chunk in call_llm_stream(prompt, provider, model):
                    yield chunk.encode('utf-8')
            
            # 设置响应头确保UTF-8编码
            headers = {"Content-Type": "text/plain; charset=utf-8"}
            return StreamingResponse(generate(), media_type="text/plain", headers=headers)
        except json.JSONDecodeError as e:
            logger.error(f"无法解析请求体为JSON: {e}")
            raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode解码错误: {e}")
            raise HTTPException(status_code=400, detail=f"编码错误: {str(e)}")
        except Exception as e:
            logger.error(f"处理流式LLM请求时出错: {e}")
            raise HTTPException(status_code=500, detail=f"流式调用失败: {str(e)}")
    
    @app.post("/sse/llm")
    async def sse_llm(request: Request):
        """使用SSE流式调用LLM API端点
        
        Args:
            request: HTTP请求，包含LLM调用参数
        
        Returns:
            SSE响应，事件流形式返回LLM生成的文本片段
        """
        try:
            # 读取并解码请求体
            body = await request.body()
            params = json.loads(body.decode('utf-8'))
            logger.debug(f"接收到SSE LLM请求参数: {params}")
            
            prompt = params.get("prompt")
            provider = params.get("provider", "openai")
            model = params.get("model")
            
            if not prompt:
                raise HTTPException(status_code=400, detail="缺少prompt参数")
            
            async def generate():
                async for chunk in call_llm_stream(prompt, provider, model):
                    if chunk:
                        yield {"data": chunk}
            
            # 配置EventSourceResponse确保UTF-8编码
            return EventSourceResponse(generate(), encoding='utf-8')
        except json.JSONDecodeError as e:
            logger.error(f"无法解析请求体为JSON: {e}")
            raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode解码错误: {e}")
            raise HTTPException(status_code=400, detail=f"编码错误: {str(e)}")
        except Exception as e:
            logger.error(f"处理SSE LLM请求时出错: {e}")
            raise HTTPException(status_code=500, detail=f"SSE调用失败: {str(e)}")
    
    @app.websocket("/ws/llm")
    async def websocket_llm(websocket):
        """WebSocket端点，用于流式调用LLM
        
        Args:
            websocket: WebSocket连接
        """
        await websocket.accept()
        
        try:
            while True:
                # 接收消息并确保正确解码
                data_raw = await websocket.receive_text()
                try:
                    data = json.loads(data_raw)
                    logger.debug(f"接收到WebSocket请求: {data}")
                except json.JSONDecodeError as e:
                    logger.error(f"无法解析WebSocket消息为JSON: {e}")
                    await websocket.send_json({"error": f"无效的JSON格式: {str(e)}"})
                    continue
                
                prompt = data.get("prompt")
                provider = data.get("provider", "openai")
                model = data.get("model")
                
                if not prompt:
                    await websocket.send_json({"error": "缺少prompt参数"})
                    continue
                
                # 流式生成响应，确保使用UTF-8编码
                async for chunk in call_llm_stream(prompt, provider, model):
                    if chunk:
                        await websocket.send_text(chunk)
                
                # 发送完成标记
                await websocket.send_json({"event": "completion"})
        
        except WebSocketDisconnect:
            logger.info("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"WebSocket处理时出错: {e}")
            logger.error(traceback.format_exc())
            try:
                await websocket.close(code=1000, reason=str(e))
            except:
                pass

    @app.get("/api/endpoints")
    async def list_endpoints():
        """列出所有可用的API端点"""
        endpoints = []
        
        # 获取所有路由
        for route in app.routes:
            endpoint = {
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods) if hasattr(route, "methods") and route.methods else None,
            }
            endpoints.append(endpoint)
        
        return {
            "status": "success",
            "endpoints": endpoints,
            "count": len(endpoints)
        }

# 主函数
def main(host="127.0.0.1", port=8000, http_only=False, simulation=False, protocol="all"):
    """主函数
    
    Args:
        host: 监听主机地址
        port: 监听端口
        http_only: 是否仅使用HTTP协议
        simulation: 是否启用模拟模式
        protocol: 协议类型 (all, http, ws, sse, simple)
    """
    global ENABLE_SIMULATION_MODE
    # 强制禁用模拟模式，确保使用真实组件
    ENABLE_SIMULATION_MODE = False
    logger.info("强制禁用模拟模式，使用实际组件")
    
    # 根据命令行参数设置模拟模式
    if simulation:
        ENABLE_SIMULATION_MODE = True
        logger.info("已启用模拟模式")
    else:
        ENABLE_SIMULATION_MODE = os.environ.get("ENABLE_SIMULATION_MODE", "").lower() in ("true", "1", "yes")
        if ENABLE_SIMULATION_MODE:
            logger.info("已通过环境变量启用模拟模式")
        else:
            logger.info("模拟模式已禁用")
    
    # 初始化组件
    load_env_vars()
    init_components()
    
    try:
        # 注册信号处理器，用于优雅退出
        def signal_handler(sig, frame):
            logger.info("接收到退出信号，正在关闭服务...")
            if planner:
                planner.stop()
            if executor:
                executor.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 根据指定的协议启动服务
        if not app or protocol == "simple":
            # 如果没有FastAPI或者指定使用SimpleHTTPServer，则使用SimpleHTTPServer
            try:
                logger.info("使用SimpleHTTPServer实现的API服务器...")
                
                # 导入需要的模块
                try:
                    # Python 3
                    from http.server import HTTPServer, BaseHTTPRequestHandler
                    import urllib.parse as urlparse
                    import urllib.parse as parse
                except ImportError:
                    # Python 2
                    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
                    import urlparse
                    import urllib as parse
                
                # 定义请求处理器
                class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
                    def _set_response(self, status_code=200, content_type="application/json"):
                        self.send_response(status_code)
                        self.send_header("Content-Type", content_type)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                        self.send_header("Access-Control-Allow-Headers", "Content-Type")
                        self.end_headers()
                    
                    def do_OPTIONS(self):
                        self._set_response()
                    
                    def do_GET(self):
                        url_parts = urlparse.urlparse(self.path)
                        path = url_parts.path
                        
                        if path == "/health":
                            # 健康检查
                            self._set_response()
                            health_result = asyncio.run(check_health())
                            self.wfile.write(health_result.encode())
                        elif path == "/":
                            # 根路径信息
                            self._set_response()
                            info = {
                                "name": "多智能体MCP服务",
                                "version": "1.0.0",
                                "status": "运行中",
                                "protocols": ["http"]
                            }
                            self.wfile.write(json.dumps(info).encode())
                        elif path == "/tools":
                            # 列出工具
                            self._set_response()
                            tools = []
                            for name, func in globals().items():
                                if callable(func) and hasattr(func, "__annotations__") and name not in ("app", "init_components", "main"):
                                    # 提取函数文档字符串
                                    doc = func.__doc__ or ""
                                    
                                    # 提取参数
                                    params = {}
                                    for param_name, param_type in func.__annotations__.items():
                                        if param_name != "return":
                                            params[param_name] = {
                                                "type": str(param_type),
                                                "required": param_name not in getattr(func, "__defaults__", []) if hasattr(func, "__defaults__") else True
                                            }
                                    
                                    tools.append({
                                        "name": name,
                                        "description": doc.strip(),
                                        "parameters": params
                                    })
                            
                            self.wfile.write(json.dumps({"tools": tools}).encode())
                        else:
                            # 未知路径
                            self._set_response(404)
                            self.wfile.write(json.dumps({"error": "未找到"}).encode())
                    
                    def do_POST(self):
                        url_parts = urlparse.urlparse(self.path)
                        path = url_parts.path
                        
                        # 读取请求数据
                        content_length = int(self.headers.get("Content-Length", 0))
                        post_data = self.rfile.read(content_length).decode("utf-8")
                        
                        try:
                            params = json.loads(post_data) if post_data else {}
                        except json.JSONDecodeError:
                            self._set_response(400)
                            self.wfile.write(json.dumps({"error": "无效的JSON数据"}).encode())
                            return
                        
                        if path.startswith("/tools/"):
                            # 调用工具
                            tool_name = path.split("/")[-1]
                            
                            if hasattr(sys.modules[__name__], tool_name):
                                tool_func = getattr(sys.modules[__name__], tool_name)
                                
                                try:
                                    result = asyncio.run(tool_func(**params))
                                    self._set_response()
                                    self.wfile.write(result.encode())
                                except Exception as e:
                                    logger.error(f"调用工具 {tool_name} 时出错: {e}")
                                    logger.error(traceback.format_exc())
                                    self._set_response(500)
                                    self.wfile.write(json.dumps({"error": f"工具调用失败: {str(e)}"}).encode())
                            else:
                                self._set_response(404)
                                self.wfile.write(json.dumps({"error": f"工具 '{tool_name}' 不存在"}).encode())
                        else:
                            self._set_response(404)
                            self.wfile.write(json.dumps({"error": "未找到"}).encode())
                
                # 启动HTTP服务器
                server = HTTPServer((host, port), SimpleHTTPRequestHandler)
                logger.info(f"启动SimpleHTTPServer API服务器，监听: {host}:{port}...")
                server.serve_forever()
            
            except KeyboardInterrupt:
                logger.info("接收到用户中断，正在关闭服务...")
                if planner:
                    planner.stop()
                if executor:
                    executor.stop()
                sys.exit(0)
            except Exception as e:
                logger.error(f"启动SimpleHTTPServer时出错: {e}")
                logger.error(traceback.format_exc())
                
                # 回退到命令行接口
                logger.info("回退到命令行接口...")
                while True:
                    try:
                        cmd = input("MCP> ")
                        if cmd.lower() in ["exit", "quit", "q"]:
                            break
                        
                        parts = cmd.split(" ", 1)
                        if len(parts) == 1:
                            tool_name = parts[0]
                            args_str = "{}"
                        else:
                            tool_name = parts[0]
                            args_str = parts[1]
                        
                        if hasattr(sys.modules[__name__], tool_name):
                            tool_func = getattr(sys.modules[__name__], tool_name)
                            try:
                                args = json.loads(args_str)
                                result = asyncio.run(tool_func(**args))
                                print(result)
                            except json.JSONDecodeError:
                                print(f"错误: 参数必须是有效的JSON格式")
                            except Exception as e:
                                print(f"错误: {e}")
                        else:
                            print(f"未知工具: {tool_name}")
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print(f"错误: {e}")
        else:
            # 启动HTTP和WebSocket服务
            if not http_only:
                # 启动MCP服务器（在单独线程中）
                logger.info("启动MCP服务器...")
                mcp_thread = threading.Thread(target=mcp.run)
                mcp_thread.daemon = True
                mcp_thread.start()
            
            # 启动FastAPI服务器
            logger.info(f"启动HTTP API服务器，监听: {host}:{port}...")
            try:
                uvicorn.run(app, host=host, port=port)
            except Exception as e:
                logger.error(f"启动HTTP API服务器时出错: {e}")
                logger.error(traceback.format_exc())
                if error_handler:
                    error_handler.handle_error(
                        e, 
                        category=ErrorCategory.SERVER if MODULES["error_handler"] else "SERVER", 
                        severity=ErrorSeverity.HIGH if MODULES["error_handler"] else "HIGH", 
                        context={"host": host, "port": port}
                    )
    except Exception as e:
        logger.error(f"运行主函数时出错: {e}")
        logger.error(traceback.format_exc())
        if error_handler:
            error_handler.handle_error(
                e, 
                category=ErrorCategory.APPLICATION if MODULES["error_handler"] else "APPLICATION", 
                severity=ErrorSeverity.CRITICAL if MODULES["error_handler"] else "CRITICAL", 
                context={"component": "main"}
            )
        sys.exit(1)

if __name__ == "__main__":
    # 使用命令行参数启动服务器
    parser = argparse.ArgumentParser(description="多智能体MCP服务器")
    parser.add_argument("--host", default="127.0.0.1", help="监听主机地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--http-only", action="store_true", help="只启动HTTP API，不启动MCP服务")
    parser.add_argument("--simulation", action="store_true", help="启用模拟模式")
    parser.add_argument("--protocol", default="all", choices=["all", "http", "ws", "sse", "simple"], 
                      help="指定启动的协议，simple表示使用SimpleHTTPServer")
    args = parser.parse_args()
    
    main(
        host=args.host,
        port=args.port,
        http_only=args.http_only,
        simulation=args.simulation,
        protocol=args.protocol
    )