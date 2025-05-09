"""跨平台测试脚本

用于验证系统在不同平台（Windows、macOS、Linux）上的兼容性。
"""

import os
import sys
import json
import platform
import logging
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from . import error_handler
    from .error_handler import ErrorCategory, ErrorSeverity, error_handler
    from .system_diagnostics import system_diagnostics
except ImportError:
    # 当作为独立脚本运行时
    error_handler = None
    system_diagnostics = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cross_platform_test")

class CrossPlatformTest:
    """跨平台测试类，用于验证系统在不同平台上的兼容性"""
    
    def __init__(self):
        """初始化跨平台测试"""
        self.system = platform.system()
        self.results = {}
    
    def get_platform_info(self) -> Dict[str, Any]:
        """获取平台信息
        
        Returns:
            包含平台信息的字典
        """
        return {
            "system": self.system,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "is_64bit": sys.maxsize > 2**32
        }
    
    def test_path_handling(self) -> Dict[str, Any]:
        """测试路径处理
        
        测试系统对不同操作系统路径格式的处理
        
        Returns:
            包含测试结果的字典
        """
        results = {
            "tests": {},
            "summary": {"passed": 0, "failed": 0}
        }
        
        # 测试1：创建临时目录
        try:
            temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
            results["tests"]["create_temp_dir"] = {"status": "passed", "path": temp_dir}
            results["summary"]["passed"] += 1
        except Exception as e:
            results["tests"]["create_temp_dir"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试2：在临时目录中创建文件
        try:
            if "create_temp_dir" in results["tests"] and results["tests"]["create_temp_dir"]["status"] == "passed":
                temp_dir = results["tests"]["create_temp_dir"]["path"]
                # 根据不同平台使用不同的路径格式
                if self.system == "Windows":
                    file_path = os.path.join(temp_dir, "test_file.txt")
                else:
                    file_path = f"{temp_dir}/test_file.txt"
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("测试内容")
                
                results["tests"]["create_file"] = {"status": "passed", "path": file_path}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["create_file"] = {"status": "skipped", "reason": "创建临时目录失败"}
        except Exception as e:
            results["tests"]["create_file"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试3：使用pathlib创建目录
        try:
            if "create_temp_dir" in results["tests"] and results["tests"]["create_temp_dir"]["status"] == "passed":
                temp_dir = results["tests"]["create_temp_dir"]["path"]
                subdir_path = Path(temp_dir) / "subdir"
                subdir_path.mkdir(exist_ok=True)
                
                results["tests"]["create_dir_pathlib"] = {"status": "passed", "path": str(subdir_path)}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["create_dir_pathlib"] = {"status": "skipped", "reason": "创建临时目录失败"}
        except Exception as e:
            results["tests"]["create_dir_pathlib"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试4：处理长路径（Windows特有问题）
        try:
            if self.system == "Windows":
                if "create_temp_dir" in results["tests"] and results["tests"]["create_temp_dir"]["status"] == "passed":
                    temp_dir = results["tests"]["create_temp_dir"]["path"]
                    # 创建一个长路径（超过260个字符，Windows的默认限制）
                    long_dir_name = "a" * 50
                    long_path = Path(temp_dir)
                    for i in range(5):  # 创建嵌套目录以增加路径长度
                        long_path = long_path / f"{long_dir_name}_{i}"
                    
                    try:
                        # 尝试创建长路径目录
                        long_path.mkdir(parents=True, exist_ok=True)
                        results["tests"]["long_path"] = {"status": "passed", "path": str(long_path)}
                        results["summary"]["passed"] += 1
                    except Exception as long_path_error:
                        # 如果创建失败，尝试使用UNC路径格式
                        try:
                            unc_path = "\\\\?\\" + str(long_path.resolve())
                            os.makedirs(unc_path, exist_ok=True)
                            results["tests"]["long_path"] = {
                                "status": "passed", 
                                "path": unc_path,
                                "note": "使用UNC路径格式"
                            }
                            results["summary"]["passed"] += 1
                        except Exception as unc_error:
                            results["tests"]["long_path"] = {
                                "status": "failed", 
                                "error": f"标准路径错误: {str(long_path_error)}, UNC路径错误: {str(unc_error)}"
                            }
                            results["summary"]["failed"] += 1
                else:
                    results["tests"]["long_path"] = {"status": "skipped", "reason": "创建临时目录失败"}
            else:
                results["tests"]["long_path"] = {"status": "skipped", "reason": f"非Windows系统: {self.system}"}
        except Exception as e:
            results["tests"]["long_path"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试5：清理临时文件
        try:
            if "create_temp_dir" in results["tests"] and results["tests"]["create_temp_dir"]["status"] == "passed":
                temp_dir = results["tests"]["create_temp_dir"]["path"]
                # 递归删除临时目录
                if self.system == "Windows":
                    # Windows可能需要特殊处理以删除只读文件
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    # Unix系统
                    import shutil
                    shutil.rmtree(temp_dir)
                
                results["tests"]["cleanup"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["cleanup"] = {"status": "skipped", "reason": "创建临时目录失败"}
        except Exception as e:
            results["tests"]["cleanup"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        return results
    
    def test_file_encoding(self) -> Dict[str, Any]:
        """测试文件编码
        
        测试系统对不同文件编码的处理
        
        Returns:
            包含测试结果的字典
        """
        results = {
            "tests": {},
            "summary": {"passed": 0, "failed": 0}
        }
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="mcp_encoding_test_")
        
        # 测试1：UTF-8编码
        try:
            file_path = os.path.join(temp_dir, "utf8.txt")
            content = "UTF-8测试内容：你好，世界！"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            with open(file_path, "r", encoding="utf-8") as f:
                read_content = f.read()
            
            if read_content == content:
                results["tests"]["utf8"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["utf8"] = {
                    "status": "failed", 
                    "error": "内容不匹配",
                    "expected": content,
                    "actual": read_content
                }
                results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"]["utf8"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试2：GBK编码（中文Windows常用）
        try:
            file_path = os.path.join(temp_dir, "gbk.txt")
            content = "GBK测试内容：你好，世界！"
            
            with open(file_path, "w", encoding="gbk") as f:
                f.write(content)
            
            with open(file_path, "r", encoding="gbk") as f:
                read_content = f.read()
            
            if read_content == content:
                results["tests"]["gbk"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["gbk"] = {
                    "status": "failed", 
                    "error": "内容不匹配",
                    "expected": content,
                    "actual": read_content
                }
                results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"]["gbk"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试3：二进制文件
        try:
            file_path = os.path.join(temp_dir, "binary.dat")
            content = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            with open(file_path, "rb") as f:
                read_content = f.read()
            
            if read_content == content:
                results["tests"]["binary"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["binary"] = {
                    "status": "failed", 
                    "error": "内容不匹配",
                    "expected": list(content),
                    "actual": list(read_content)
                }
                results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"]["binary"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试4：含有特殊字符的文件名
        try:
            special_filename = "特殊字符 !@#$%^&()_+-={}[];',..txt"
            file_path = os.path.join(temp_dir, special_filename)
            content = "特殊文件名测试"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            with open(file_path, "r", encoding="utf-8") as f:
                read_content = f.read()
            
            if read_content == content:
                results["tests"]["special_filename"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["special_filename"] = {
                    "status": "failed", 
                    "error": "内容不匹配",
                    "expected": content,
                    "actual": read_content
                }
                results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"]["special_filename"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 清理临时目录
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        
        return results
    
    def test_environment_variables(self) -> Dict[str, Any]:
        """测试环境变量
        
        测试系统对环境变量的处理
        
        Returns:
            包含测试结果的字典
        """
        results = {
            "tests": {},
            "summary": {"passed": 0, "failed": 0}
        }
        
        # 测试1：设置和获取环境变量
        try:
            var_name = "MCP_TEST_VAR"
            var_value = "test_value"
            
            os.environ[var_name] = var_value
            read_value = os.environ.get(var_name)
            
            if read_value == var_value:
                results["tests"]["set_get_env"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["set_get_env"] = {
                    "status": "failed", 
                    "error": "值不匹配",
                    "expected": var_value,
                    "actual": read_value
                }
                results["summary"]["failed"] += 1
            
            # 清理
            del os.environ[var_name]
        except Exception as e:
            results["tests"]["set_get_env"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试2：环境变量区分大小写
        try:
            # Windows上环境变量不区分大小写，其他平台区分
            var_name_lower = "mcp_test_case"
            var_name_upper = "MCP_TEST_CASE"
            var_value_lower = "lower_value"
            var_value_upper = "upper_value"
            
            os.environ[var_name_lower] = var_value_lower
            os.environ[var_name_upper] = var_value_upper
            
            read_lower = os.environ.get(var_name_lower)
            read_upper = os.environ.get(var_name_upper)
            
            if self.system == "Windows":
                # Windows不区分大小写，后设置的会覆盖先设置的
                expected_same = True
                reason = "Windows不区分环境变量大小写"
            else:
                # Unix区分大小写
                expected_same = False
                reason = "Unix区分环境变量大小写"
            
            actual_same = read_lower == read_upper
            
            if actual_same == expected_same:
                results["tests"]["env_case_sensitivity"] = {
                    "status": "passed",
                    "note": reason,
                    "case_sensitive": not expected_same
                }
                results["summary"]["passed"] += 1
            else:
                results["tests"]["env_case_sensitivity"] = {
                    "status": "failed", 
                    "error": f"预期{'' if expected_same else '不'}相同，但实际{'相同' if actual_same else '不同'}",
                    "expected_same": expected_same,
                    "actual_same": actual_same,
                    "lower_value": read_lower,
                    "upper_value": read_upper
                }
                results["summary"]["failed"] += 1
            
            # 清理
            del os.environ[var_name_lower]
            del os.environ[var_name_upper]
        except Exception as e:
            results["tests"]["env_case_sensitivity"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试3：unicode环境变量
        try:
            var_name = "MCP_TEST_UNICODE"
            var_value = "Unicode值：你好，世界！"
            
            os.environ[var_name] = var_value
            read_value = os.environ.get(var_name)
            
            if read_value == var_value:
                results["tests"]["unicode_env"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["unicode_env"] = {
                    "status": "failed", 
                    "error": "值不匹配",
                    "expected": var_value,
                    "actual": read_value
                }
                results["summary"]["failed"] += 1
            
            # 清理
            del os.environ[var_name]
        except Exception as e:
            results["tests"]["unicode_env"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        return results
    
    def test_process_management(self) -> Dict[str, Any]:
        """测试进程管理
        
        测试系统对进程的创建和管理
        
        Returns:
            包含测试结果的字典
        """
        results = {
            "tests": {},
            "summary": {"passed": 0, "failed": 0}
        }
        
        # 测试1：使用subprocess运行命令
        try:
            import subprocess
            
            # 根据平台选择合适的命令
            if self.system == "Windows":
                cmd = ["cmd", "/c", "echo", "Hello World"]
            else:
                cmd = ["echo", "Hello World"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                results["tests"]["subprocess_run"] = {"status": "passed", "output": result.stdout.strip()}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["subprocess_run"] = {
                    "status": "failed", 
                    "error": f"返回码非零: {result.returncode}",
                    "stderr": result.stderr
                }
                results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"]["subprocess_run"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        # 测试2：创建子进程并通信
        try:
            import subprocess
            import sys
            
            # 编写一个简单的Python脚本
            script = """
import sys
print("子进程输出")
sys.stdout.flush()
# 从标准输入读取
line = sys.stdin.readline().strip()
print(f"收到输入: {line}")
sys.exit(0)
"""
            
            # 创建临时脚本文件
            temp_dir = tempfile.mkdtemp(prefix="mcp_process_test_")
            script_path = os.path.join(temp_dir, "test_script.py")
            
            with open(script_path, "w") as f:
                f.write(script)
            
            # 运行脚本并通信
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待并读取第一行输出
            first_line = process.stdout.readline().strip()
            
            # 发送输入
            process.stdin.write("测试输入\n")
            process.stdin.flush()
            
            # 读取响应
            second_line = process.stdout.readline().strip()
            
            # 等待进程结束
            return_code = process.wait()
            
            if return_code == 0 and first_line == "子进程输出" and second_line == "收到输入: 测试输入":
                results["tests"]["process_communication"] = {"status": "passed"}
                results["summary"]["passed"] += 1
            else:
                results["tests"]["process_communication"] = {
                    "status": "failed", 
                    "error": "通信失败",
                    "return_code": return_code,
                    "first_line": first_line,
                    "second_line": second_line
                }
                results["summary"]["failed"] += 1
            
            # 清理
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            results["tests"]["process_communication"] = {"status": "failed", "error": str(e)}
            results["summary"]["failed"] += 1
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试
        
        Returns:
            包含所有测试结果的字典
        """
        self.results = {
            "platform_info": self.get_platform_info(),
            "path_handling": self.test_path_handling(),
            "file_encoding": self.test_file_encoding(),
            "environment_variables": self.test_environment_variables(),
            "process_management": self.test_process_management()
        }
        
        # 生成总结
        total_passed = sum(self.results[category]["summary"]["passed"] for category in self.results if category != "platform_info" and "summary" in self.results[category])
        total_failed = sum(self.results[category]["summary"]["failed"] for category in self.results if category != "platform_info" and "summary" in self.results[category])
        total_tests = total_passed + total_failed
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": f"{(total_passed / total_tests * 100) if total_tests > 0 else 0:.2f}%",
            "status": "success" if total_failed == 0 else "failed",
            "system": self.system
        }
        
        return self.results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="跨平台兼容性测试")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    
    tester = CrossPlatformTest()
    results = tester.run_all_tests()
    
    if args.format == "json":
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