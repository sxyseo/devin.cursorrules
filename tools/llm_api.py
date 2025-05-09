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
from typing import Optional, Union, List, Dict, Any, Tuple, AsyncGenerator
import mimetypes
import time
import platform
import httpx
import json
import asyncio

# 将当前目录添加到sys.path以解决直接运行脚本时的导入问题
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
import tools.token_tracker as token_tracker
from tools.token_tracker import TokenUsage, APIResponse, get_token_tracker, TokenTracker
try:
    from tools.error_handler import get_error_handler, ErrorCategory, ErrorSeverity, handle_exception
    error_handler_available = True
except ImportError:
    error_handler_available = False
    print("警告: 错误处理模块不可用，将使用基本错误处理", file=sys.stderr)

# 获取错误处理器
error_handler = get_error_handler() if error_handler_available else None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("llm_api")

# 全局变量
OPENAI_API_KEY = None
ANTHROPIC_API_KEY = None
GOOGLE_API_KEY = None
DEEPSEEK_API_KEY = None
AZURE_OPENAI_API_KEY = None
AZURE_ENDPOINT = None
LOCAL_LLM_URL = "http://localhost:8080/v1"
SILICONFLOW_API_KEY = None
SILICONFLOW_API_URL = "https://api.siliconflow.com/v1"
OPENROUTER_API_KEY = None
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"

# 创建一个HTTP客户端，超时设置为60秒
http_client = httpx.Client(timeout=60.0)

def load_environment():
    """加载环境变量
    
    Returns:
        Dict[str, str]: 环境变量映射
    """
    global OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, DEEPSEEK_API_KEY
    global AZURE_OPENAI_API_KEY, AZURE_ENDPOINT, SILICONFLOW_API_KEY, OPENROUTER_API_KEY
    
    # 尝试加载.env文件
    try:
        from dotenv import load_dotenv
        
        # 优先级：.env.local > .env > .env.example
        env_files = ['.env.local', '.env', '.env.example']
        for env_file in env_files:
            env_path = Path(env_file)
            if env_path.exists():
                logger.debug(f"从 {env_file} 加载环境变量")
                load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        logger.warning("未找到dotenv模块，无法从.env文件加载环境变量")
    except Exception as e:
        logger.warning(f"加载环境变量时出错: {e}")
    
    # 获取API密钥
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
    AZURE_ENDPOINT = os.environ.get('AZURE_ENDPOINT', 'https://msopenai.openai.azure.com')
    SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    
    # 返回环境变量映射
    return {
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'ANTHROPIC_API_KEY': ANTHROPIC_API_KEY,
        'GOOGLE_API_KEY': GOOGLE_API_KEY,
        'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY,
        'AZURE_OPENAI_API_KEY': AZURE_OPENAI_API_KEY,
        'AZURE_ENDPOINT': AZURE_ENDPOINT,
        'SILICONFLOW_API_KEY': SILICONFLOW_API_KEY,
        'OPENROUTER_API_KEY': OPENROUTER_API_KEY
    }

def encode_image_file(image_path: str) -> Tuple[str, str]:
    """将图像文件编码为base64字符串，并确定MIME类型
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        Tuple[str, str]: (base64编码的图像, MIME类型)
        
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是图像
    """
    # 判断文件是否存在
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    # 确定MIME类型
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError(f"不是有效的图像文件: {image_path}")
    
    # 读取并编码文件
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    return encoded_string, mime_type

# 修改TokenTracker.APIResponse类，添加lower方法
# 在token_tracker.py中添加此方法太复杂，直接在这里扩展类
def api_response_lower(self):
    """将content转换为小写"""
    return self.content.lower() if self.content else ""

# 扩展APIResponse类
APIResponse.lower = api_response_lower

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

