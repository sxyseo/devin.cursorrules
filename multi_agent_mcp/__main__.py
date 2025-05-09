#!/usr/bin/env python3
"""
多智能体MCP服务器主程序入口点

允许包作为脚本运行，例如：
    python -m multi_agent_mcp [选项]
"""

import sys
import argparse
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("multi_agent_mcp")

def main():
    """主程序入口函数"""
    # 创建命令行解析器
    parser = argparse.ArgumentParser(
        description="多智能体MCP服务器和工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  启动MCP服务器:
    python -m multi_agent_mcp server --host 127.0.0.1 --port 8000 --simulation
    
  运行跨平台测试:
    python -m multi_agent_mcp test cross-platform
    
  测试LLM API:
    python -m multi_agent_mcp test llm-api --provider openai
    
  运行系统诊断:
    python -m multi_agent_mcp diagnose
"""
    )
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 服务器命令
    server_parser = subparsers.add_parser("server", help="启动MCP服务器")
    server_parser.add_argument("--host", default="127.0.0.1", help="监听主机地址")
    server_parser.add_argument("--port", type=int, default=8000, help="监听端口")
    server_parser.add_argument("--simulation", action="store_true", help="启用模拟模式")
    server_parser.add_argument(
        "--protocol", 
        default="all", 
        choices=["all", "http", "ws", "sse", "simple"], 
        help="指定启动的协议，simple表示使用SimpleHTTPServer"
    )
    
    # 测试命令
    test_parser = subparsers.add_parser("test", help="运行测试")
    test_subparsers = test_parser.add_subparsers(dest="test_type", help="测试类型")
    
    # 跨平台测试
    cp_test_parser = test_subparsers.add_parser("cross-platform", help="运行跨平台测试")
    cp_test_parser.add_argument("--output", help="输出文件路径")
    cp_test_parser.add_argument(
        "--format", 
        choices=["json", "text"], 
        default="text", 
        help="输出格式"
    )
    
    # LLM API测试
    llm_test_parser = test_subparsers.add_parser("llm-api", help="测试LLM API")
    llm_test_parser.add_argument("--provider", help="要测试的特定提供商")
    llm_test_parser.add_argument("--model", help="要测试的特定模型")
    llm_test_parser.add_argument("--include-models", action="store_true", help="测试每个提供商的多个模型")
    llm_test_parser.add_argument("--error-tests", action="store_true", help="运行错误处理测试")
    llm_test_parser.add_argument("--output", help="输出文件路径")
    llm_test_parser.add_argument(
        "--format", 
        choices=["json", "text"], 
        default="text", 
        help="输出格式"
    )
    
    # 系统诊断命令
    diag_parser = subparsers.add_parser("diagnose", help="运行系统诊断")
    diag_parser.add_argument("--output", help="输出文件路径")
    diag_parser.add_argument(
        "--format", 
        choices=["json", "text"], 
        default="text", 
        help="输出格式"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 处理命令
    if args.command == "server":
        # 导入server模块并启动服务器
        try:
            from .server import main as server_main
            # 直接传递参数给server_main函数
            server_main(
                host=args.host,
                port=args.port,
                simulation=args.simulation,
                protocol=args.protocol
            )
        except ImportError as e:
            logger.error(f"导入server模块失败: {e}")
            sys.exit(1)
    
    elif args.command == "test":
        if args.test_type == "cross-platform":
            # 运行跨平台测试
            try:
                from .tools.cross_platform_test import CrossPlatformTest
                
                tester = CrossPlatformTest()
                results = tester.run_all_tests()
                
                if args.format == "json":
                    import json
                    output = json.dumps(results, indent=2, ensure_ascii=False)
                else:
                    # 文本格式
                    output = "跨平台兼容性测试报告\n"
                    output += "=" * 50 + "\n"
                    output += f"系统: {results['platform_info']['system']}\n"
                    output += f"Python版本: {results['platform_info']['python_version']}\n\n"
                    
                    output += "测试结果汇总:\n"
                    output += f"总测试数: {results['summary']['total_tests']}\n"
                    output += f"通过: {results['summary']['passed']}\n"
                    output += f"失败: {results['summary']['failed']}\n"
                    output += f"通过率: {results['summary']['pass_rate']}\n"
                    output += f"状态: {results['summary']['status']}\n\n"
                    
                    for category in ["path_handling", "file_encoding", "environment_variables", "process_management"]:
                        output += f"{category.replace('_', ' ').title()}:\n"
                        output += f"  通过: {results[category]['summary']['passed']}\n"
                        output += f"  失败: {results[category]['summary']['failed']}\n"
                        output += "  详细测试:\n"
                        
                        for test_name, test_result in results[category]["tests"].items():
                            status = test_result["status"]
                            output += f"    {test_name}: {status}"
                            if status == "failed" and "error" in test_result:
                                output += f" - {test_result['error']}"
                            output += "\n"
                        
                        output += "\n"
                
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output)
                    print(f"测试结果已保存到: {args.output}")
                else:
                    print(output)
            
            except ImportError as e:
                logger.error(f"导入跨平台测试模块失败: {e}")
                sys.exit(1)
        
        elif args.test_type == "llm-api":
            # 运行LLM API测试
            try:
                from .tools.llm_api_test import LLMAPITest
                
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
                    import json
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
                
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output)
                    print(f"测试结果已保存到: {args.output}")
                else:
                    print(output)
            
            except ImportError as e:
                logger.error(f"导入LLM API测试模块失败: {e}")
                sys.exit(1)
        
        else:
            logger.error(f"未知的测试类型: {args.test_type}")
            parser.print_help()
            sys.exit(1)
    
    elif args.command == "diagnose":
        # 运行系统诊断
        try:
            from .tools.system_diagnostics import SystemDiagnostics
            
            diagnostics = SystemDiagnostics()
            results = diagnostics.run_full_diagnostics()
            
            if args.format == "json":
                import json
                output = json.dumps(results, indent=2, ensure_ascii=False)
            else:
                # 文本格式
                output = "系统诊断报告\n"
                output += "=" * 50 + "\n"
                output += f"时间: {results['datetime']}\n"
                output += f"Python版本: {results['python_environment']['python_version']}\n"
                output += f"系统: {results['python_environment']['system']}\n"
                output += f"平台: {results['python_environment']['platform']}\n\n"
                
                output += "系统资源:\n"
                output += f"  CPU使用率: {results['system_resources']['cpu']['usage_percent']}%\n"
                output += f"  内存使用率: {results['system_resources']['memory']['percent']}%\n"
                output += f"  磁盘使用率: {results['system_resources']['disk']['percent']}%\n\n"
                
                output += "网络连接:\n"
                for target, info in results['network_connectivity'].items():
                    if isinstance(info, dict):
                        status = "成功" if info.get("success") else "失败"
                        latency = f", 延迟: {info.get('latency'):.3f}s" if info.get("latency") is not None else ""
                        output += f"  {target}: {status}{latency}\n"
                
                output += "\n摘要:\n"
                output += f"  状态: {results['summary']['status']}\n"
                output += f"  问题数量: {results['summary']['issues_count']}\n"
                
                if results['summary']['issues']:
                    output += "  问题列表:\n"
                    for issue in results['summary']['issues']:
                        output += f"    - {issue}\n"
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"诊断结果已保存到: {args.output}")
            else:
                print(output)
        
        except ImportError as e:
            logger.error(f"导入系统诊断模块失败: {e}")
            sys.exit(1)
    
    else:
        # 如果没有指定命令，显示帮助
        parser.print_help()

if __name__ == "__main__":
    main() 