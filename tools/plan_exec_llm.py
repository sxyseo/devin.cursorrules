#!/usr/bin/env python3
"""
提供任务规划和执行相关的LLM功能

此模块用于调用大型语言模型，支持任务规划、任务分解、指令生成等功能。
支持多种LLM提供商，并提供统一的API接口。
"""

import os
import sys
import json
import logging
import time
import platform
from typing import Dict, List, Optional, Any, Union
import requests
from pathlib import Path
import argparse
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("planner_llm")

# 检查环境变量中的API密钥
def _check_api_keys():
    """检查和加载环境变量，并返回可用的API提供商"""
    # 首先加载环境变量
    # 优先级顺序：
    # 1. 系统环境变量（已加载）
    # 2. .env.local（用户特定覆盖）
    # 3. .env（项目默认值）
    # 4. .env.example（示例配置）
    
    env_files = ['.env.local', '.env', '.env.example']
    env_loaded = False
    
    logger.debug(f"当前工作目录: {Path('.').absolute()}")
    logger.debug(f"查找环境文件: {env_files}")
    
    for env_file in env_files:
        env_path = Path('.') / env_file
        logger.debug(f"检查 {env_path.absolute()}")
        if env_path.exists():
            logger.info(f"找到 {env_file}，加载变量...")
            load_dotenv(dotenv_path=env_path)
            env_loaded = True
            logger.info(f"从 {env_file} 加载环境变量")
            # 打印加载的键（出于安全原因不打印值）
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    keys = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
                    logger.debug(f"从 {env_file} 加载的键: {keys}")
            except Exception as e:
                logger.warning(f"读取 {env_file} 中的键时出错: {e}")
    
    if not env_loaded:
        logger.warning("未找到 .env 文件。仅使用系统环境变量。")
        logger.debug(f"可用的系统环境变量: {list(os.environ.keys())}")
        
    # 检查可用的API提供商
    providers = {
        "siliconflow": "SILICONFLOW_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY"
    }
    
    available = []
    for provider, env_var in providers.items():
        api_key = os.environ.get(env_var)
        if api_key:
            available.append(provider)
            logger.debug(f"找到{provider}的API密钥")
    
    if available:
        logger.info(f"可用的LLM提供商: {', '.join(available)}")
    else:
        logger.warning("没有找到有效的LLM API密钥，将使用模拟响应")
    
    return available

# 初始化可用的提供商
AVAILABLE_PROVIDERS = _check_api_keys()

# 环境变量常量
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://msopenai.openai.azure.com")
AZURE_OPENAI_MODEL_DEPLOYMENT = os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT", "gpt-4o-ms")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_API_URL = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:8006/v1")

def query_planner_llm(prompt: str, provider: str = "siliconflow", 
                     model: Optional[str] = None,
                     max_retries: int = 3,
                     timeout: int = 60) -> str:
    """调用大型语言模型进行任务规划
    
    Args:
        prompt: 提示词
        provider: LLM提供商 (siliconflow, openai, anthropic, deepseek, gemini, azure)
        model: 模型名称 (如果不指定，使用提供商的默认模型)
        max_retries: 最大重试次数
        timeout: 超时时间(秒)
    
    Returns:
        LLM的响应文本
    """
    # 验证提供商
    if provider not in ["siliconflow", "openai", "anthropic", "deepseek", "gemini", "azure", "mock"]:
        logger.warning(f"未知的LLM提供商: {provider}，使用模拟响应")
        provider = "mock"
    
    # 如果不是模拟模式但提供商不可用，回退到模拟模式
    if provider != "mock" and provider not in AVAILABLE_PROVIDERS:
        logger.warning(f"提供商 {provider} 不可用，使用模拟响应")
        provider = "mock"
    
    # 根据提供商选择处理函数
    provider_functions = {
        "siliconflow": _query_siliconflow,
        "openai": _query_openai,
        "anthropic": _query_anthropic,
        "deepseek": _query_deepseek,
        "gemini": _query_gemini,
        "azure": _query_azure,
        "mock": _mock_response
    }
    
    # 获取处理函数
    process_function = provider_functions.get(provider, _mock_response)
    
    # 重试机制
    retries = 0
    while retries < max_retries:
        try:
            return process_function(prompt, model, timeout)
        except Exception as e:
            retries += 1
            wait_time = 2 ** retries  # 指数退避
            logger.warning(f"调用LLM失败 ({retries}/{max_retries}): {e}")
            
            if retries < max_retries:
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"达到最大重试次数，返回模拟响应")
                return _mock_response(prompt, None, timeout)

