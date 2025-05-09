"""
模拟数据模块

提供各种工具和API调用的模拟响应，在真实服务不可用时提供基本功能支持。
包括LLM、记忆银行、任务管理等功能的模拟响应。
"""

import os
import json
import random
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

# 配置日志
logger = logging.getLogger("simulation")

# 示例记忆文件内容
SAMPLE_MEMORY_CONTENT = {
    "activeContext.md": """# 活动上下文

这是一个示例文档，用于演示记忆银行功能。

## 当前工作焦点
- 增强错误处理系统
- 实现跨平台兼容性
- 优化LLM API调用

## 最近变更
- 添加了错误分类和严重度评估
- 实现了指数退避重试机制
- 添加了模拟模式支持

## 下一步计划
- 完善跨平台测试
- 增强WebSocket通信可靠性
- 优化记忆管理系统
""",
    "projectbrief.md": """# 项目简介

增强型多智能体协作框架是一个基于Planner-Executor模式的智能体系统，
旨在提供高效的任务规划和执行能力。

## 核心目标
- 实现可靠的多智能体协作
- 提供持久化的记忆管理
- 支持复杂任务的分解和执行
- 实现跨平台兼容性

## 主要功能
- 记忆银行：持久化存储系统知识
- 任务规划：分析和分解复杂任务
- LLM集成：支持多种LLM提供商
- 错误处理：全面的错误恢复机制
""",
    "progress.md": """# 项目进度

## 已完成功能
- [x] 基础服务器框架
- [x] 记忆银行核心功能
- [x] LLM API集成
- [x] 错误处理框架
- [x] WebSocket通信

## 进行中的工作
- [ ] 跨平台兼容性优化
- [ ] 任务规划算法增强
- [ ] 高级错误恢复机制
- [ ] 性能监控系统

## 已知问题
- 某些复杂环境下的API调用不稳定
- Windows平台上的路径处理有细微差异
- 需要增强对断网情况的处理
""",
    "systemPatterns.md": """# 系统模式

## 架构概览
该系统采用模块化架构，围绕核心服务器构建，集成多个功能模块。

## 核心组件
- **MCP服务器**：中央协调器，管理所有通信和服务
- **记忆管理系统**：持久化存储和检索系统知识
- **任务规划器**：分析需求，分解任务，制定执行计划
- **执行器**：执行具体任务，提供结果反馈
- **通信层**：管理组件间通信，提供多种协议支持

## 设计模式
- **Planner-Executor模式**：将规划和执行分离，提高效率
- **装饰器模式**：用于错误处理和日志记录
- **适配器模式**：统一不同LLM提供商的接口
- **工厂模式**：创建不同类型的客户端和服务
- **观察者模式**：实现组件间的事件通知
""",
    "techContext.md": """# 技术上下文

## 技术栈
- Python 3.8+
- FastAPI
- WebSockets
- 多种LLM API (OpenAI, Anthropic, DeepSeek等)

## 开发环境
- 支持Windows、macOS和Linux
- 使用Python虚拟环境管理依赖
- 使用.env文件管理环境变量和密钥

## 依赖关系
- fastmcp: 核心MCP框架
- requests: HTTP请求
- websockets: WebSocket通信
- python-dotenv: 环境变量管理
- psutil: 系统资源监控
- loguru: 高级日志记录

## 关键配置
- MCP服务器默认端口: 8080
- WebSocket服务默认路径: /ws
- 支持HTTP和stdio通信
- 记忆银行默认存储在项目根目录下的memory-bank文件夹
"""
}