@handle_exception(source="query_llm", context={"module": "llm_api"})
def query_llm(prompt: str, 
              client=None, 
              model=None, 
              provider="openai", 
              image_path: Optional[str] = None,
              max_retries: int = 3,
              mock_mode: bool = False,
              temperature: float = 0.7,
              stream: bool = False) -> Union[APIResponse, AsyncGenerator]:
    """调用大语言模型API

    Args:
        prompt: 提示词
        client: LLM客户端对象，如果为None则创建新的客户端
        model: 使用的模型名称，如果为None则使用默认模型
        provider: 使用的提供商，默认为"openai"
        image_path: 可选的图像路径，用于多模态交互
        max_retries: 最大重试次数
        mock_mode: 是否使用模拟响应
        temperature: 温度参数，控制输出的随机性 (0-1)
        stream: 是否使用流式响应

    Returns:
        如果stream=False，返回API响应对象；如果stream=True，返回一个异步生成器
    """
    if stream:
        # 对于流式响应，直接返回异步生成器
        return query_llm_stream(
            prompt=prompt,
            client=client,
            model=model,
            provider=provider,
            image_path=image_path,
            max_retries=max_retries,
            mock_mode=mock_mode,
            temperature=temperature
        )
    
    # 非流式响应的逻辑
    start_time = time.time()
    logger.info(f"调用LLM API，提供商: {provider}，模型: {model or '默认'}，提示词长度: {len(prompt)}")
    
    # 创建令牌追踪器
    token_tracker = get_token_tracker()
    
    # 如果处于模拟模式，返回模拟响应
    if mock_mode:
        logger.info("使用模拟模式返回响应")
        mock_text = f"这是来自{provider}的模拟响应: {prompt[:20]}..."
        
        # 创建模拟的令牌使用情况
        token_usage = TokenUsage(
            prompt_tokens=len(prompt.split()),
            completion_tokens=10,
            total_tokens=len(prompt.split()) + 10
        )
        
        mock_response = APIResponse(
            content=mock_text,
            token_usage=token_usage,
            cost=0.001,
            thinking_time=0.1,
            provider=provider,
            model=model or "mock-model"
        )
        
        return mock_response
    
    # 加载环境变量
    env_vars = load_environment()
    
    # 根据提供商设置默认模型
    if model is None:
        if provider == "openai":
            model = "gpt-4o"
        elif provider == "anthropic":
            model = "claude-3-5-sonnet-20241022"
        elif provider == "gemini":
            model = "gemini-pro"
        elif provider == "azure":
            model = env_vars.get("AZURE_OPENAI_MODEL_DEPLOYMENT", "gpt-4o-ms")
        elif provider == "deepseek":
            model = "deepseek-chat"
        elif provider == "siliconflow":
            model = "deepseek-ai/DeepSeek-R1"
        elif provider == "openrouter":
            model = "openai/gpt-4o"
        elif provider == "local":
            model = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    
    current_retry = 0
    last_error = None
    
    while current_retry <= max_retries:
        try:
            # 如果没有提供客户端，则创建新的客户端
            if client is None:
                client = create_llm_client(provider)
            
            logger.info(f"调用 {provider} 的 {model} 模型")
            
            # 根据提供商和模型发送请求
            if provider == "openai" or provider == "azure" or provider == "deepseek" or provider == "local" or provider == "siliconflow" or provider == "openrouter":
                messages = []
                # 处理图像
                if image_path:
                    encoded_image, mime_type = encode_image_file(image_path)
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{encoded_image}"
                                    }
                                }
                            ]
                        }
                    ]
                else:
                    messages = [{"role": "user", "content": prompt}]
                
                # 发送请求
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature
                )
                
                # 解析响应
                response_text = response.choices[0].message.content
                
                # 创建令牌使用情况对象
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
                
            elif provider == "anthropic":
                messages = [{"role": "user", "content": prompt}]
                
                if image_path:
                    encoded_image, mime_type = encode_image_file(image_path)
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": encoded_image
                                    }
                                }
                            ]
                        }
                    ]
                
                response = client.messages.create(
                    model=model,
                    messages=messages,
                    max_tokens=1000
                )
                
                response_text = response.content[0].text
                
                # 创建令牌使用情况对象
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens
                )
                
            elif provider == "gemini":
                if image_path:
                    import PIL.Image
                    img = PIL.Image.open(image_path)
                    model_client = client.GenerativeModel(model)
                    response = model_client.generate_content([prompt, img])
                else:
                    model_client = client.GenerativeModel(model)
                    response = model_client.generate_content(prompt)
                
                response_text = response.text
                
                # 估计Gemini的令牌使用情况
                estimated_prompt_tokens = len(prompt.split()) * 1.3
                estimated_completion_tokens = len(response_text.split()) * 1.3
                
                # 创建令牌使用情况对象
                token_usage = TokenUsage(
                    prompt_tokens=int(estimated_prompt_tokens),
                    completion_tokens=int(estimated_completion_tokens),
                    total_tokens=int(estimated_prompt_tokens + estimated_completion_tokens)
                )
            
            else:
                raise ValueError(f"不支持的提供商: {provider}")
            
            # 计算延迟
            thinking_time = time.time() - start_time
            
            # 计算成本
            cost = TokenTracker.calculate_cost(
                token_usage.prompt_tokens,
                token_usage.completion_tokens,
                model,
                provider
            )
            
            # 创建APIResponse对象
            api_response = APIResponse(
                content=response_text,
                token_usage=token_usage,
                cost=cost,
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            
            # 跟踪请求
            token_tracker.track_request(api_response)
            
            return api_response
            
        except Exception as e:
            last_error = e
            current_retry += 1
            
            # 使用错误处理器记录错误
            if error_handler:
                error_info = error_handler.handle_error(e, "query_llm", {
                    "provider": provider,
                    "model": model,
                    "retry": current_retry,
                    "max_retries": max_retries,
                    "has_image": image_path is not None
                })
                
                # 根据错误类别确定重试策略
                if error_info.category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.API]:
                    # 使用指数退避策略
                    wait_time = min(2 ** (current_retry - 1), 60)
                    logger.warning(f"查询LLM失败 (重试 {current_retry}/{max_retries})，等待 {wait_time} 秒: {e}")
                    time.sleep(wait_time)
                    continue
            else:
                # 如果没有错误处理器，使用简单的退避策略
                wait_time = min(2 ** (current_retry - 1), 60)
                logger.warning(f"查询LLM失败 (重试 {current_retry}/{max_retries})，等待 {wait_time} 秒: {e}")
                time.sleep(wait_time)
    
    # 如果所有重试都失败，返回模拟响应
    logger.error(f"调用 {provider} 模型失败，已达到最大重试次数: {max_retries}")
    
    # 生成错误报告
    if error_handler:
        error_report = error_handler.get_error_report()
        logger.error(f"错误报告: {json.dumps(error_report, ensure_ascii=False)}")
    
    # 返回模拟响应，但标记为失败
    mock_text = f"[错误] 调用{provider}模型失败: {str(last_error) if last_error else '未知错误'}"
    
    token_usage = TokenUsage(
        prompt_tokens=len(prompt.split()),
        completion_tokens=10,
        total_tokens=len(prompt.split()) + 10
    )
    
    mock_response = APIResponse(
        content=mock_text,
        token_usage=token_usage,
        cost=0,
        thinking_time=time.time() - start_time,
        provider=provider,
        model=model or "mock-model"
    )
    
    return mock_response