def _query_siliconflow(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用SiliconFlow AI (DeepSeek-R1)
    
    Args:
        prompt: 提示词
        model: 模型名称，默认为deepseek-ai/DeepSeek-R1
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = SILICONFLOW_API_KEY
    if not api_key:
        logger.error("未找到SILICONFLOW_API_KEY")
        return _mock_response(prompt, model, timeout)
    
    model = model or "deepseek-ai/DeepSeek-R1"
    
    # SiliconFlow API URL
    url = f"{SILICONFLOW_API_URL}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.2
    }
    
    logger.info(f"正在调用SiliconFlow API, URL: {url}, 模型: {model}, 超时: {timeout}秒")
    logger.debug(f"请求数据: {payload}")
    
    try:
        # 设置更短的连接超时和读取超时
        start_time = time.time()
        response = requests.post(
            url, 
            headers=headers, 
            json=payload, 
            timeout=(10, timeout)  # (连接超时, 读取超时)
        )
        
        elapsed_time = time.time() - start_time
        logger.debug(f"请求耗时: {elapsed_time:.2f}秒")
        
        # 记录响应状态
        logger.debug(f"响应状态码: {response.status_code}")
        
        response.raise_for_status()
        result = response.json()
        
        logger.debug(f"响应数据: {result}")
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"SiliconFlow API调用成功，响应长度: {len(content)}字符")
        return content
    except requests.exceptions.Timeout:
        logger.error(f"SiliconFlow API调用超时 (超过{timeout}秒)")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"SiliconFlow API连接错误: {e}")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"SiliconFlow API HTTP错误: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"错误详情: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"SiliconFlow API调用失败: {e}")
        raise