# 任务示例
SAMPLE_TASKS = [
    {
        "id": "task-001",
        "title": "实现错误处理系统",
        "description": "开发一个全面的错误处理系统，支持错误分类、日志记录和自动恢复",
        "status": "completed",
        "created_at": "2023-10-01T10:00:00Z",
        "completed_at": "2023-10-05T15:30:00Z",
        "subtasks": [
            {"id": "subtask-001-1", "title": "设计错误分类系统", "status": "completed"},
            {"id": "subtask-001-2", "title": "实现日志记录功能", "status": "completed"},
            {"id": "subtask-001-3", "title": "开发自动恢复机制", "status": "completed"}
        ]
    },
    {
        "id": "task-002",
        "title": "优化LLM API调用",
        "description": "提高LLM API调用的可靠性和效率，支持多种提供商和模型",
        "status": "in_progress",
        "created_at": "2023-10-06T09:00:00Z",
        "completed_at": None,
        "subtasks": [
            {"id": "subtask-002-1", "title": "实现统一的API接口", "status": "completed"},
            {"id": "subtask-002-2", "title": "添加缓存机制", "status": "in_progress"},
            {"id": "subtask-002-3", "title": "实现并发请求控制", "status": "not_started"}
        ]
    },
    {
        "id": "task-003",
        "title": "跨平台兼容性测试",
        "description": "确保系统在Windows、macOS和Linux平台上均能正常运行",
        "status": "not_started",
        "created_at": "2023-10-07T14:00:00Z",
        "completed_at": None,
        "subtasks": [
            {"id": "subtask-003-1", "title": "Windows平台测试", "status": "not_started"},
            {"id": "subtask-003-2", "title": "macOS平台测试", "status": "not_started"},
            {"id": "subtask-003-3", "title": "Linux平台测试", "status": "not_started"}
        ]
    }
]

# 模拟LLM响应生成器
def generate_llm_response(prompt: str, provider: str = "mock", model: Optional[str] = None) -> str:
    """
    生成模拟的LLM响应
    
    Args:
        prompt: 提示词
        provider: 模拟的提供商
        model: 模拟的模型名称
        
    Returns:
        模拟的LLM响应
    """
    # 记录请求
    logger.info(f"模拟LLM请求: 提供商={provider}, 模型={model}, 提示词长度={len(prompt)}")
    
    # 根据提示词内容生成不同的响应
    if "天气" in prompt or "weather" in prompt.lower():
        return "今天天气晴朗，温度适宜，是个出行的好日子。"
    
    if "你是谁" in prompt or "who are you" in prompt.lower():
        return "我是一个模拟的LLM响应，由多智能体协作框架的模拟数据模块生成。"
    
    if "错误处理" in prompt or "error handling" in prompt.lower():
        return """错误处理是软件开发中的重要环节，良好的错误处理机制可以提高系统的稳定性和用户体验。
        
主要包括以下方面：
1. 错误分类：将错误按类型和严重程度分类
2. 错误日志：记录详细的错误信息，便于诊断
3. 错误恢复：尝试从错误中恢复，如重试操作
4. 用户反馈：向用户提供友好的错误提示
        
在Python中，可以使用try-except语句进行错误处理，通过捕获异常并进行相应处理，避免程序崩溃。"""
    
    if "任务规划" in prompt or "task planning" in prompt.lower():
        return """任务规划是将复杂任务分解为更小、更易管理的子任务的过程。有效的任务规划可以提高工作效率，降低复杂度。
        
任务规划的步骤包括：
1. 明确目标：清晰定义任务的最终目标
2. 任务分解：将复杂任务分解为子任务
3. 依赖分析：识别任务间的依赖关系
4. 资源分配：分配时间和资源给各个子任务
5. 进度跟踪：监控执行情况，及时调整计划
        
在项目管理中，可以使用各种工具如甘特图、PERT图等辅助任务规划。"""
    
    if "跨平台" in prompt or "cross platform" in prompt.lower():
        return """跨平台开发指的是创建能够在多种操作系统或环境中运行的应用程序。在开发跨平台应用时需要考虑各平台的差异。
        
主要挑战包括：
1. 文件路径表示不同（Windows使用反斜杠，Unix使用正斜杠）
2. 环境变量和系统调用的差异
3. 文件权限模型的不同
4. 换行符的差异（Windows: CRLF, Unix: LF）
5. 默认字符编码的不同
        
Python是一种优秀的跨平台语言，可以通过标准库模块如os、pathlib等处理平台差异，编写可移植代码。"""
    
    # 支持简单问答
    simple_qa = {
        "什么是人工智能": "人工智能是指由人制造出来的机器所表现出的智能，通常通过计算机程序实现。它可以模拟、延伸和扩展人的智能，感知环境、获取知识并使用知识达成特定目标。",
        "什么是机器学习": "机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习和改进，而无需显式编程。它使用算法来识别数据中的模式，并做出数据驱动的预测或决策。",
        "什么是深度学习": "深度学习是机器学习的一个子领域，它使用多层神经网络来模拟人脑的工作方式。这些神经网络能够从大量数据中学习复杂的模式，常用于图像识别、自然语言处理等领域。",
        "什么是自然语言处理": "自然语言处理(NLP)是人工智能的一个分支，专注于使计算机能够理解、解释和生成人类语言。它结合了计算语言学、机器学习和深度学习技术，应用于机器翻译、情感分析、问答系统等。"
    }
    
    for question, answer in simple_qa.items():
        if question in prompt:
            return answer
    
    # 常见的任务操作
    task_operations = {
        "创建任务": "已成功创建新任务，ID为task-004，标题为'开发新功能'。",
        "列出任务": "当前有3个任务：\n1. 实现错误处理系统 (已完成)\n2. 优化LLM API调用 (进行中)\n3. 跨平台兼容性测试 (未开始)",
        "更新任务": "已成功更新任务状态。",
        "删除任务": "已成功删除指定任务。"
    }
    
    for operation, response in task_operations.items():
        if operation in prompt:
            return response
    
    # 默认返回一个通用回复
    default_responses = [
        "根据您的描述，我建议从基本需求分析开始，然后逐步进行设计和实现。可以考虑采用模块化设计，提高代码的可维护性。",
        "您提到的问题是一个常见的挑战。通常可以通过以下方法解决：首先确认问题的根源，然后针对性地应用解决方案，最后进行充分测试验证。",
        "这是一个有趣的话题。从技术角度看，需要考虑性能、安全性和扩展性等多个方面。建议先从小规模原型开始，再逐步扩展功能。",
        "您的问题涉及多个领域。建议将其分解为更小的子问题，分别解决后再整合结果。这样可以降低复杂度，提高解决效率。",
        "这个情况下，最佳实践是先进行全面的需求分析，明确系统的边界和核心功能，然后制定详细的实施计划，逐步推进。"
    ]
    
    # 稍作随机化，避免总是返回同一个回复
    return random.choice(default_responses)

