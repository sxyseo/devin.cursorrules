"""系统诊断工具

提供系统状态检查和环境诊断功能。
"""

import os
import sys
import json
import time
import platform
import socket
import psutil
import logging
import importlib
import traceback
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    from . import error_handler
    from .error_handler import ErrorCategory, ErrorSeverity, error_handler
except ImportError:
    # 当作为独立脚本运行时
    error_handler = None
    ErrorCategory = None
    ErrorSeverity = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("system_diagnostics")

class SystemDiagnostics:
    """系统诊断工具类，用于检查系统状态和环境"""
    
    def __init__(self):
        """初始化系统诊断工具"""
        pass
    
    def check_python_environment(self) -> Dict[str, Any]:
        """检查Python环境
        
        Returns:
            包含Python环境信息的字典
        """
        try:
            env_info = {
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "platform": platform.platform(),
                "system": platform.system(),
                "processor": platform.processor(),
                "path": sys.path,
                "executable": sys.executable,
                "environment_variables": {
                    k: v for k, v in os.environ.items() 
                    if k.startswith(("PYTHON", "PATH", "VIRTUAL_ENV", "CONDA"))
                },
            }
            
            # 检查虚拟环境
            env_info["virtual_env"] = os.environ.get("VIRTUAL_ENV")
            env_info["in_virtual_env"] = env_info["virtual_env"] is not None
            
            return env_info
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, 
                    {"component": "check_python_environment"}
                )
            logger.error(f"检查Python环境失败: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def check_dependencies(self, required_packages: List[str] = None) -> Dict[str, Any]:
        """检查依赖项
        
        Args:
            required_packages: 要检查的包列表，如果为None则检查预定义的关键包
            
        Returns:
            包含依赖项检查结果的字典
        """
        try:
            if required_packages is None:
                required_packages = [
                    "fastapi", "uvicorn", "websockets", "httpx", 
                    "openai", "anthropic", "tiktoken", "psutil",
                    "numpy", "pandas", "matplotlib", "seaborn",
                    "scikit-learn", "tensorflow", "torch", "transformers",
                    "pytest", "sphinx", "black", "flake8", "mypy"
                ]
            
            dependency_info = {}
            for package in required_packages:
                try:
                    module = importlib.import_module(package)
                    version = getattr(module, "__version__", "未知")
                    dependency_info[package] = {
                        "installed": True,
                        "version": version
                    }
                except ImportError:
                    dependency_info[package] = {
                        "installed": False,
                        "version": None
                    }
            
            return dependency_info
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, 
                    {"component": "check_dependencies"}
                )
            logger.error(f"检查依赖项失败: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源
        
        Returns:
            包含系统资源信息的字典
        """
        try:
            system_info = {}
            
            # CPU信息
            system_info["cpu"] = {
                "count_logical": psutil.cpu_count(logical=True),
                "count_physical": psutil.cpu_count(logical=False),
                "usage_percent": psutil.cpu_percent(interval=1),
                "per_cpu_percent": psutil.cpu_percent(interval=1, percpu=True)
            }
            
            # 内存信息
            memory = psutil.virtual_memory()
            system_info["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            }
            
            # 磁盘信息
            disk = psutil.disk_usage('/')
            system_info["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
            
            # 网络信息
            try:
                net_io = psutil.net_io_counters()
                system_info["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "hostname": socket.gethostname(),
                    "ip_address": socket.gethostbyname(socket.gethostname())
                }
            except (socket.gaierror, psutil.Error):
                system_info["network"] = {"error": "无法获取网络信息"}
            
            return system_info
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, 
                    {"component": "check_system_resources"}
                )
            logger.error(f"检查系统资源失败: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def check_network_connectivity(self, targets: List[str] = None) -> Dict[str, Any]:
        """检查网络连接性
        
        Args:
            targets: 要检查的目标列表，格式为"host:port"
            
        Returns:
            包含网络连接性检查结果的字典
        """
        try:
            if targets is None:
                targets = [
                    "api.openai.com:443",
                    "claude-api.anthropic.com:443",
                    "api.siliconflow.com:443",
                    "api.deepseek.com:443",
                    "api.gemini.ai:443",
                    "github.com:443",
                    "pypi.org:443",
                    "google.com:443"
                ]
            
            results = {}
            for target in targets:
                try:
                    host, port = target.split(":")
                    start_time = time.time()
                    
                    # 创建套接字
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    
                    # 尝试连接
                    result = sock.connect_ex((host, int(port)))
                    elapsed = time.time() - start_time
                    
                    # 关闭套接字
                    sock.close()
                    
                    results[target] = {
                        "success": result == 0,
                        "latency": elapsed if result == 0 else None,
                        "error_code": result
                    }
                except Exception as e:
                    results[target] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return results
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, 
                    {"component": "check_network_connectivity"}
                )
            logger.error(f"检查网络连接性失败: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def check_file_system(self, paths: List[str] = None) -> Dict[str, Any]:
        """检查文件系统
        
        Args:
            paths: 要检查的路径列表
            
        Returns:
            包含文件系统检查结果的字典
        """
        try:
            if paths is None:
                # 默认检查当前目录、临时目录和用户主目录
                paths = [
                    ".",
                    os.path.expanduser("~"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    os.environ.get("TEMP", "/tmp")
                ]
            
            results = {}
            for path_str in paths:
                path = Path(path_str).resolve()
                try:
                    stats = os.stat(path)
                    results[str(path)] = {
                        "exists": True,
                        "is_dir": os.path.isdir(path),
                        "is_file": os.path.isfile(path),
                        "permissions": {
                            "read": os.access(path, os.R_OK),
                            "write": os.access(path, os.W_OK),
                            "execute": os.access(path, os.X_OK)
                        },
                        "size": stats.st_size,
                        "last_modified": time.ctime(stats.st_mtime)
                    }
                except FileNotFoundError:
                    results[str(path)] = {
                        "exists": False
                    }
                except PermissionError:
                    results[str(path)] = {
                        "exists": True,
                        "permissions": {
                            "read": False,
                            "write": False,
                            "execute": False
                        },
                        "error": "权限被拒绝"
                    }
                except Exception as e:
                    results[str(path)] = {
                        "error": str(e)
                    }
            
            return results
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.RESOURCE, ErrorSeverity.MEDIUM, 
                    {"component": "check_file_system"}
                )
            logger.error(f"检查文件系统失败: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def check_environment_variables(self, prefixes: List[str] = None) -> Dict[str, str]:
        """检查环境变量
        
        Args:
            prefixes: 要检查的环境变量前缀列表
            
        Returns:
            包含环境变量检查结果的字典
        """
        try:
            if prefixes is None:
                prefixes = [
                    "OPENAI", "ANTHROPIC", "DEEPSEEK", "SILICONFLOW", "GOOGLE", 
                    "PYTHON", "PATH", "HOME", "USER", "TEMP", "TMP"
                ]
            
            env_vars = {}
            for key, value in os.environ.items():
                # 如果环境变量以任何指定前缀开头，或者前缀为空（检查所有变量），则包含它
                if any(key.startswith(prefix) for prefix in prefixes):
                    # 对于敏感变量，只显示前4个字符和长度
                    if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower() or "password" in key.lower():
                        if len(value) > 4:
                            env_vars[key] = f"{value[:4]}...（长度：{len(value)}）"
                        else:
                            env_vars[key] = "（已设置）"
                    else:
                        env_vars[key] = value
            
            return env_vars
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    e, ErrorCategory.SYSTEM, ErrorSeverity.LOW, 
                    {"component": "check_environment_variables"}
                )
            logger.error(f"检查环境变量失败: {e}")
            return {"error": str(e)}
    
    def run_full_diagnostics(self) -> Dict[str, Any]:
        """运行完整的系统诊断
        
        Returns:
            包含完整诊断结果的字典
        """
        results = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "python_environment": self.check_python_environment(),
            "dependencies": self.check_dependencies(),
            "system_resources": self.check_system_resources(),
            "network_connectivity": self.check_network_connectivity(),
            "file_system": self.check_file_system(),
            "environment_variables": self.check_environment_variables()
        }
        
        # 生成摘要
        issues = []
        
        # 检查依赖项问题
        missing_deps = [
            pkg for pkg, info in results["dependencies"].items() 
            if isinstance(info, dict) and info.get("installed") is False
        ]
        if missing_deps:
            issues.append(f"缺少依赖项: {', '.join(missing_deps)}")
        
        # 检查网络连接问题
        failed_connections = [
            target for target, info in results["network_connectivity"].items() 
            if isinstance(info, dict) and info.get("success") is False
        ]
        if failed_connections:
            issues.append(f"网络连接失败: {', '.join(failed_connections)}")
        
        # 检查资源问题
        if results["system_resources"].get("memory", {}).get("percent", 0) > 90:
            issues.append("内存使用率超过90%")
        
        if results["system_resources"].get("disk", {}).get("percent", 0) > 90:
            issues.append("磁盘使用率超过90%")
        
        # 检查文件系统问题
        permission_issues = [
            path for path, info in results["file_system"].items() 
            if isinstance(info, dict) and info.get("permissions", {}).get("write") is False
        ]
        if permission_issues:
            issues.append(f"文件权限问题: {', '.join(permission_issues)}")
        
        results["summary"] = {
            "issues_count": len(issues),
            "issues": issues,
            "status": "healthy" if len(issues) == 0 else "issues_detected"
        }
        
        return results

# 创建全局实例
system_diagnostics = SystemDiagnostics()

if __name__ == "__main__":
    # 当作为脚本运行时，执行完整诊断并打印结果
    import argparse
    
    parser = argparse.ArgumentParser(description="系统诊断工具")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    
    diagnostics = SystemDiagnostics()
    results = diagnostics.run_full_diagnostics()
    
    if args.format == "json":
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