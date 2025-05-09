"""LLM API测试脚本

用于测试不同LLM提供商API的调用和错误处理。
"""

import os
import sys
import json
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple

try:
    from . import error_handler
    from .error_handler import ErrorCategory, ErrorSeverity, error_handler
except ImportError:
    # 当作为独立脚本运行时
    error_handler = None
    ErrorCategory = None
    ErrorSeverity = None

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm_api_test")

class LLMAPITest:
    """LLM API测试类，用于测试不同LLM提供商API的调用和错误处理"""
    
    PROVIDERS = [
        "openai",
        "anthropic",
        "deepseek",
        "siliconflow",
        "gemini",
        "local",
        "azure",
        "openrouter"
    ]
    
    def __init__(self, tool_dir: str = None):
        """初始化LLM API测试
        
        Args:
            tool_dir: 工具目录的路径，默认为当前目录
        """
        # 查找llm_api.py文件
        if tool_dir is None:
            # 如果未指定，尝试从当前模块所在目录查找
            import pathlib
            current_path = pathlib.Path(__file__).parent
            
            # 首先尝试当前目录
            self.llm_api_path = current_path / "llm_api.py"
            
            # 如果不存在，尝试上一级的tools目录
            if not self.llm_api_path.exists():
                self.llm_api_path = current_path.parent / "tools" / "llm_api.py"
            
            # 如果还不存在，尝试项目根目录下的tools目录
            if not self.llm_api_path.exists():
                self.llm_api_path = current_path.parent.parent / "tools" / "llm_api.py"
        else:
            self.llm_api_path = os.path.join(tool_dir, "llm_api.py")
        
        # 检查文件是否存在
        if not os.path.exists(self.llm_api_path):
            raise FileNotFoundError(f"找不到llm_api.py文件: {self.llm_api_path}")
        
        # 初始化结果字典
        self.results = {}
        
        logger.info(f"使用LLM API路径: {self.llm_api_path}")
    
    def _import_llm_api(self):
        """导入llm_api模块
        
        Returns:
            导入的llm_api模块
        """
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("llm_api", self.llm_api_path)
            llm_api = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(llm_api)
            return llm_api
        except Exception as e:
            logger.error(f"导入llm_api模块失败: {e}")
            traceback.print_exc()
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, 
                    {"component": "import_llm_api"}
                )
            raise
    
    def test_provider(self, provider: str, model: str = None) -> Dict[str, Any]:
        """测试特定提供商的API调用
        
        Args:
            provider: 提供商名称
            model: 模型名称，如果为None则使用默认模型
            
        Returns:
            包含测试结果的字典
        """
        logger.info(f"测试提供商: {provider}, 模型: {model or '默认'}")
        
        result = {
            "provider": provider,
            "model": model,
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # 导入llm_api模块
            llm_api = self._import_llm_api()
            
            # 简单提示词
            prompt = "简要回答：1+1等于几？"
            
            # 记录开始时间
            start_time = time.time()
            
            # 调用query_llm函数
            response = llm_api.query_llm(prompt, provider=provider, model=model)
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 记录结果
            result.update({
                "status": "success",
                "response": response,
                "elapsed_time": elapsed_time,
                "error": None
            })
            
            logger.info(f"测试成功，耗时: {elapsed_time:.2f}秒")
            logger.info(f"响应: {response[:100]}...")
        except Exception as e:
            logger.error(f"测试失败: {e}")
            
            # 记录错误信息
            result.update({
                "status": "failed",
                "response": None,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
            })
            
            # 使用错误处理器处理错误
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.API, ErrorSeverity.MEDIUM, 
                    {"provider": provider, "model": model}
                )
        
        return result
    
    def test_all_providers(self, include_models: bool = False) -> Dict[str, Any]:
        """测试所有提供商的API调用
        
        Args:
            include_models: 是否测试每个提供商的多个模型
            
        Returns:
            包含所有测试结果的字典
        """
        results = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "providers": {}
        }
        
        # 定义要测试的提供商和模型
        test_cases = []
        for provider in self.PROVIDERS:
            if include_models:
                # 为每个提供商定义要测试的模型
                models = self._get_provider_models(provider)
                for model in models:
                    test_cases.append((provider, model))
            else:
                # 只使用默认模型
                test_cases.append((provider, None))
        
        # 执行测试
        for provider, model in test_cases:
            try:
                result = self.test_provider(provider, model)
                
                # 添加到结果
                if provider not in results["providers"]:
                    results["providers"][provider] = {
                        "default": None,
                        "models": {}
                    }
                
                if model is None:
                    results["providers"][provider]["default"] = result
                else:
                    results["providers"][provider]["models"][model] = result
            except Exception as e:
                logger.error(f"测试提供商 {provider} 模型 {model or '默认'} 时出错: {e}")
                
                # 记录错误
                if provider not in results["providers"]:
                    results["providers"][provider] = {
                        "default": None,
                        "models": {}
                    }
                
                error_info = {
                    "provider": provider,
                    "model": model,
                    "status": "error",
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc()
                    }
                }
                
                if model is None:
                    results["providers"][provider]["default"] = error_info
                else:
                    results["providers"][provider]["models"][model] = error_info
        
        # 生成摘要
        summary = {
            "total_providers": len(self.PROVIDERS),
            "successful_providers": sum(1 for p in results["providers"] if results["providers"][p]["default"] and results["providers"][p]["default"]["status"] == "success"),
            "failed_providers": sum(1 for p in results["providers"] if results["providers"][p]["default"] and results["providers"][p]["default"]["status"] != "success"),
        }
        
        if include_models:
            total_models = sum(len(results["providers"][p]["models"]) for p in results["providers"])
            successful_models = sum(1 for p in results["providers"] for m in results["providers"][p]["models"] 
                                 if results["providers"][p]["models"][m]["status"] == "success")
            
            summary.update({
                "total_models": total_models,
                "successful_models": successful_models,
                "failed_models": total_models - successful_models
            })
        
        results["summary"] = summary
        self.results = results
        
        return results
    
    def _get_provider_models(self, provider: str) -> List[str]:
        """获取提供商支持的模型列表
        
        Args:
            provider: 提供商名称
            
        Returns:
            模型名称列表
        """
        # 为不同提供商定义模型
        if provider == "openai":
            return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        elif provider == "anthropic":
            return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        elif provider == "deepseek":
            return ["deepseek-chat", "deepseek-coder"]
        elif provider == "siliconflow":
            return ["Pro/deepseek-ai/DeepSeek-R1", "Qwen/Qwen3-235B-A22B"]
        elif provider == "gemini":
            return ["gemini-pro", "gemini-pro-vision"]
        elif provider == "azure":
            return ["gpt-4", "gpt-4o"]
        elif provider == "local":
            return ["Qwen/Qwen2.5-72B-Instruct-AWQ"]
        elif provider == "openrouter":
            return ["anthropic/claude-3-opus", "openai/gpt-4o", "google/gemini-pro"]
        else:
            return []
    
    def test_error_handling(self) -> Dict[str, Any]:
        """测试错误处理
        
        测试在不同错误情况下的错误处理机制
        
        Returns:
            包含测试结果的字典
        """
        results = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        try:
            llm_api = self._import_llm_api()
            
            # 测试1：无效的提供商
            try:
                response = llm_api.query_llm("测试", provider="invalid_provider")
                results["tests"]["invalid_provider"] = {
                    "status": "failed",
                    "reason": "应该抛出异常，但没有"
                }
            except Exception as e:
                results["tests"]["invalid_provider"] = {
                    "status": "success",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            
            # 测试2：无效的模型
            try:
                response = llm_api.query_llm("测试", provider="openai", model="invalid_model")
                results["tests"]["invalid_model"] = {
                    "status": "failed",
                    "reason": "应该抛出异常，但没有"
                }
            except Exception as e:
                results["tests"]["invalid_model"] = {
                    "status": "success",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            
            # 测试3：空提示词
            try:
                response = llm_api.query_llm("", provider="openai")
                results["tests"]["empty_prompt"] = {
                    "status": "failed",
                    "reason": "应该抛出异常，但没有"
                }
            except Exception as e:
                results["tests"]["empty_prompt"] = {
                    "status": "success",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            
            # 测试4：模拟模式
            try:
                original_mode = llm_api.SIMULATION_MODE
                llm_api.SIMULATION_MODE = True
                
                response = llm_api.query_llm("测试", provider="openai")
                
                if "模拟" in response or "simulation" in response.lower():
                    results["tests"]["simulation_mode"] = {
                        "status": "success",
                        "response": response
                    }
                else:
                    results["tests"]["simulation_mode"] = {
                        "status": "failed",
                        "reason": "响应中应包含'模拟'或'simulation'",
                        "response": response
                    }
                
                # 恢复原始模式
                llm_api.SIMULATION_MODE = original_mode
            except Exception as e:
                results["tests"]["simulation_mode"] = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            
            # 测试5：缺少API密钥
            try:
                # 保存原始环境变量
                original_key = os.environ.get("OPENAI_API_KEY")
                
                # 临时删除API密钥
                if "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
                
                # 调用API
                response = llm_api.query_llm("测试", provider="openai")
                
                # 恢复原始环境变量
                if original_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_key
                
                results["tests"]["missing_api_key"] = {
                    "status": "failed",
                    "reason": "应该抛出异常，但没有"
                }
            except Exception as e:
                # 恢复原始环境变量
                if original_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_key
                
                results["tests"]["missing_api_key"] = {
                    "status": "success",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
        except Exception as e:
            logger.error(f"测试错误处理失败: {e}")
            results["error"] = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
        
        return results
    
    def run_all_tests(self, include_models: bool = False, include_error_tests: bool = True) -> Dict[str, Any]:
        """运行所有测试
        
        Args:
            include_models: 是否测试每个提供商的多个模型
            include_error_tests: 是否包含错误处理测试
            
        Returns:
            包含所有测试结果的字典
        """
        results = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 测试所有提供商
        provider_results = self.test_all_providers(include_models)
        results["provider_tests"] = provider_results
        
        # 测试错误处理
        if include_error_tests:
            error_results = self.test_error_handling()
            results["error_handling_tests"] = error_results
        
        # 生成摘要
        summary = {
            "total_providers_tested": provider_results["summary"]["total_providers"],
            "successful_providers": provider_results["summary"]["successful_providers"],
            "failed_providers": provider_results["summary"]["failed_providers"]
        }
        
        if include_models:
            summary.update({
                "total_models_tested": provider_results["summary"]["total_models"],
                "successful_models": provider_results["summary"]["successful_models"],
                "failed_models": provider_results["summary"]["failed_models"]
            })
        
        if include_error_tests:
            total_error_tests = len(error_results["tests"])
            successful_error_tests = sum(1 for test in error_results["tests"] if error_results["tests"][test]["status"] == "success")
            
            summary.update({
                "total_error_tests": total_error_tests,
                "successful_error_tests": successful_error_tests,
                "failed_error_tests": total_error_tests - successful_error_tests
            })
        
        results["summary"] = summary
        
        return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM API测试工具")
    parser.add_argument("--provider", help="要测试的特定提供商")
    parser.add_argument("--model", help="要测试的特定模型")
    parser.add_argument("--include-models", action="store_true", help="测试每个提供商的多个模型")
    parser.add_argument("--error-tests", action="store_true", help="运行错误处理测试")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    
    try:
        tester = LLMAPITest()
        
        if args.provider:
            # 测试特定提供商
            result = tester.test_provider(args.provider, args.model)
            output_data = result
        elif args.error_tests:
            # 只运行错误处理测试
            result = tester.test_error_handling()
            output_data = result
        else:
            # 运行所有测试
            result = tester.run_all_tests(args.include_models)
            output_data = result
        
        # 输出结果
        if args.format == "json":
            output = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            # 文本格式输出
            if args.provider:
                # 单个提供商测试结果
                output = f"LLM API测试结果 - {args.provider} {args.model or '默认模型'}\n"
                output += "=" * 50 + "\n"
                output += f"状态: {result['status']}\n"
                
                if result['status'] == "success":
                    output += f"响应: {result['response'][:200]}...\n"
                    output += f"耗时: {result['elapsed_time']:.2f}秒\n"
                else:
                    output += f"错误类型: {result['error']['type']}\n"
                    output += f"错误消息: {result['error']['message']}\n"
            elif args.error_tests:
                # 错误处理测试结果
                output = "LLM API错误处理测试结果\n"
                output += "=" * 50 + "\n"
                
                for test_name, test_result in result["tests"].items():
                    output += f"{test_name}:\n"
                    output += f"  状态: {test_result['status']}\n"
                    
                    if test_result['status'] == "success":
                        if "response" in test_result:
                            output += f"  响应: {test_result['response'][:100]}...\n"
                        elif "error_type" in test_result:
                            output += f"  错误类型: {test_result['error_type']}\n"
                            output += f"  错误消息: {test_result['error_message']}\n"
                    else:
                        output += f"  失败原因: {test_result.get('reason', '未知')}\n"
                    
                    output += "\n"
            else:
                # 所有测试结果
                output = "LLM API综合测试结果\n"
                output += "=" * 50 + "\n"
                
                # 摘要
                output += "摘要:\n"
                output += f"测试的提供商: {result['summary']['total_providers_tested']}\n"
                output += f"成功的提供商: {result['summary']['successful_providers']}\n"
                output += f"失败的提供商: {result['summary']['failed_providers']}\n"
                
                if args.include_models:
                    output += f"测试的模型: {result['summary']['total_models_tested']}\n"
                    output += f"成功的模型: {result['summary']['successful_models']}\n"
                    output += f"失败的模型: {result['summary']['failed_models']}\n"
                
                output += "\n提供商详细结果:\n"
                
                for provider, provider_result in result['provider_tests']['providers'].items():
                    output += f"{provider}:\n"
                    
                    # 默认模型
                    default_result = provider_result['default']
                    if default_result:
                        output += f"  默认模型: {default_result['status']}"
                        if default_result['status'] == "success":
                            output += f", 耗时: {default_result['elapsed_time']:.2f}秒\n"
                        else:
                            output += f", 错误: {default_result.get('error', {}).get('message', '未知')}\n"
                    
                    # 特定模型
                    if args.include_models and provider_result['models']:
                        output += "  模型:\n"
                        for model, model_result in provider_result['models'].items():
                            output += f"    {model}: {model_result['status']}"
                            if model_result['status'] == "success":
                                output += f", 耗时: {model_result['elapsed_time']:.2f}秒\n"
                            else:
                                output += f", 错误: {model_result.get('error', {}).get('message', '未知')}\n"
                    
                    output += "\n"
        
        # 输出结果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"测试结果已保存到: {args.output}")
        else:
            print(output)
    
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        traceback.print_exc()
        sys.exit(1) 