# 模拟记忆银行读取响应
def simulate_read_memory(file_path: str) -> str:
    """
    模拟读取记忆文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        模拟的文件内容
    """
    logger.info(f"模拟读取记忆文件: {file_path}")
    
    # 从预定义的样本内容中获取
    file_name = os.path.basename(file_path)
    content = SAMPLE_MEMORY_CONTENT.get(file_name, f"# {file_name}\n\n这是一个示例文档，用于演示记忆银行功能。")
    
    return content

# 模拟记忆银行列表响应
def simulate_list_memory_files() -> List[str]:
    """
    模拟列出记忆文件
    
    Returns:
        模拟的文件列表
    """
    logger.info("模拟列出记忆文件")
    
    # 返回预定义的样本文件列表
    return list(SAMPLE_MEMORY_CONTENT.keys())

# 模拟记忆银行更新响应
def simulate_update_memory(file_path: str, content: str) -> str:
    """
    模拟更新记忆文件
    
    Args:
        file_path: 文件路径
        content: 新内容
        
    Returns:
        模拟的操作结果
    """
    logger.info(f"模拟更新记忆文件: {file_path}, 内容长度: {len(content)}")
    
    # 返回成功消息
    return f"已成功更新记忆文件: {os.path.basename(file_path)}，内容长度: {len(content)} 字符"

# 模拟记忆银行搜索响应
def simulate_search_memory(query: str) -> List[Dict[str, str]]:
    """
    模拟搜索记忆内容
    
    Args:
        query: 搜索查询
        
    Returns:
        模拟的搜索结果
    """
    logger.info(f"模拟搜索记忆内容: {query}")
    
    # 简单模拟搜索，返回包含查询词的文件和匹配行
    results = []
    for file_name, content in SAMPLE_MEMORY_CONTENT.items():
        if query.lower() in content.lower():
            # 找出包含查询词的行
            lines = content.split("\n")
            matches = [line for line in lines if query.lower() in line.lower()]
            
            if matches:
                results.append({
                    "file": file_name,
                    "matches": matches[:3],  # 最多返回3个匹配行
                    "score": 0.85  # 模拟的相似度分数
                })
    
    # 如果没有结果，返回一个通用结果
    if not results:
        random_file = random.choice(list(SAMPLE_MEMORY_CONTENT.keys()))
        results.append({
            "file": random_file,
            "matches": ["没有找到完全匹配的内容，这是一个近似结果。"],
            "score": 0.5
        })
    
    return results

