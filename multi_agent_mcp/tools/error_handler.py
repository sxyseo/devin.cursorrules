"""错误处理模块

提供全面的错误分类、诊断和恢复机制。
"""

import os
import sys
import time
import enum
import json
import logging
import inspect
import platform
import traceback
import functools
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("error_handler")

# 定义错误类别
class ErrorCategory(enum.Enum):
    NETWORK = "network"  # 网络相关错误
    API = "api"          # API调用错误
    RESOURCE = "resource"  # 资源访问错误
    CONFIG = "config"    # 配置错误
    PERMISSION = "permission"  # 权限错误
    DATA = "data"        # 数据处理错误
    LOGIC = "logic"      # 业务逻辑错误
    SYSTEM = "system"    # 系统级错误
    SERVER = "server"    # 服务器错误
    CLIENT = "client"    # 客户端错误
    APPLICATION = "application"  # 应用程序错误
    UNKNOWN = "unknown"  # 未知错误
    
    @classmethod
    def from_string(cls, category_str: str) -> 'ErrorCategory':
        """从字符串获取错误类别"""
        try:
            return cls(category_str.lower())
        except ValueError:
            return cls.UNKNOWN

# 定义错误严重性
class ErrorSeverity(enum.Enum):
    LOW = "low"          # 低严重性，不影响系统运行
    MEDIUM = "medium"    # 中等严重性，部分功能可能受影响
    HIGH = "high"        # 高严重性，主要功能受影响
    CRITICAL = "critical"  # 严重错误，系统无法正常运行
    
    @classmethod
    def from_string(cls, severity_str: str) -> 'ErrorSeverity':
        """从字符串获取错误严重性"""
        try:
            return cls(severity_str.lower())
        except ValueError:
            return cls.MEDIUM

# 错误模式库
ERROR_PATTERNS = {
    # 网络错误模式
    "connection_refused": {
        "patterns": ["connection refused", "failed to establish connection", "cannot connect to"],
        "category": ErrorCategory.NETWORK,
        "severity": ErrorSeverity.HIGH,
        "recovery": lambda: time.sleep(5)  # 简单的重试策略
    },
    "timeout": {
        "patterns": ["timeout", "timed out", "deadline exceeded"],
        "category": ErrorCategory.NETWORK,
        "severity": ErrorSeverity.MEDIUM,
        "recovery": lambda: time.sleep(2)  # 短暂延迟后重试
    },
    "dns_resolution": {
        "patterns": ["name resolution", "unknown host", "could not resolve"],
        "category": ErrorCategory.NETWORK,
        "severity": ErrorSeverity.HIGH,
        "recovery": None  # 需要手动解决
    },
    
    # API错误模式
    "rate_limit": {
        "patterns": ["rate limit", "too many requests", "quota exceeded"],
        "category": ErrorCategory.API,
        "severity": ErrorSeverity.MEDIUM,
        "recovery": lambda: time.sleep(60)  # 等待一分钟
    },
    "authentication": {
        "patterns": ["authentication failed", "invalid token", "unauthorized", "auth"],
        "category": ErrorCategory.API,
        "severity": ErrorSeverity.HIGH,
        "recovery": None  # 需要手动解决
    },
    "api_unavailable": {
        "patterns": ["service unavailable", "api down", "503"],
        "category": ErrorCategory.API,
        "severity": ErrorSeverity.HIGH,
        "recovery": lambda: time.sleep(30)  # 短暂延迟后重试
    },
    
    # 资源错误模式
    "file_not_found": {
        "patterns": ["file not found", "no such file", "not exist"],
        "category": ErrorCategory.RESOURCE,
        "severity": ErrorSeverity.MEDIUM,
        "recovery": None  # 需要手动解决
    },
    "permission_denied": {
        "patterns": ["permission denied", "access denied", "forbidden"],
        "category": ErrorCategory.PERMISSION,
        "severity": ErrorSeverity.HIGH,
        "recovery": None  # 需要手动解决
    },
    "disk_full": {
        "patterns": ["disk full", "no space left", "insufficient storage"],
        "category": ErrorCategory.RESOURCE,
        "severity": ErrorSeverity.CRITICAL,
        "recovery": None  # 需要手动解决
    }
}