async def query_llm_stream(
    prompt: str, 
    client=None, 
    model=None, 
    provider="openai", 
    image_path: Optional[str] = None,
    max_retries: int = 3,
    mock_mode: bool = False,
    temperature: float = 0.7
) -> AsyncGenerator[Any, None]:
    """以流式方式调用大语言模型API

    Args:
        prompt: 提示词
        client: LLM客户端对象，如果为None则创建新的客户端
        model: 使用的模型名称，如果为None则使用默认模型
        provider: 使用的提供商，默认为"openai"
        image_path: 可选的图像路径，用于多模态交互
        max_retries: 最大重试次数
        mock_mode: 是否使用模拟响应
        temperature: 温度参数，控制输出的随机性 (0-1)

    Yields:
        流式响应片段
    """
    logger.info(f"流式调用LLM API，提供商: {provider}，模型: {model or '默认'}，提示词长度: {len(prompt)}")
    
    if mock_mode:
        # 模拟流式响应
        mock_responses = mock_stream_response(prompt)
        for chunk in mock_responses:
            await asyncio.sleep(0.1)  # 模拟网络延迟
            yield chunk
        return

    # 创建客户端（如果未提供）
    if client is None:
        client = create_llm_client(provider=provider)
    
    # 设置默认模型（如果未提供）
    if model is None:
        if provider == "openai":
            model = "gpt-4o"
        elif provider == "anthropic":
            model = "claude-3-sonnet-20240229"
        elif provider == "deepseek":
            model = "deepseek-chat"
        elif provider == "siliconflow":
            model = "deepseek-coder"
        elif provider == "gemini":
            model = "gemini-pro"
        elif provider == "azure":
            # 从环境变量中获取部署名称，默认为gpt-4o-ms
            model = os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT", "gpt-4o-ms")
        else:  # 本地模型
            model = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    
    current_retry = 0
    last_error = None
    
    while current_retry <= max_retries:
        try:
            # 处理多模态查询
            if image_path:
                if provider in ["openai", "azure"]:
                    # 设置多模态消息
                    base64_image, content_type = encode_image_file(image_path)
                    
                    # 创建带有图像的消息
                    messages = [
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{base64_image}"}}
                        ]}
                    ]
                    
                    # 使用OpenAI流式API
                    if provider == "openai":
                        stream = await client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            stream=True
                        )
                    else:  # Azure
                        stream = await client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            stream=True
                        )
                
                elif provider == "anthropic":
                    # Anthropic 的多模态支持
                    base64_image, content_type = encode_image_file(image_path)
                    
                    stream = await client.messages.create(
                        model=model,
                        max_tokens=1024,
                        temperature=temperature,
                        stream=True,
                        messages=[
                            {
                                "role": "user", 
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": base64_image}}
                                ]
                            }
                        ]
                    )
                
                elif provider == "gemini":
                    # Gemini 的多模态支持
                    image_parts = [{"mime_type": mimetypes.guess_type(image_path)[0], "data": open(image_path, "rb").read()}]
                    stream = client.generate_content(
                        model=model,
                        contents=[{"role": "user", "parts": [prompt, {"inline_data": image_parts[0]}]}],
                        stream=True
                    )
                else:
                    raise ValueError(f"提供商 {provider} 不支持多模态流式响应")
            else:
                # 常规文本查询
                if provider == "openai":
                    stream = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        stream=True
                    )
                elif provider == "anthropic":
                    stream = await client.messages.create(
                        model=model,
                        max_tokens=1024,
                        temperature=temperature,
                        stream=True,
                        messages=[{"role": "user", "content": prompt}]
                    )
                elif provider == "deepseek":
                    # DeepSeek流式API调用
                    messages = [{"role": "user", "content": prompt}]
                    stream = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        stream=True
                    )
                elif provider == "siliconflow":
                    # SiliconFlow流式API调用
                    messages = [{"role": "user", "content": prompt}]
                    stream = client.completions.create(
                        model=model,
                        prompt=prompt,
                        temperature=temperature,
                        stream=True
                    )
                elif provider == "gemini":
                    # Gemini流式API调用
                    stream = client.generate_content(
                        model=model,
                        contents=[{"role": "user", "parts": [prompt]}],
                        stream=True
                    )
                elif provider == "azure":
                    # Azure OpenAI流式API调用
                    stream = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        stream=True
                    )
                else:
                    # 本地LLM流式调用
                    raise NotImplementedError(f"流式调用尚未实现: {provider}")
            
            # 处理流式响应
            async for chunk in stream:
                yield chunk
            
            # 成功获取响应，跳出重试循环
            break
            
        except Exception as e:
            error_msg = f"流式调用LLM时出错 (重试 {current_retry}/{max_retries}): {str(e)}"
            logger.error(error_msg)
            if error_handler:
                error_handler.handle_error(
                    e, 
                    category="API_ERROR", 
                    severity="MEDIUM",
                    context={
                        "provider": provider,
                        "model": model,
                        "retry": current_retry,
                        "stream": True
                    }
                )
            last_error = e
            current_retry += 1
            if current_retry <= max_retries:
                # 指数退避重试
                await asyncio.sleep(2 ** current_retry)
    
    # 如果所有重试都失败了，抛出异常
    if current_retry > max_retries and last_error is not None:
        logger.error(f"达到最大重试次数，无法获取流式响应: {last_error}")
        raise last_error
        