# 模拟记忆银行文件创建响应
def simulate_create_memory_file(file_path: str, content: str) -> str:
    """
    模拟创建记忆文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        
    Returns:
        模拟的操作结果
    """
    logger.info(f"模拟创建记忆文件: {file_path}, 内容长度: {len(content)}")
    
    # 返回成功消息
    return f"已成功创建记忆文件: {os.path.basename(file_path)}，内容长度: {len(content)} 字符"

# 模拟任务管理响应
def simulate_create_task(title: str, description: str) -> Dict[str, Any]:
    """
    模拟创建任务
    
    Args:
        title: 任务标题
        description: 任务描述
        
    Returns:
        模拟的任务数据
    """
    logger.info(f"模拟创建任务: {title}")
    
    # 生成任务ID
    task_id = f"task-{str(random.randint(100, 999)).zfill(3)}"
    
    # 创建新任务
    new_task = {
        "id": task_id,
        "title": title,
        "description": description,
        "status": "not_started",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "subtasks": []
    }
    
    return new_task

# 模拟获取任务状态
def simulate_get_task_status(task_id: str) -> Dict[str, Any]:
    """
    模拟获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        模拟的任务状态数据
    """
    logger.info(f"模拟获取任务状态: {task_id}")
    
    # 查找匹配的任务
    for task in SAMPLE_TASKS:
        if task["id"] == task_id:
            return {
                "id": task["id"],
                "title": task["title"],
                "status": task["status"],
                "progress": _calculate_task_progress(task),
                "subtasks_count": len(task["subtasks"]),
                "completed_subtasks": sum(1 for st in task["subtasks"] if st["status"] == "completed")
            }
    
    # 如果找不到，返回一个模拟任务
    return {
        "id": task_id,
        "title": "模拟任务",
        "status": random.choice(["not_started", "in_progress", "completed"]),
        "progress": random.randint(0, 100),
        "subtasks_count": random.randint(2, 5),
        "completed_subtasks": random.randint(0, 3)
    }

# 计算任务进度
def _calculate_task_progress(task: Dict[str, Any]) -> int:
    """
    计算任务进度百分比
    
    Args:
        task: 任务数据
        
    Returns:
        进度百分比(0-100)
    """
    if not task["subtasks"]:
        if task["status"] == "completed":
            return 100
        elif task["status"] == "in_progress":
            return 50
        else:
            return 0
    
    completed = sum(1 for st in task["subtasks"] if st["status"] == "completed")
    in_progress = sum(1 for st in task["subtasks"] if st["status"] == "in_progress")
    
    total = len(task["subtasks"])
    progress = (completed + 0.5 * in_progress) / total * 100
    
    return int(progress)

# 模拟列出任务
def simulate_list_tasks() -> List[Dict[str, Any]]:
    """
    模拟列出所有任务
    
    Returns:
        模拟的任务列表
    """
    logger.info("模拟列出所有任务")
    
    # 返回任务列表的简化版本
    simplified_tasks = []
    for task in SAMPLE_TASKS:
        simplified_tasks.append({
            "id": task["id"],
            "title": task["title"],
            "status": task["status"],
            "progress": _calculate_task_progress(task),
            "created_at": task["created_at"]
        })
    
    return simplified_tasks