class ErrorHandler:
    """错误处理器类，提供错误分类、诊断和恢复机制"""
    
    def __init__(self, log_dir: str = None):
        """初始化错误处理器
        
        Args:
            log_dir: 错误日志存储目录，默认为项目根目录下的error_logs
        """
        # 设置错误日志目录
        if log_dir is None:
            # 获取当前模块所在目录
            current_dir = Path(__file__).parent
            # 设置默认日志目录为项目根目录下的error_logs
            self.log_dir = current_dir.parent / "error_logs"
        else:
            self.log_dir = Path(log_dir)
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 设置错误日志文件处理器
        self.log_file = self.log_dir / f"error_log_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"错误处理器初始化完成，日志目录：{self.log_dir}")
    
    def handle_error(self, 
                   error: Exception, 
                   category: Union[ErrorCategory, str] = None, 
                   severity: Union[ErrorSeverity, str] = None, 
                   context: dict = None,
                   recovery_attempts: int = 0) -> dict:
        """处理错误
        
        Args:
            error: 异常对象
            category: 错误类别，可以是ErrorCategory枚举或字符串
            severity: 错误严重性，可以是ErrorSeverity枚举或字符串
            context: 错误上下文信息
            recovery_attempts: 已尝试恢复的次数
            
        Returns:
            包含错误处理结果的字典
        """
        # 确保context是字典
        if context is None:
            context = {}
        
        # 获取调用栈信息
        stack_trace = traceback.format_exc()
        frame = inspect.currentframe().f_back
        caller_info = inspect.getframeinfo(frame)
        
        # 自动分类错误
        identified_pattern = None
        if category is None or severity is None:
            error_str = str(error).lower()
            for pattern_name, pattern_info in ERROR_PATTERNS.items():
                if any(p.lower() in error_str for p in pattern_info["patterns"]):
                    identified_pattern = pattern_name
                    if category is None:
                        category = pattern_info["category"]
                    if severity is None:
                        severity = pattern_info["severity"]
                    break
        
        # 处理类别和严重性
        if isinstance(category, str):
            category = ErrorCategory.from_string(category)
        elif category is None:
            category = ErrorCategory.UNKNOWN
            
        if isinstance(severity, str):
            severity = ErrorSeverity.from_string(severity)
        elif severity is None:
            severity = ErrorSeverity.MEDIUM
        
        # 记录错误信息
        error_id = f"{int(time.time())}_{hash(str(error)) % 10000}"
        error_info = {
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "category": category.value,
            "severity": severity.value,
            "identified_pattern": identified_pattern,
            "stack_trace": stack_trace,
            "context": context,
            "file": caller_info.filename,
            "line": caller_info.lineno,
            "function": caller_info.function,
            "recovery_attempts": recovery_attempts,
            "system_info": {
                "os": platform.system(),
                "version": platform.version(),
                "python": platform.python_version()
            }
        }
        
        # 记录到日志
        logger.error(f"错误ID: {error_id}, 类别: {category.value}, 严重性: {severity.value}")
        logger.error(f"错误消息: {error}")
        logger.error(f"错误模式: {identified_pattern}")
        logger.error(f"堆栈: {stack_trace}")
        
        # 保存详细错误信息到JSON文件
        error_file = self.log_dir / f"error_{error_id}.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)
        
        # 尝试恢复
        recovery_result = self._attempt_recovery(error, identified_pattern, category, severity, context, recovery_attempts)
        error_info.update(recovery_result)
        
        return error_info
    
    def _attempt_recovery(self, 
                        error: Exception, 
                        pattern: str, 
                        category: ErrorCategory, 
                        severity: ErrorSeverity,
                        context: dict,
                        recovery_attempts: int) -> dict:
        """尝试恢复错误
        
        Args:
            error: 异常对象
            pattern: 识别的错误模式
            category: 错误类别
            severity: 错误严重性
            context: 错误上下文
            recovery_attempts: 已尝试恢复的次数
            
        Returns:
            包含恢复结果的字典
        """
        # 如果已经尝试恢复太多次，放弃恢复
        if recovery_attempts >= 3:
            logger.warning(f"已尝试恢复{recovery_attempts}次，放弃进一步恢复")
            return {
                "recovery_success": False,
                "recovery_action": "none",
                "recovery_message": "已达到最大恢复尝试次数"
            }
        
        # 如果识别了模式，尝试应用对应的恢复策略
        if pattern and pattern in ERROR_PATTERNS:
            recovery_func = ERROR_PATTERNS[pattern].get("recovery")
            if recovery_func:
                try:
                    logger.info(f"尝试应用恢复策略: {pattern}")
                    recovery_func()
                    return {
                        "recovery_success": True,
                        "recovery_action": pattern,
                        "recovery_message": f"已应用{pattern}恢复策略"
                    }
                except Exception as recovery_error:
                    logger.error(f"恢复策略失败: {recovery_error}")
                    return {
                        "recovery_success": False,
                        "recovery_action": pattern,
                        "recovery_message": f"恢复策略失败: {recovery_error}"
                    }
        
        # 根据错误类别应用通用恢复策略
        if category == ErrorCategory.NETWORK:
            logger.info("应用网络错误通用恢复策略")
            time.sleep(5)  # 网络错误通常可以通过等待后重试解决
            return {
                "recovery_success": True,
                "recovery_action": "network_retry",
                "recovery_message": "已应用网络错误通用恢复策略"
            }
        elif category == ErrorCategory.API:
            logger.info("应用API错误通用恢复策略")
            time.sleep(10)  # API错误可能需要等待更长时间
            return {
                "recovery_success": True,
                "recovery_action": "api_retry",
                "recovery_message": "已应用API错误通用恢复策略"
            }
        elif severity == ErrorSeverity.LOW:
            # 低严重性错误，可以忽略
            return {
                "recovery_success": True,
                "recovery_action": "ignore",
                "recovery_message": "低严重性错误，已忽略"
            }
        else:
            # 其他情况，无法自动恢复
            return {
                "recovery_success": False,
                "recovery_action": "none",
                "recovery_message": "无法自动恢复"
            }
    
    def with_error_handling(self, 
                          category: Union[ErrorCategory, str] = None, 
                          severity: Union[ErrorSeverity, str] = None,
                          max_retries: int = 3,
                          retry_delay: int = 2):
        """错误处理装饰器
        
        Args:
            category: 错误类别
            severity: 错误严重性
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                
                retries = 0
                while retries <= max_retries:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        retries += 1
                        recovery_info = self.handle_error(
                            e, category, severity, context, retries - 1
                        )
                        
                        if retries > max_retries or not recovery_info.get("recovery_success", False):
                            logger.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数或无法恢复")
                            raise
                        
                        logger.info(f"函数 {func.__name__} 执行失败，正在重试 ({retries}/{max_retries})")
                        time.sleep(retry_delay * (2 ** (retries - 1)))  # 指数退避
            
            return wrapper
        return decorator

# 创建全局错误处理器实例
error_handler = ErrorHandler()

# 导出模块内容
__all__ = ["ErrorCategory", "ErrorSeverity", "ErrorHandler", "error_handler"] 