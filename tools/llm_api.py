#!/usr/bin/env python3

import google.generativeai as genai
from openai import OpenAI, AzureOpenAI
from anthropic import Anthropic
import argparse
import os
from dotenv import load_dotenv
from pathlib import Path
import sys
import base64
import logging
from typing import Optional, Union, List, Dict, Any
import mimetypes
import time
import platform
import httpx

# 将当前目录添加到sys.path以解决直接运行脚本时的导入问题
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
import tools.token_tracker as token_tracker
from tools.token_tracker import TokenUsage, APIResponse, get_token_tracker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("llm_api")

def load_environment():
    """Load environment variables from .env files in order of precedence"""
    # Order of precedence:
    # 1. System environment variables (already loaded)
    # 2. .env.local (user-specific overrides)
    # 3. .env (project defaults)
    # 4. .env.example (example configuration)
    
    env_files = ['.env.local', '.env', '.env.example']
    env_loaded = False
    
    logger.debug("Current working directory: %s", Path('.').absolute())
    logger.debug("Looking for environment files: %s", env_files)
    
    for env_file in env_files:
        env_path = Path('.') / env_file
        logger.debug("Checking %s", env_path.absolute())
        if env_path.exists():
            logger.info("Found %s, loading variables...", env_file)
            load_dotenv(dotenv_path=env_path)
            env_loaded = True
            logger.info("Loaded environment variables from %s", env_file)
            # Print loaded keys (but not values for security)
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    keys = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
                    logger.debug("Keys loaded from %s: %s", env_file, keys)
            except Exception as e:
                logger.warning("Error reading keys from %s: %s", env_file, e)
    
    if not env_loaded:
        logger.warning("No .env files found. Using system environment variables only.")
        logger.debug("Available system environment variables: %s", list(os.environ.keys()))

# Load environment variables at module import
load_environment()

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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:8006/v1")

# 创建一个httpx客户端，用于处理代理和超时
http_client = httpx.Client(
    timeout=60.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
)

def encode_image_file(image_path: str) -> tuple[str, str]:
    """
    Encode an image file to base64 and determine its MIME type.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        tuple: (base64_encoded_string, mime_type)
    """
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = 'image/png'  # Default to PNG if type cannot be determined
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    return encoded_string, mime_type