# 模拟分析任务
def simulate_analyze_task(description: str) -> Dict[str, Any]:
    """
    模拟分析任务并创建子任务
    
    Args:
        description: 任务描述
        
    Returns:
        模拟的任务分析结果
    """
    logger.info(f"模拟分析任务: {description}")
    
    # 根据描述中的关键词生成不同的子任务
    subtasks = []
    
    if "开发" in description or "实现" in description or "创建" in description:
        subtasks.extend([
            {"title": "需求分析", "description": "分析并明确功能需求"},
            {"title": "设计方案", "description": "设计技术实现方案"},
            {"title": "代码实现", "description": "编写代码实现功能"},
            {"title": "测试验证", "description": "进行单元测试和集成测试"}
        ])
    
    if "优化" in description or "改进" in description:
        subtasks.extend([
            {"title": "性能分析", "description": "分析当前性能瓶颈"},
            {"title": "优化方案", "description": "设计优化方案"},
            {"title": "实施优化", "description": "实施优化措施"},
            {"title": "效果验证", "description": "验证优化效果"}
        ])
    
    if "测试" in description or "验证" in description:
        subtasks.extend([
            {"title": "设计测试用例", "description": "设计全面的测试用例"},
            {"title": "执行单元测试", "description": "执行单元测试"},
            {"title": "执行集成测试", "description": "执行集成测试"},
            {"title": "测试报告", "description": "生成测试报告"}
        ])
    
    # 如果没有匹配到关键词，生成通用子任务
    if not subtasks:
        subtasks = [
            {"title": "需求分析", "description": "分析并明确需求"},
            {"title": "方案设计", "description": "设计实施方案"},
            {"title": "执行实施", "description": "执行实施计划"},
            {"title": "评估验证", "description": "评估验证结果"}
        ]
    
    # 限制子任务数量，避免太多
    if len(subtasks) > 5:
        subtasks = subtasks[:5]
    
    # 添加子任务ID
    for i, subtask in enumerate(subtasks):
        subtask["id"] = f"subtask-{str(random.randint(100, 999)).zfill(3)}-{i+1}"
        subtask["status"] = "not_started"
    
    # 生成任务分析结果
    result = {
        "original_description": description,
        "analysis": f"根据描述，这是一个{'开发' if '开发' in description else '优化' if '优化' in description else '一般'}类任务，建议分解为{len(subtasks)}个子任务。",
        "estimated_effort": f"{random.randint(2, 10)}人天",
        "subtasks": subtasks
    }
    
    return result

# 模拟系统健康检查
def simulate_system_health_check() -> Dict[str, Any]:
    """
    模拟系统健康检查
    
    Returns:
        模拟的健康状态数据
    """
    logger.info("模拟系统健康检查")
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "server": {
                "status": "running",
                "uptime": "3 days, 5 hours",
                "load": 0.35
            },
            "memory_bank": {
                "status": "running",
                "file_count": len(SAMPLE_MEMORY_CONTENT),
                "last_update": "2023-10-10T15:30:00Z"
            },
            "llm_api": {
                "status": "running",
                "providers": ["openai", "anthropic", "deepseek", "mock"],
                "last_call": "2023-10-10T16:45:00Z"
            }
        },
        "resources": {
            "cpu": {
                "usage": f"{random.randint(5, 30)}%",
                "cores": 8
            },
            "memory": {
                "total": "16GB",
                "used": f"{random.randint(20, 60)}%"
            },
            "disk": {
                "total": "500GB",
                "used": f"{random.randint(30, 70)}%"
            }
        },
        "errors": {
            "last_24h": random.randint(0, 5),
            "critical": 0,
            "high": random.randint(0, 2),
            "medium": random.randint(0, 3)
        }
    }

# 模拟响应函数集合
SIMULATION_RESPONSES = {
    "call_llm": generate_llm_response,
    "read_memory": simulate_read_memory,
    "list_memory_files": simulate_list_memory_files,
    "update_memory": simulate_update_memory,
    "search_memory": simulate_search_memory,
    "create_memory_file": simulate_create_memory_file,
    "create_task": simulate_create_task,
    "get_task_status": simulate_get_task_status,
    "list_tasks": simulate_list_tasks,
    "analyze_task": simulate_analyze_task,
    "system_health": simulate_system_health_check
}

# 修复Unicode显示问题
def fix_unicode_display(text: str) -> str:
    """
    修复Unicode编码显示问题，确保特殊字符正确显示
    
    Args:
        text: 原始文本
        
    Returns:
        修复后的文本
    """
    # 替换JSON中的Unicode转义序列
    if text:
        # 转换\uXXXX的Unicode转义序列
        text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)
        # 转换\xXX的十六进制转义序列
        text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), text)
    return text 