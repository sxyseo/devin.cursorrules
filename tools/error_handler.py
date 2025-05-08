#!/usr/bin/env python3
"""
错误处理模块

提供错误分类、诊断和自动恢复功能，用于增强系统的可靠性和稳定性
"""

import os
import sys
import logging
import traceback
import json
import time
import platform
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("error_handler")

# 错误类别枚举
class ErrorCategory(Enum):
    """错误类别枚举"""
    NETWORK = "network"
    API = "api"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    DATA = "data"
    SYNTAX = "syntax"
    LOGIC = "logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"

# 错误严重程度枚举
class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_type: str
    message: str
    source: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_method: Optional[str] = None
    system_info: Dict[str, str] = field(default_factory=dict)

class ErrorHandler:
    """错误处理器类"""
    
    def __init__(self, log_dir: Optional[str] = None, max_log_size: int = 1024*1024*10):
        """初始化错误处理器
        
        Args:
            log_dir: 错误日志目录，默认为'error_logs'
            max_log_size: 日志文件最大大小，默认为10MB
        """
        self.log_dir = Path(log_dir or 'error_logs')
        self.max_log_size = max_log_size
        self.errors = []  # 保存当前会话中的错误
        self.recovery_strategies = {}  # 错误恢复策略映射
        self.system_info = self._collect_system_info()
        
        # 确保日志目录存在
        self.log_dir.mkdir(exist_ok=True)
        
        logger.info(f"错误处理器初始化完成，日志目录: {self.log_dir.absolute()}")
    
    def _collect_system_info(self) -> Dict[str, str]:
        """收集系统信息
        
        Returns:
            Dict[str, str]: 系统信息
        """
        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "time": datetime.datetime.now().isoformat()
        }
    
    def _categorize_error(self, error: Exception, source: str) -> Tuple[ErrorCategory, ErrorSeverity]:
        """对错误进行分类和评估严重程度
        
        Args:
            error: 异常对象
            source: 错误来源
            
        Returns:
            Tuple[ErrorCategory, ErrorSeverity]: 错误类别和严重程度
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # 网络相关错误
        if any(err in error_type for err in ['ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError', 'ConnectionAbortedError']):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # 超时错误
        if 'TimeoutError' in error_type or 'timeout' in error_msg:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
        
        # API错误
        if 'API' in error_type or 'api' in error_msg or 'key' in error_msg:
            if 'authentication' in error_msg or 'unauthorized' in error_msg or 'auth' in error_msg:
                return ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH
            return ErrorCategory.API, ErrorSeverity.MEDIUM
        
        # 资源错误
        if 'MemoryError' in error_type or 'memory' in error_msg or 'resource' in error_msg:
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
        
        # 依赖错误
        if 'ImportError' in error_type or 'ModuleNotFoundError' in error_type:
            return ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH
        
        # 权限错误
        if 'PermissionError' in error_type or 'permission' in error_msg or 'access' in error_msg:
            return ErrorCategory.PERMISSION, ErrorSeverity.HIGH
        
        # 数据错误
        if any(err in error_type for err in ['ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError']):
            return ErrorCategory.DATA, ErrorSeverity.MEDIUM
        
        # 语法错误
        if 'SyntaxError' in error_type:
            return ErrorCategory.SYNTAX, ErrorSeverity.HIGH
        
        # 逻辑错误
        if 'AssertionError' in error_type or 'logic' in error_msg:
            return ErrorCategory.LOGIC, ErrorSeverity.MEDIUM
        
        # 系统错误
        if 'OSError' in error_type or 'system' in error_msg:
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
        
        # 默认为未知错误
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def handle_error(self, error: Exception, source: str, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理错误
        
        Args:
            error: 异常对象
            source: 错误来源
            context: 错误上下文信息
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        # 对错误进行分类
        category, severity = self._categorize_error(error, source)
        
        # 创建错误信息对象
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            source=source,
            category=category,
            severity=severity,
            stack_trace=traceback.format_exc(),
            context=context or {},
            system_info=self.system_info
        )
        
        # 记录错误
        self.errors.append(error_info)
        
        # 记录到日志文件
        self._log_error(error_info)
        
        # 尝试自动恢复
        resolved = self._try_recover(error_info)
        if resolved:
            error_info.resolved = True
            logger.info(f"错误已自动恢复: {error_info.error_type} - {error_info.message}")
        else:
            logger.warning(f"无法自动恢复错误: {error_info.error_type} - {error_info.message}")
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """将错误记录到日志文件
        
        Args:
            error_info: 错误信息对象
        """
        # 创建日志文件名
        timestamp = datetime.datetime.fromtimestamp(error_info.timestamp).strftime("%Y%m%d")
        log_file = self.log_dir / f"error_{timestamp}.log"
        
        # 检查日志文件大小，如果超过最大大小则创建新文件
        if log_file.exists() and log_file.stat().st_size > self.max_log_size:
            time_str = datetime.datetime.fromtimestamp(error_info.timestamp).strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"error_{time_str}.log"
        
        # 将错误信息转换为JSON格式
        error_dict = {
            "timestamp": datetime.datetime.fromtimestamp(error_info.timestamp).isoformat(),
            "error_type": error_info.error_type,
            "message": error_info.message,
            "source": error_info.source,
            "category": error_info.category.value,
            "severity": error_info.severity.name,
            "stack_trace": error_info.stack_trace,
            "context": error_info.context,
            "system_info": error_info.system_info
        }
        
        # 写入日志文件
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_dict, ensure_ascii=False) + "\n")
                logger.debug(f"错误信息已记录到 {log_file}")
        except Exception as e:
            logger.error(f"记录错误信息到日志文件时出错: {e}")
    
    def _try_recover(self, error_info: ErrorInfo) -> bool:
        """尝试自动恢复错误
        
        Args:
            error_info: 错误信息对象
            
        Returns:
            bool: 是否成功恢复
        """
        # 简单恢复策略
        if error_info.category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.API]:
            # 网络、超时和API错误通常可以通过重试解决
            error_info.recovery_attempts += 1
            error_info.resolution_method = "retry"
            # 实际的重试逻辑在调用此方法的代码中实现
            logger.info(f"建议重试以解决 {error_info.category.value} 错误，当前重试次数: {error_info.recovery_attempts}")
            return False  # 返回False，因为实际重试在外部进行
        
        if error_info.category == ErrorCategory.RESOURCE:
            # 资源错误可能需要释放资源
            try:
                import gc
                gc.collect()
                error_info.recovery_attempts += 1
                error_info.resolution_method = "gc_collect"
                logger.info("已执行垃圾回收，尝试释放内存资源")
                return True
            except Exception as e:
                logger.error(f"执行垃圾回收时出错: {e}")
                return False
        
        # 不知道如何恢复的错误
        return False
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable[[ErrorInfo], bool]) -> None:
        """注册错误恢复策略
        
        Args:
            category: 错误类别
            strategy: 恢复策略函数，接收ErrorInfo对象，返回是否成功恢复
        """
        self.recovery_strategies[category] = strategy
        logger.info(f"已注册 {category.value} 类型错误的恢复策略")
    
    def get_error_report(self) -> Dict[str, Any]:
        """获取错误报告
        
        Returns:
            Dict[str, Any]: 错误报告
        """
        if not self.errors:
            return {"status": "no_errors", "message": "没有记录的错误"}
        
        # 统计各类型错误的数量
        error_counts = {}
        for error in self.errors:
            category = error.category.value
            if category in error_counts:
                error_counts[category] += 1
            else:
                error_counts[category] = 1
        
        # 最近的5个错误
        recent_errors = []
        for error in self.errors[-5:]:
            recent_errors.append({
                "timestamp": datetime.datetime.fromtimestamp(error.timestamp).isoformat(),
                "error_type": error.error_type,
                "message": error.message,
                "source": error.source,
                "category": error.category.value,
                "severity": error.severity.name,
                "resolved": error.resolved
            })
        
        return {
            "status": "has_errors",
            "total_errors": len(self.errors),
            "error_counts": error_counts,
            "recent_errors": recent_errors,
            "resolved_count": sum(1 for e in self.errors if e.resolved),
            "system_info": self.system_info
        }
    
    def clear_errors(self) -> None:
        """清除记录的错误"""
        self.errors.clear()
        logger.info("已清除所有记录的错误")

# 单例模式
_error_handler = None

def get_error_handler(log_dir: Optional[str] = None) -> ErrorHandler:
    """获取或创建错误处理器实例
    
    Args:
        log_dir: 错误日志目录，默认为'error_logs'
        
    Returns:
        ErrorHandler: 错误处理器实例
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(log_dir)
    return _error_handler

def handle_exception(source: str, context: Dict[str, Any] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """装饰器，用于捕获和处理函数中的异常
    
    Args:
        source: 错误来源
        context: 错误上下文信息
        severity: 错误严重程度
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                error_info = handler.handle_error(e, source, context)
                # 如果错误已经被自动恢复，重新调用函数
                if error_info.resolved:
                    logger.info(f"错误已自动恢复，重新调用函数 {func.__name__}")
                    return func(*args, **kwargs)
                # 否则重新抛出异常
                logger.error(f"函数 {func.__name__} 执行时出错: {e}")
                raise
        return wrapper
    return decorator

if __name__ == "__main__":
    # 测试错误处理器
    handler = get_error_handler()
    try:
        # 测试网络错误
        raise ConnectionError("测试连接错误")
    except Exception as e:
        error_info = handler.handle_error(e, "测试源", {"test": "context"})
        print(f"错误类别: {error_info.category.value}")
        print(f"错误严重程度: {error_info.severity.name}")
        print(f"是否已解决: {error_info.resolved}")
    
    # 输出错误报告
    report = handler.get_error_report()
    print(json.dumps(report, indent=2, ensure_ascii=False)) 