def create_llm_client(provider="openai"):
    """创建LLM客户端
    
    Args:
        provider (str): LLM提供商名称
        
    Returns:
        客户端实例
        
    Raises:
        ValueError: 如果未找到API密钥或提供商不受支持
    """
    if provider == "openai":
        api_key = OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key,
            http_client=http_client
        )
    elif provider == "azure":
        api_key = AZURE_OPENAI_API_KEY
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables")
        return AzureOpenAI(
            api_key=api_key,
            api_version="2024-08-01-preview",
            azure_endpoint=AZURE_ENDPOINT,
            http_client=http_client
        )
    elif provider == "deepseek":
        api_key = DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            http_client=http_client
        )
    elif provider == "anthropic":
        api_key = ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return Anthropic(
            api_key=api_key
        )
    elif provider == "gemini":
        api_key = GOOGLE_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        return genai
    elif provider == "local":
        return OpenAI(
            base_url=LOCAL_LLM_URL,
            api_key="not-needed",
            http_client=http_client
        )
    elif provider == "siliconflow":
        api_key = SILICONFLOW_API_KEY
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key,
            base_url=SILICONFLOW_API_URL,
            http_client=http_client
        )
    elif provider == "openrouter":
        api_key = OPENROUTER_API_KEY
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_API_URL,
            http_client=http_client
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def query_llm(prompt: str, client=None, model=None, provider="openai", image_path: Optional[str] = None) -> Optional[str]:
    """
    Query an LLM with a prompt and optional image attachment.
    
    Args:
        prompt (str): The text prompt to send
        client: The LLM client instance
        model (str, optional): The model to use. Special handling for OpenAI's o1 model:
            - Uses different response format
            - Has reasoning_effort parameter
            - Is the only model that provides reasoning_tokens in its response
        provider (str): The API provider to use
        image_path (str, optional): Path to an image file to attach
        
    Returns:
        Optional[str]: The LLM's response or None if there was an error
        
    Note:
        Token tracking behavior varies by provider:
        - OpenAI-style APIs (OpenAI, Azure, DeepSeek, Local): Full token tracking
        - Anthropic: Has its own token tracking system (input/output tokens)
        - Gemini: Token tracking not yet implemented
        
        Reasoning tokens are only available when using OpenAI's o1 model.
        For all other models, reasoning_tokens will be None.
    """
    if client is None:
        client = create_llm_client(provider)
    
    try:
        # Set default model
        if model is None:
            if provider == "openai":
                model = "gpt-4o"
            elif provider == "azure":
                model = os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt-4o-ms')  # Get from env with fallback
            elif provider == "deepseek":
                model = "deepseek-chat"
            elif provider == "anthropic":
                model = "claude-3-5-sonnet-20241022"
            elif provider == "gemini":
                model = "gemini-2.0-flash"
            elif provider == "local":
                model = "Qwen/Qwen2.5-32B-Instruct-AWQ"
            elif provider == "siliconflow":
                model = "deepseek-ai/DeepSeek-R1"
            elif provider == "openrouter":
                model = "openai/gpt-4o"
        
        start_time = time.time()
        
        if provider in ["openai", "local", "deepseek", "azure", "siliconflow", "openrouter"]:
            # 这些提供商都使用OpenAI兼容的API
            system_message = {"role": "system", "content": "你是一个有用的助手。"}
            user_message = {"role": "user", "content": []}
            
            # Add text content
            user_message["content"].append({
                "type": "text",
                "text": prompt
            })
            
            # Add image content if provided
            if image_path:
                if provider in ["openai", "azure"]:
                    encoded_image, mime_type = encode_image_file(image_path)
                    user_message["content"] = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"}}
                    ]
            
            messages = [system_message, user_message]
            
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
            }
            
            # Add o1-specific parameters
            if model == "o1" or model.endswith("/o1"):
                kwargs["response_format"] = {"type": "text"}
                kwargs["reasoning_effort"] = "low"
                del kwargs["temperature"]
            
            # Add OpenRouter-specific headers
            if provider == "openrouter":
                kwargs["extra_headers"] = {
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                    "X-Title": os.getenv("OPENROUTER_APP_TITLE", "LLM API Tool")
                }
            
            response = client.chat.completions.create(**kwargs)
            thinking_time = time.time() - start_time
            
            # Track token usage
            token_usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                reasoning_tokens=response.usage.reasoning_tokens if hasattr(response.usage, 'reasoning_tokens') and (model.lower() == "o1" or model.lower().endswith("/o1")) else None
            )
            
            # Calculate cost
            if hasattr(get_token_tracker(), "calculate_cost"):
                cost = get_token_tracker().calculate_cost(
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens,
                    model,
                    provider
                )
            else:
                # 兼容旧版本的token_tracker
                if provider in ["openai", "azure", "deepseek", "local", "siliconflow", "openrouter"]:
                    cost = get_token_tracker().calculate_openai_cost(
                        token_usage.prompt_tokens,
                        token_usage.completion_tokens,
                        model
                    )
                else:
                    cost = 0.0
            
            # Track the request
            api_response = APIResponse(
                content=response.choices[0].message.content,
                token_usage=token_usage,
                cost=cost,
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            get_token_tracker().track_request(api_response)
            
            return response.choices[0].message.content
            
        elif provider == "anthropic":
            messages = [{"role": "user", "content": []}]
            
            # Add text content
            messages[0]["content"].append({
                "type": "text",
                "text": prompt
            })
            
            # Add image content if provided
            if image_path:
                encoded_image, mime_type = encode_image_file(image_path)
                messages[0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": encoded_image
                    }
                })
            
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                messages=messages
            )
            thinking_time = time.time() - start_time
            
            # Track token usage
            token_usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
            )
            
            # Calculate cost
            if hasattr(get_token_tracker(), "calculate_cost"):
                cost = get_token_tracker().calculate_cost(
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens,
                    model,
                    provider
                )
            else:
                # 兼容旧版本的token_tracker
                cost = get_token_tracker().calculate_claude_cost(
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens,
                    model
                )
            
            # Track the request
            api_response = APIResponse(
                content=response.content[0].text,
                token_usage=token_usage,
                cost=cost,
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            get_token_tracker().track_request(api_response)
            
            return response.content[0].text
            
        elif provider == "gemini":
            model_instance = client.GenerativeModel(model)
            
            if image_path:
                # 使用Gemini的多模态能力
                image_data = None
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                response = model_instance.generate_content([prompt, image_data])
            else:
                response = model_instance.generate_content(prompt)
            
            thinking_time = time.time() - start_time
            
            # Gemini 目前不提供标准的token统计，我们可以粗略估计
            estimated_prompt_tokens = len(prompt.split()) * 1.3
            estimated_completion_tokens = len(response.text.split()) * 1.3
            
            token_usage = TokenUsage(
                prompt_tokens=int(estimated_prompt_tokens),
                completion_tokens=int(estimated_completion_tokens),
                total_tokens=int(estimated_prompt_tokens + estimated_completion_tokens)
            )
            
            # Gemini价格估计
            if hasattr(get_token_tracker(), "calculate_cost"):
                cost = get_token_tracker().calculate_cost(
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens,
                    model,
                    provider
                )
            else:
                # 粗略估计Gemini成本
                cost = (token_usage.prompt_tokens / 1000 * 0.0005) + (token_usage.completion_tokens / 1000 * 0.0015)
            
            api_response = APIResponse(
                content=response.text,
                token_usage=token_usage,
                cost=cost,
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            get_token_tracker().track_request(api_response)
            
            return response.text
            
    except Exception as e:
        logger.error(f"Error querying LLM ({provider}/{model}): {e}")
        print(f"Error querying LLM: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Query an LLM with a prompt')
    parser.add_argument('--prompt', type=str, help='The prompt to send to the LLM', required=True)
    parser.add_argument('--provider', 
                       choices=['openai','anthropic','gemini','local','deepseek','azure','siliconflow','openrouter','mock'], 
                       default='openai', help='The API provider to use')
    parser.add_argument('--model', type=str, help='The model to use (default depends on provider)')
    parser.add_argument('--image', type=str, help='Path to an image file to attach to the prompt')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # 记录系统信息
    logger.debug("Operating System: %s", platform.system())
    logger.debug("Python Version: %s", platform.python_version())

    if not args.model:
        if args.provider == 'openai':
            args.model = "gpt-4o" 
        elif args.provider == "deepseek":
            args.model = "deepseek-chat"
        elif args.provider == 'anthropic':
            args.model = "claude-3-5-sonnet-20241022"
        elif args.provider == 'gemini':
            args.model = "gemini-2.0-flash"
        elif args.provider == 'azure':
            args.model = os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt-4o-ms')
        elif args.provider == 'siliconflow':
            args.model = "deepseek-ai/DeepSeek-R1"
        elif args.provider == 'openrouter':
            args.model = "openai/gpt-4o"
        elif args.provider == 'mock':
            args.model = "mock-model"

    try:
        if args.provider == 'mock':
            logger.info("Using mock LLM provider")
            response = mock_response(args.prompt, args.model)
        else:
            client = create_llm_client(args.provider)
            logger.info(f"Querying {args.provider}/{args.model}")
            response = query_llm(args.prompt, client, model=args.model, provider=args.provider, image_path=args.image)
        
        if response:
            print(response)
        else:
            print("未能从LLM获取响应", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        logger.error(f"调用LLM时出错: {e}")
        print(f"调用LLM时出错: {e}", file=sys.stderr)
        sys.exit(1)

def mock_response(prompt: str, model: str = "mock-model") -> str:
    """生成模拟响应，用于测试和调试
    
    Args:
        prompt: 提示词
        model: 模型名称
        
    Returns:
        模拟的响应文本
    """
    logger.info(f"Mock LLM called with prompt: {prompt[:30]}...")
    
    # 模拟token使用情况和成本计算
    estimated_prompt_tokens = len(prompt.split()) * 1.3
    estimated_completion_tokens = 150  # 假设响应大约有150个token
    
    token_usage = TokenUsage(
        prompt_tokens=int(estimated_prompt_tokens),
        completion_tokens=estimated_completion_tokens,
        total_tokens=int(estimated_prompt_tokens) + estimated_completion_tokens
    )
    
    # 使用安全的成本计算方式，固定一个低成本
    cost = 0.001  # 固定成本为0.001美元
    
    # 记录模拟响应
    api_response = APIResponse(
        content="模拟响应",
        token_usage=token_usage,
        cost=cost,
        thinking_time=0.5,
        provider="mock",
        model=model
    )
    
    try:
        get_token_tracker().track_request(api_response)
    except Exception as e:
        logger.warning(f"无法记录token使用情况: {e}")
    
    # 根据提示词包含的关键字返回不同的模拟响应
    if "任务" in prompt and "规划" in prompt:
        return """
任务规划优化功能开发可以拆分为以下具体子任务：

1. 需求分析与范围确定
   - 明确任务规划优化的具体目标和需求
   - 定义输入输出规范和性能指标
   - 确定优化范围和约束条件

2. 算法设计与选型
   - 研究适用的任务规划算法（关键路径、资源分配等）
   - 设计任务依赖关系表示模型
   - 确定优先级计算方法和规则

3. 核心引擎实现
   - 开发任务分解与组合模块
   - 实现依赖关系分析功能
   - 开发关键路径识别算法
   - 构建资源分配与约束处理机制

4. LLM集成与提示工程
   - 设计LLM任务分解提示模板
   - 实现LLM响应解析器
   - 开发LLM与规划引擎的集成接口
   - 优化提示词以提高分解质量

5. 测试与优化
   - 构建单元测试和集成测试
   - 性能基准测试和对比分析
   - 边缘情况处理和鲁棒性增强
   - 算法参数调优和性能优化

6. 文档与示例
   - 编写API文档和使用说明
   - 创建示例和教程
   - 整理最佳实践指南
"""
    elif "测试" in prompt:
        return "这是一条模拟响应，用于测试llm_api模块的导入和基本功能。"
    else:
        return f"已收到您的提示: {prompt[:50]}...，这是一个模拟响应，仅用于测试。"

if __name__ == "__main__":
    main()