def mock_stream_response(prompt: str) -> List[str]:
    """生成模拟的流式响应

    Args:
        prompt: 提示词

    Returns:
        模拟的流式响应片段列表
    """
    # 构建模拟响应
    if "任务" in prompt and "规划" in prompt:
        full_response = """
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
        full_response = "这是一条模拟响应，用于测试llm_api模块的流式功能。"
    else:
        full_response = f"已收到您的提示: {prompt[:50]}...，这是一个模拟的流式响应，仅用于测试。"
    
    # 将完整响应分割成多个块
    words = full_response.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 5 or word.endswith(('.', '?', '!')):
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def mock_response(prompt: str, model: str = "mock-model") -> str:
    """提供模拟的LLM响应，用于测试和开发
    
    Args:
        prompt: 提示词
        model: 模型名称
        
    Returns:
        str: 模拟的响应文本
    """
    logger.info(f"使用mock模式响应提示: '{prompt[:50]}...' (如果较长)")
    
    # 创建模拟响应
    response = f"这是模拟模式下的回复。您的提问是: '{prompt}'\n\n"
    response += f"在实际模式下，这会使用 {model} 模型进行处理。\n\n"
    
    # 添加一些针对特定提示的自定义响应
    if "健康" in prompt or "health" in prompt.lower():
        response += "系统健康状态良好。所有组件正常运行。"
    elif "服务器" in prompt or "server" in prompt.lower():
        response += "服务器使用FastMCP框架实现，与Cursor完全兼容，提供了丰富的工具功能，可以极大增强Cursor中Claude的能力。"
        response += "通过这种方式，我们可以让Cursor具备持久化记忆、多智能体协作和强大的任务分解能力，更好地辅助复杂的开发工作。"
    elif "记忆" in prompt or "memory" in prompt.lower():
        response += "记忆银行是系统的核心组件，提供了持久化存储和检索功能，支持向量化搜索和多维度记忆管理。"
    elif "错误" in prompt or "error" in prompt.lower():
        response += "系统实现了完善的错误处理机制，包括错误分类、诊断和自动恢复功能，能够有效应对各种异常情况。"
    elif "框架" in prompt or "framework" in prompt.lower():
        response += "多智能体协作框架基于Planner-Executor模式，支持复杂任务的分解、规划和执行，大大提高了智能体的处理能力。"
    else:
        response += "这是一个通用的模拟响应。在实际部署中，您会得到真实的API响应。"
    
    # 跟踪token使用
    tktrkr = get_token_tracker()
    usage = TokenUsage(prompt_tokens=len(prompt.split()), completion_tokens=len(response.split()), total_tokens=len(prompt.split()) + len(response.split()))
    tktrkr.track_usage("mock", model, usage)
    
    return response

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='调用大型语言模型API')
    parser.add_argument('--prompt', type=str, help='提示词')
    parser.add_argument('--provider', type=str, default='openai', 
                      choices=['openai', 'anthropic', 'gemini', 'azure', 'deepseek', 'siliconflow', 'openrouter', 'local', 'mock'],
                      help='LLM提供商')
    parser.add_argument('--model', type=str, help='模型名称 (如果未提供，将使用提供商的默认模型)')
    parser.add_argument('--image', type=str, help='要附加到提示词的图像文件路径')
    parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数')
    parser.add_argument('--mock', action='store_true', help='使用模拟模式（不实际调用API）')
    parser.add_argument('--stream', action='store_true', help='使用流式响应模式')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细日志输出')
    parser.add_argument('--error-report', action='store_true', help='在发生错误时显示完整的错误报告')
    parser.add_argument('--temperature', type=float, default=0.7, help='温度参数，控制输出的随机性 (0-1)')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # 如果没有通过命令行提供提示词，则从终端读取
    if not args.prompt:
        print("请输入提示词 (按Ctrl+D或Ctrl+Z结束):")
        prompt_lines = []
        try:
            while True:
                line = input()
                prompt_lines.append(line)
        except (KeyboardInterrupt, EOFError):
            pass
        args.prompt = "\n".join(prompt_lines)
    
    if not args.prompt:
        parser.print_help()
        sys.exit(1)
    
    try:
        # 如果提供商是mock，设置mock_mode为True
        mock_mode = args.mock or args.provider == 'mock'
        if mock_mode:
            logger.info("使用模拟模式")
            if args.provider == 'mock':
                args.provider = 'openai'  # 默认使用openai作为模拟提供商
        
        if args.stream:
            # 流式模式需要使用异步调用
            import asyncio
            
            async def run_stream():
                try:
                    # 流式调用LLM
                    async for chunk in query_llm_stream(
                        prompt=args.prompt,
                        provider=args.provider,
                        model=args.model,
                        image_path=args.image,
                        max_retries=args.max_retries,
                        mock_mode=mock_mode,
                        temperature=args.temperature
                    ):
                        # 对于不同提供商，响应格式会不同，需要适配
                        if hasattr(chunk, 'choices') and hasattr(chunk.choices[0], 'delta'):
                            # OpenAI格式
                            if chunk.choices[0].delta.content:
                                print(chunk.choices[0].delta.content, end="", flush=True)
                        elif hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                            # Anthropic格式
                            if chunk.delta.text:
                                print(chunk.delta.text, end="", flush=True)
                        elif isinstance(chunk, str):
                            # 直接字符串
                            print(chunk, end="", flush=True)
                        else:
                            # 尝试其他格式
                            try:
                                if hasattr(chunk, 'content'):
                                    print(chunk.content, end="", flush=True)
                                elif isinstance(chunk, dict) and 'content' in chunk:
                                    print(chunk['content'], end="", flush=True)
                            except:
                                # 如果无法提取，直接打印整个对象
                                print(chunk, end="", flush=True)
                    
                    # 流式响应结束后换行
                    print()
                except Exception as e:
                    logger.error(f"流式调用LLM时出错: {e}")
                    if args.verbose and hasattr(e, '__traceback__'):
                        import traceback
                        traceback.print_exception(type(e), e, e.__traceback__)
            
            # 运行异步函数
            asyncio.run(run_stream())
        else:
            # 常规同步调用LLM
            response = query_llm(
                prompt=args.prompt,
                provider=args.provider,
                model=args.model,
                image_path=args.image,
                max_retries=args.max_retries,
                mock_mode=mock_mode,
                temperature=args.temperature
            )
            
            # 打印响应文本
            print(response.content)
            
            # 打印令牌使用情况
            if args.verbose:
                print("\n令牌使用情况:")
                print(f"提示词令牌: {response.token_usage.prompt_tokens}")
                print(f"补全令牌: {response.token_usage.completion_tokens}")
                print(f"总令牌: {response.token_usage.total_tokens}")
                print(f"延迟: {response.thinking_time:.2f}秒")
                
                # 显示会话总计
                session_summary = get_token_tracker().get_session_summary()
                print("\n会话总计:")
                print(f"总请求数: {session_summary['total_requests']}")
                print(f"总成本: ${session_summary['total_cost']:.4f}")
                print(f"总令牌数: {session_summary['total_tokens']}")
            
    except Exception as e:
        logger.error(f"调用LLM时出错: {e}")
        
        # 显示错误报告
        if args.error_report and error_handler:
            error_report = error_handler.get_error_report()
            print("\n错误报告:")
            print(json.dumps(error_report, indent=2, ensure_ascii=False))
        
        if args.verbose and hasattr(e, '__traceback__'):
            import traceback
            traceback.print_exception(type(e), e, e.__traceback__)
        
        sys.exit(1)

if __name__ == "__main__":
    main()