def _query_openai(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用OpenAI API
    
    Args:
        prompt: 提示词
        model: 模型名称，默认为gpt-4o
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = OPENAI_API_KEY
    if not api_key:
        logger.error("未找到OPENAI_API_KEY")
        return _mock_response(prompt, model, timeout)
    
    model = model or "gpt-4o"
    
    try:
        import openai
        openai.api_key = api_key
        
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2,
            timeout=timeout
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API调用失败: {e}")
        raise

def _query_anthropic(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用Anthropic API
    
    Args:
        prompt: 提示词
        model: 模型名称，默认为claude-3-5-sonnet-20240620
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        logger.error("未找到ANTHROPIC_API_KEY")
        return _mock_response(prompt, model, timeout)
    
    model = model or "claude-3-5-sonnet-20240620"
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Anthropic API调用失败: {e}")
        raise

def _query_deepseek(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用DeepSeek API
    
    Args:
        prompt: 提示词
        model: 模型名称，默认为deepseek-chat
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        logger.error("未找到DEEPSEEK_API_KEY")
        return _mock_response(prompt, model, timeout)
    
    model = model or "deepseek-chat"
    
    # DeepSeek API URL
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.2
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"DeepSeek API调用失败: {e}")
        raise

def _query_gemini(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用Google Gemini API
    
    Args:
        prompt: 提示词
        model: 模型名称，默认为gemini-pro
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = GOOGLE_API_KEY
    if not api_key:
        logger.error("未找到GOOGLE_API_KEY")
        return _mock_response(prompt, model, timeout)
    
    model = model or "gemini-pro"
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model_obj = genai.GenerativeModel(model_name=model)
        response = model_obj.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API调用失败: {e}")
        raise

def _query_azure(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """调用Azure OpenAI API
    
    Args:
        prompt: 提示词
        model: 模型部署名称，默认从环境变量AZURE_OPENAI_MODEL_DEPLOYMENT获取
        timeout: 超时时间(秒)
    
    Returns:
        模型响应
    """
    api_key = AZURE_OPENAI_API_KEY
    api_base = AZURE_ENDPOINT
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    deployment = model or AZURE_OPENAI_MODEL_DEPLOYMENT
    
    if not api_key or not api_base:
        logger.error("未找到AZURE_OPENAI_API_KEY或AZURE_OPENAI_ENDPOINT")
        return _mock_response(prompt, model, timeout)
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base
        )
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2,
            timeout=timeout
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Azure OpenAI API调用失败: {e}")
        raise

def _mock_response(prompt: str, model: Optional[str] = None, timeout: int = 60) -> str:
    """生成模拟响应（当真实LLM不可用时）
    
    Args:
        prompt: 提示词
        model: 模型名称（未使用）
        timeout: 超时时间（未使用）
    
    Returns:
        模拟的LLM响应
    """
    logger.info("使用模拟响应")
    
    # 任务规划优化关键词
    planning_keywords = ["任务规划", "规划优化", "planning", "优化", "任务分解", "调度"]
    has_planning_keywords = any(kw in prompt.lower() for kw in planning_keywords)
    
    # 分析提示中的关键词，返回相应的模拟响应
    if has_planning_keywords and ("拆分" in prompt or "子任务" in prompt or "分解" in prompt):
        # 任务规划优化的分解响应
        return json.dumps([
            "任务规划算法设计与优化",
            "大型语言模型集成与调优",
            "智能任务分解模块实现",
            "依赖关系分析与关键路径优化",
            "任务规划性能测试与评估"
        ], ensure_ascii=False)
    
    elif "分解" in prompt and "子任务" in prompt:
        # 通用任务分解的模拟响应
        if "开发" in prompt.lower():
            return json.dumps([
                "需求分析和功能规划",
                "架构设计和技术选型",
                "核心功能实现",
                "测试和质量保证",
                "部署和监控配置"
            ], ensure_ascii=False)
        elif "测试" in prompt.lower():
            return json.dumps([
                "制定测试策略和计划",
                "设计测试用例",
                "搭建测试环境",
                "执行测试并记录结果",
                "分析问题并提交报告"
            ], ensure_ascii=False)
        else:
            return json.dumps([
                "需求收集和分析",
                "方案设计和资源准备",
                "执行主要工作",
                "验证和测试结果",
                "总结和文档记录"
            ], ensure_ascii=False)
    
    elif "指令" in prompt or "instruction" in prompt.lower():
        # 返回指令生成的模拟响应
        return """
        1. 确认任务范围和目标
        2. 准备必要的资源和环境
        3. 按照以下步骤执行任务:
           a. 首先分析需求
           b. 设计解决方案
           c. 实现核心功能
           d. 进行测试和验证
        4. 记录执行过程和结果
        5. 提交完成报告
        """
    
    elif "计划" in prompt or "调度" in prompt:
        # 返回计划生成的模拟响应
        return json.dumps({
            "tasks": [
                {"id": "task_1", "name": "需求分析", "duration": "2天", "dependencies": []},
                {"id": "task_2", "name": "设计方案", "duration": "3天", "dependencies": ["task_1"]},
                {"id": "task_3", "name": "实现核心功能", "duration": "5天", "dependencies": ["task_2"]},
                {"id": "task_4", "name": "测试和验证", "duration": "3天", "dependencies": ["task_3"]},
                {"id": "task_5", "name": "部署和文档", "duration": "2天", "dependencies": ["task_4"]}
            ],
            "estimated_completion_time": "15天",
            "critical_path": ["task_1", "task_2", "task_3", "task_4", "task_5"]
        }, ensure_ascii=False)
    
    else:
        # 通用响应
        return "收到您的请求，我已分析完成。请根据具体情况进行下一步操作。"

def main():
    parser = argparse.ArgumentParser(description='任务规划和分解LLM工具')
    parser.add_argument('--prompt', type=str, help='发送给LLM的提示词', required=True)
    parser.add_argument('--file', type=str, help='要包含在提示中的文件路径', required=False)
    parser.add_argument('--provider', choices=['siliconflow', 'openai', 'anthropic', 'deepseek', 'gemini', 'azure', 'mock'], default='mock', help='使用的LLM提供商')
    parser.add_argument('--model', type=str, help='使用的模型名称（默认值取决于提供商）')
    parser.add_argument('--verbose', action='store_true', help='启用详细输出')
    parser.add_argument('--debug', action='store_true', help='启用调试输出')
    parser.add_argument('--timeout', type=int, default=60, help='API请求超时时间（秒）')
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("调试日志级别已启用")
    elif args.verbose:
        logger.setLevel(logging.INFO)
        logger.info("详细日志级别已启用")
    
    # 记录系统信息
    logger.debug(f"操作系统: {platform.system()} {platform.release()}")
    logger.debug(f"Python版本: {platform.python_version()}")
    logger.debug(f"命令行参数: {args}")

    # 从参数获取提示词
    prompt = args.prompt

    # 如果指定了文件，读取内容
    file_content = None
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        prompt = f"{prompt}\n\n文件内容:\n{file_content}"
        logger.debug(f"已加载文件: {args.file}, 内容长度: {len(file_content)}字符")

    # 调用LLM
    try:
        logger.info(f"开始调用LLM, 提供商: {args.provider}, 模型: {args.model or '默认'}")
        response = query_planner_llm(prompt, args.provider, args.model, timeout=args.timeout)
        
        # 直接输出响应结果
        print(f"\n{'-'*50}\nLLM响应:\n{response}\n{'-'*50}")
    except Exception as e:
        logger.error(f"调用LLM时出错: {e}")
        print(f"调用LLM时出错: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 