"""错误处理模块

该模块实现了一个全面的错误处理系统，支持错误分类、严重程度评估、
错误日志记录和自动恢复策略。用于提高系统的稳定性和可靠性。
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
logger = logging.getLogger("error_handler")
logger.setLevel(logging.INFO)

# 确保跨平台兼容性的日志路径处理
def get_log_path() -> Path:
    """获取平台适配的日志目录路径"""
    system = platform.system()
    home = Path.home()
    
    if system == "Windows":
        log_dir = home / "AppData" / "Local" / "multi_agent_mcp" / "logs"
    elif system == "Darwin":  # macOS
        log_dir = home / "Library" / "Logs" / "multi_agent_mcp"
    else:  # Linux和其他
        log_dir = home / ".local" / "share" / "multi_agent_mcp" / "logs"
    
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

# 创建文件处理器
log_file = get_log_path() / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# 设置格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 定义错误类别
class ErrorCategory(enum.Enum):
    NETWORK = "network"  # 网络相关错误
    API = "api"          # API调用错误
    API_KEY_MISSING = "api_key_missing"  # API密钥缺失
    API_QUOTA = "api_quota"  # API配额超限
    API_RATE_LIMIT = "api_rate_limit"  # API速率限制
    API_TIMEOUT = "api_timeout"  # API超时
    API_ERROR = "api_error"  # 其他API错误
    RESOURCE = "resource"  # 资源访问错误
    CONFIG = "config"    # 配置错误
    PERMISSION = "permission"  # 权限错误
    DATA = "data"        # 数据处理错误
    LOGIC = "logic"      # 业务逻辑错误
    SYSTEM = "system"    # 系统级错误
    SERVER = "server"    # 服务器错误
    CLIENT = "client"    # 客户端错误
    APPLICATION = "application"  # 应用程序错误
    MODULE_NOT_AVAILABLE = "module_not_available"  # 模块不可用
    IMPORT_ERROR = "import_error"  # 导入错误
    FILE_OPERATION = "file_operation"  # 文件操作错误
    SEARCH = "search"    # 搜索错误
    SYNC = "sync"        # 同步错误
    INVALID_INPUT = "invalid_input"  # 无效输入
    LLM_API = "llm_api"  # LLM API错误
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

# 定义错误模式类
class ErrorPattern:
    """错误模式类，用于定义错误特征和恢复策略"""
    
    def __init__(self, name: str, keywords: List[str], category: ErrorCategory, 
                 message_patterns: List[str], recovery_strategy: Optional[Callable] = None):
        """
        初始化错误模式
        
        Args:
            name: 错误模式名称
            keywords: 与错误类型相关的关键词列表
            category: 错误类别
            message_patterns: 错误消息中的模式列表
            recovery_strategy: 恢复策略函数
        """
        self.name = name
        self.keywords = keywords
        self.category = category
        self.message_patterns = message_patterns
        self.recovery_strategy = recovery_strategy
    
    def matches(self, error: Exception, error_message: str) -> bool:
        """
        检查错误是否匹配此模式
        
        Args:
            error: 异常对象
            error_message: 错误消息
            
        Returns:
            是否匹配
        """
        # 检查错误类型
        error_type = error.__class__.__name__
        if any(keyword in error_type for keyword in self.keywords):
            return True
        
        # 检查错误消息
        error_message = error_message.lower()
        if any(pattern.lower() in error_message for pattern in self.message_patterns):
            return True
        
        return False

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
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_patterns = self._build_error_patterns()
        self.error_stats = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "recovery_attempts": 0,
            "recovery_success": 0
        }
        self.error_history = []
        self.max_history_size = 100
    
    def _build_error_patterns(self) -> List[ErrorPattern]:
        """构建错误模式库"""
        patterns = []
        
        # 网络错误
        patterns.append(ErrorPattern(
            name="connection_error",
            keywords=["ConnectionError", "ConnectionRefused", "ConnectionTimeout"],
            category=ErrorCategory.NETWORK,
            message_patterns=["connection refused", "failed to establish", "network unreachable"],
            recovery_strategy=self._handle_network_error
        ))
        
        # API密钥错误
        patterns.append(ErrorPattern(
            name="api_key_error",
            keywords=["AuthenticationError", "KeyError"],
            category=ErrorCategory.API_KEY_MISSING,
            message_patterns=["invalid api key", "api key missing", "authentication failed"],
            recovery_strategy=self._handle_api_key_error
        ))
        
        # API配额错误
        patterns.append(ErrorPattern(
            name="api_quota_error",
            keywords=["QuotaExceeded", "BillingError"],
            category=ErrorCategory.API_QUOTA,
            message_patterns=["quota exceeded", "billing error", "payment required"],
            recovery_strategy=self._handle_api_quota_error
        ))
        
        # API速率限制错误
        patterns.append(ErrorPattern(
            name="rate_limit_error",
            keywords=["RateLimitError", "TooManyRequests"],
            category=ErrorCategory.API_RATE_LIMIT,
            message_patterns=["rate limit", "too many requests", "429"],
            recovery_strategy=self._handle_rate_limit_error
        ))
        
        # API超时错误
        patterns.append(ErrorPattern(
            name="timeout_error",
            keywords=["Timeout", "ReadTimeout", "ConnectTimeout"],
            category=ErrorCategory.API_TIMEOUT,
            message_patterns=["timeout", "timed out", "request took too long"],
            recovery_strategy=self._handle_timeout_error
        ))
        
        # 导入错误
        patterns.append(ErrorPattern(
            name="import_error",
            keywords=["ImportError", "ModuleNotFoundError"],
            category=ErrorCategory.IMPORT_ERROR,
            message_patterns=["no module named", "cannot import", "module not found"],
            recovery_strategy=self._handle_import_error
        ))
        
        # 资源错误
        patterns.append(ErrorPattern(
            name="resource_error",
            keywords=["ResourceWarning", "MemoryError", "DiskError"],
            category=ErrorCategory.RESOURCE,
            message_patterns=["no space left", "memory error", "resource exhausted"],
            recovery_strategy=self._handle_resource_error
        ))
        
        return patterns
    
    def _identify_error_pattern(self, error: Exception, error_message: str) -> Optional[ErrorPattern]:
        """
        识别错误模式
        
        Args:
            error: 异常对象
            error_message: 错误消息
            
        Returns:
            匹配的错误模式，如果没有匹配则返回None
        """
        for pattern in self.error_patterns:
            if pattern.matches(error, error_message):
                return pattern
        return None
    
    def handle_error(self, 
                    error: Exception, 
                    category: ErrorCategory = None, 
                    severity: ErrorSeverity = None,
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            category: 错误类别，如果为None则自动识别
            severity: 错误严重程度，如果为None则自动评估
            context: 错误上下文
            
        Returns:
            处理结果字典
        """
        self.error_stats["total_errors"] += 1
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # 上下文处理
        context = context or {}
        
        # 识别错误模式
        error_pattern = None
        if category is None:
            error_pattern = self._identify_error_pattern(error, error_message)
            if error_pattern:
                category = error_pattern.category
            else:
                category = ErrorCategory.UNKNOWN
        
        # 评估严重程度
        if severity is None:
            severity = self._assess_severity(category, error_message)
        
        # 更新统计
        if category.value not in self.error_stats["by_category"]:
            self.error_stats["by_category"][category.value] = 0
        self.error_stats["by_category"][category.value] += 1
        
        if severity.value not in self.error_stats["by_severity"]:
            self.error_stats["by_severity"][severity.value] = 0
        self.error_stats["by_severity"][severity.value] += 1
        
        # 记录错误
        timestamp = datetime.now().isoformat()
        error_record = {
            "timestamp": timestamp,
            "error_type": error.__class__.__name__,
            "message": error_message,
            "category": category.value,
            "severity": severity.value,
            "context": context,
            "traceback": error_traceback
        }
        
        # 添加到历史记录
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
        
        # 记录日志
        self._log_error(error_record)
        
        # 尝试恢复
        recovery_result = None
        if error_pattern and error_pattern.recovery_strategy:
            self.error_stats["recovery_attempts"] += 1
            try:
                recovery_result = error_pattern.recovery_strategy(error, context)
                if recovery_result.get("success", False):
                    self.error_stats["recovery_success"] += 1
            except Exception as recovery_error:
                recovery_result = {
                    "success": False,
                    "message": f"恢复策略执行失败: {str(recovery_error)}"
                }
        
        # 返回处理结果
        result = {
            "error_id": hash(f"{timestamp}-{error_message}"),
            "category": category.value,
            "severity": severity.value,
            "recovery_attempted": recovery_result is not None,
            "recovery_result": recovery_result
        }
        
        return result
    
    def _assess_severity(self, category: ErrorCategory, message: str) -> ErrorSeverity:
        """
        评估错误严重程度
        
        Args:
            category: 错误类别
            message: 错误消息
            
        Returns:
            严重程度级别
        """
        # 根据错误类别确定基础严重程度
        base_severity = {
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.API_KEY_MISSING: ErrorSeverity.HIGH,
            ErrorCategory.API_QUOTA: ErrorSeverity.HIGH,
            ErrorCategory.API_RATE_LIMIT: ErrorSeverity.MEDIUM,
            ErrorCategory.API_TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorCategory.API_ERROR: ErrorSeverity.MEDIUM,
            ErrorCategory.SYSTEM: ErrorSeverity.HIGH,
            ErrorCategory.RESOURCE: ErrorSeverity.HIGH,
            ErrorCategory.IMPORT_ERROR: ErrorSeverity.HIGH,
            ErrorCategory.MODULE_NOT_AVAILABLE: ErrorSeverity.HIGH,
            ErrorCategory.INVALID_INPUT: ErrorSeverity.LOW,
            ErrorCategory.LLM_API: ErrorSeverity.MEDIUM,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM
        }.get(category, ErrorSeverity.MEDIUM)
        
        # 根据错误消息中的关键词可能提高严重程度
        critical_keywords = ["critical", "fatal", "crash", "emergency", "corrupt"]
        for keyword in critical_keywords:
            if keyword.lower() in message.lower():
                return ErrorSeverity.CRITICAL
        
        high_keywords = ["error", "failure", "failed", "exception", "denied"]
        if base_severity.value == ErrorSeverity.MEDIUM.value:
            for keyword in high_keywords:
                if keyword.lower() in message.lower():
                    return ErrorSeverity.HIGH
        
        return base_severity
    
    def _log_error(self, error_record: Dict[str, Any]) -> None:
        """
        记录错误日志
        
        Args:
            error_record: 错误记录
        """
        severity = error_record["severity"]
        category = error_record["category"]
        error_type = error_record["error_type"]
        message = error_record["message"]
        context_str = json.dumps(error_record["context"], ensure_ascii=False)
        
        log_message = f"[{severity.upper()}] [{category}] {error_type}: {message} | Context: {context_str}"
        
        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH.value:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM.value:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # 对于严重错误，记录完整堆栈跟踪
        if severity in [ErrorSeverity.HIGH.value, ErrorSeverity.CRITICAL.value]:
            logger.error(f"Traceback:\n{error_record['traceback']}")
        
        # 保存错误记录到文件
        try:
            error_file = get_log_path() / "error_records.jsonl"
            with open(error_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存错误记录失败: {e}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            错误统计数据字典
        """
        return self.error_stats
    
    def get_error_history(self, 
                         limit: int = 10, 
                         category: Optional[ErrorCategory] = None, 
                         severity: Optional[ErrorSeverity] = None) -> List[Dict[str, Any]]:
        """
        获取错误历史记录
        
        Args:
            limit: 返回记录的最大数量
            category: 按类别筛选
            severity: 按严重程度筛选
            
        Returns:
            错误历史记录列表
        """
        filtered_history = self.error_history
        
        if category:
            filtered_history = [
                record for record in filtered_history 
                if record["category"] == category.value
            ]
        
        if severity:
            filtered_history = [
                record for record in filtered_history 
                if record["severity"] == severity.value
            ]
        
        # 最新的错误排在前面
        return sorted(
            filtered_history, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )[:limit]
    
    def _handle_network_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理网络错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        # 实现指数退避重试
        max_retries = context.get("max_retries", 3)
        current_retry = context.get("current_retry", 0)
        
        if current_retry >= max_retries:
            return {
                "success": False,
                "message": f"达到最大重试次数 ({max_retries})",
                "retry_exhausted": True
            }
        
        # 计算退避时间
        backoff_time = (2 ** current_retry) * 0.5  # 0.5, 1, 2, 4, ...秒
        logger.info(f"网络错误，将在{backoff_time}秒后重试 (尝试 {current_retry + 1}/{max_retries})")
        
        # 等待退避时间
        time.sleep(backoff_time)
        
        return {
            "success": True,
            "message": f"成功应用网络错误恢复策略，等待{backoff_time}秒后重试",
            "next_retry": current_retry + 1,
            "backoff_time": backoff_time
        }
    
    def _handle_api_key_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理API密钥错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        provider = context.get("provider", "unknown")
        
        # 尝试使用备用API密钥
        backup_key_var = f"{provider.upper()}_API_KEY_BACKUP"
        backup_key = os.environ.get(backup_key_var)
        
        if backup_key:
            # 将备用密钥设置为主密钥
            os.environ[f"{provider.upper()}_API_KEY"] = backup_key
            return {
                "success": True,
                "message": f"成功切换到备用API密钥",
                "action": "switched_to_backup_key"
            }
        
        # 如果没有备用密钥，尝试切换到备用提供商
        if provider != "local" and provider != "mock":
            return {
                "success": True,
                "message": f"API密钥无效，建议切换到备用提供商",
                "action": "switch_provider",
                "recommended_provider": "local" if os.path.exists("./models") else "mock"
            }
        
        return {
            "success": False,
            "message": f"无法恢复API密钥错误，没有可用的备用密钥或提供商"
        }
    
    def _handle_api_quota_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理API配额错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        provider = context.get("provider", "unknown")
        
        # 尝试切换到不同的提供商
        available_providers = ["local", "mock"]
        for alternative in available_providers:
            if alternative != provider:
                return {
                    "success": True,
                    "message": f"API配额超限，建议切换到{alternative}提供商",
                    "action": "switch_provider",
                    "recommended_provider": alternative
                }
        
        return {
            "success": False,
            "message": "无法恢复API配额错误，没有可用的备用提供商"
        }
    
    def _handle_rate_limit_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理速率限制错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        # 实现较长的指数退避重试
        max_retries = context.get("max_retries", 5)
        current_retry = context.get("current_retry", 0)
        
        if current_retry >= max_retries:
            return {
                "success": False,
                "message": f"达到最大重试次数 ({max_retries})",
                "retry_exhausted": True
            }
        
        # 计算退避时间 - 对于速率限制，使用更长的等待时间
        backoff_time = (2 ** current_retry) * 2.0  # 2, 4, 8, 16, ...秒
        logger.info(f"速率限制错误，将在{backoff_time}秒后重试 (尝试 {current_retry + 1}/{max_retries})")
        
        # 等待退避时间
        time.sleep(backoff_time)
        
        return {
            "success": True,
            "message": f"成功应用速率限制恢复策略，等待{backoff_time}秒后重试",
            "next_retry": current_retry + 1,
            "backoff_time": backoff_time
        }
    
    def _handle_timeout_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理超时错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        max_retries = context.get("max_retries", 2)
        current_retry = context.get("current_retry", 0)
        
        if current_retry >= max_retries:
            return {
                "success": False,
                "message": f"达到最大重试次数 ({max_retries})",
                "retry_exhausted": True
            }
        
        # 计算退避时间
        backoff_time = 1.0 * (current_retry + 1)  # 1, 2, 3秒
        logger.info(f"超时错误，将在{backoff_time}秒后重试 (尝试 {current_retry + 1}/{max_retries})")
        
        # 等待退避时间
        time.sleep(backoff_time)
        
        return {
            "success": True,
            "message": f"成功应用超时错误恢复策略，等待{backoff_time}秒后重试",
            "next_retry": current_retry + 1,
            "backoff_time": backoff_time
        }
    
    def _handle_import_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理导入错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        module = context.get("module", "unknown")
        
        return {
            "success": False,
            "message": f"无法自动解决导入错误，模块 '{module}' 缺失",
            "recommendation": "请检查系统环境并安装所需依赖"
        }
    
    def _handle_resource_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理资源错误的恢复策略
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果
        """
        # 尝试清理临时文件
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_files = os.listdir(temp_dir)
            
            # 只删除由应用程序创建的临时文件
            app_temp_files = [f for f in temp_files if f.startswith("multi_agent_mcp_")]
            for f in app_temp_files:
                try:
                    os.remove(os.path.join(temp_dir, f))
                except:
                    pass
            
            return {
                "success": True,
                "message": f"已清理 {len(app_temp_files)} 个临时文件",
                "action": "cleaned_temp_files"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"尝试清理资源失败: {str(e)}"
            }

# 创建全局错误处理实例
error_handler = ErrorHandler()

def with_error_handling(category: ErrorCategory = None):
    """
    错误处理装饰器
    
    Args:
        category: 默认错误类别
        
    Returns:
        装饰后的函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                error_handler.handle_error(e, category=category, context=context)
                # 重新抛出异常，以便调用者可以决定如何处理
                raise
        return wrapper
    return decorator

# 错误诊断函数
def diagnose_system() -> Dict[str, Any]:
    """
    诊断系统状态
    
    Returns:
        系统状态诊断结果
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "system": platform.system(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "memory": {},
        "disk": {},
        "network": {},
        "environment": {}
    }
    
    # 检查内存
    try:
        import psutil
        mem = psutil.virtual_memory()
        result["memory"] = {
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent,
            "used": mem.used,
            "free": mem.free
        }
    except ImportError:
        result["memory"] = {"status": "psutil模块未安装，无法获取内存信息"}
    
    # 检查磁盘
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        result["disk"] = {
            "total": total,
            "used": used,
            "free": free,
            "percent_used": (used / total) * 100
        }
    except Exception as e:
        result["disk"] = {"status": f"无法获取磁盘信息: {str(e)}"}
    
    # 检查网络连接
    network_targets = ["www.google.com", "www.baidu.com", "api.openai.com", "cloud.anthropic.com"]
    result["network"] = {}
    
    for target in network_targets:
        try:
            import socket
            socket.create_connection((target, 443), timeout=2)
            result["network"][target] = "可连接"
        except Exception:
            result["network"][target] = "不可连接"
    
    # 检查环境变量
    env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "PYTHON_PATH"]
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # 不显示完整的API密钥，只显示前4个字符
            if "API_KEY" in var and len(value) > 8:
                result["environment"][var] = f"{value[:4]}...{value[-4:]}"
            else:
                result["environment"][var] = value
        else:
            result["environment"][var] = "未设置"
    
    return result

# 导出模块内容
__all__ = ["ErrorCategory", "ErrorSeverity", "ErrorHandler", "error_handler"] 