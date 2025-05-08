#!/usr/bin/env python3
"""
错误处理与恢复模块

此模块提供错误分类、诊断和自动恢复功能，用于提高多智能体系统的稳定性和可靠性。
主要功能包括：
1. 错误分类：将错误分为网络错误、资源错误、逻辑错误等不同类别
2. 错误诊断：分析错误原因和影响范围
3. 恢复策略：提供针对不同错误的恢复方案
4. 错误报告：生成结构化的错误报告
"""

import logging
import time
import traceback
import sys
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("error_handler")

class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = 1      # 轻微错误，不影响主要功能
    MEDIUM = 2   # 中等错误，影响部分功能但系统可继续运行
    HIGH = 3     # 严重错误，影响关键功能
    CRITICAL = 4 # 致命错误，系统无法继续运行

class ErrorCategory(Enum):
    """错误类别枚举"""
    NETWORK = "network"           # 网络连接错误
    API = "api"                   # API调用错误
    RESOURCE = "resource"         # 资源访问或分配错误
    LOGIC = "logic"               # 业务逻辑错误
    PERMISSION = "permission"     # 权限错误
    CONFIG = "config"             # 配置错误
    DATA = "data"                 # 数据处理错误
    TIMEOUT = "timeout"           # 超时错误
    DEPENDENCY = "dependency"     # 依赖项错误
    UNKNOWN = "unknown"           # 未知错误

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    message: str                      # 错误消息
    error_type: str                   # 错误类型
    timestamp: float                  # 错误发生时间戳
    category: ErrorCategory           # 错误类别
    severity: ErrorSeverity           # 错误严重程度
    source: str                       # 错误来源
    traceback: Optional[str] = None   # 错误堆栈
    context: Dict[str, Any] = None    # 错误上下文信息
    recovery_attempts: int = 0        # 恢复尝试次数
    resolved: bool = False            # 是否已解决

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, log_dir: Optional[str] = None, max_retries: int = 3):
        """初始化错误处理器
        
        Args:
            log_dir: 错误日志目录，默认为"error_logs"
            max_retries: 最大重试次数
        """
        self.max_retries = max_retries
        self.errors: List[ErrorInfo] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = self._init_recovery_strategies()
        
        # 设置日志目录
        self.log_dir = Path(log_dir or "error_logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 记录系统信息
        self.system_info = {
            "os": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        }
        
        logger.info(f"错误处理器初始化完成，日志目录: {self.log_dir}")
    
    def _init_recovery_strategies(self) -> Dict[ErrorCategory, List[Callable]]:
        """初始化不同错误类别的恢复策略"""
        return {
            ErrorCategory.NETWORK: [self._network_recovery],
            ErrorCategory.API: [self._api_recovery],
            ErrorCategory.RESOURCE: [self._resource_recovery],
            ErrorCategory.LOGIC: [self._logic_recovery],
            ErrorCategory.PERMISSION: [self._permission_recovery],
            ErrorCategory.CONFIG: [self._config_recovery],
            ErrorCategory.DATA: [self._data_recovery],
            ErrorCategory.TIMEOUT: [self._timeout_recovery],
            ErrorCategory.DEPENDENCY: [self._dependency_recovery],
            ErrorCategory.UNKNOWN: [self._fallback_recovery]
        }
    
    def handle_error(self, error: Exception, source: str, 
                    context: Dict[str, Any] = None,
                    severity: ErrorSeverity = None) -> ErrorInfo:
        """处理错误并返回错误信息
        
        Args:
            error: 异常对象
            source: 错误来源
            context: 错误上下文信息
            severity: 错误严重程度
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        # 获取错误堆栈
        tb_str = traceback.format_exc()
        
        # 错误分类
        category, error_severity = self._classify_error(error, source)
        
        # 如果外部指定了严重程度，则使用外部指定的
        if severity:
            error_severity = severity
        
        # 创建错误信息
        error_info = ErrorInfo(
            message=str(error),
            error_type=type(error).__name__,
            timestamp=time.time(),
            category=category,
            severity=error_severity,
            source=source,
            traceback=tb_str,
            context=context or {},
            recovery_attempts=0,
            resolved=False
        )
        
        # 记录错误
        self.errors.append(error_info)
        
        # 记录日志
        self._log_error(error_info)
        
        # 尝试恢复
        self._try_recover(error_info)
        
        return error_info
    
    def _classify_error(self, error: Exception, source: str) -> Tuple[ErrorCategory, ErrorSeverity]:
        """对错误进行分类
        
        Args:
            error: 异常对象
            source: 错误来源
            
        Returns:
            Tuple[ErrorCategory, ErrorSeverity]: 错误类别和严重程度
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # 网络错误
        if any(net_err in error_type for net_err in ["ConnectionError", "ConnectionRefused", "NetworkError"]):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # API错误
        if "api" in source.lower() or any(api_err in error_type for api_err in ["APIError", "RequestError"]):
            return ErrorCategory.API, ErrorSeverity.MEDIUM
        
        # 超时错误
        if "timeout" in error_type.lower() or "timeout" in error_msg:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
        
        # 资源错误
        if any(res_err in error_type for res_err in ["ResourceError", "MemoryError", "DiskError"]):
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
        
        # 权限错误
        if any(perm_err in error_type for perm_err in ["PermissionError", "AccessDenied"]):
            return ErrorCategory.PERMISSION, ErrorSeverity.HIGH
        
        # 配置错误
        if "config" in error_msg or "configuration" in error_msg:
            return ErrorCategory.CONFIG, ErrorSeverity.MEDIUM
        
        # 数据错误
        if any(data_err in error_type for data_err in ["ValueError", "TypeError", "JSONDecodeError"]):
            return ErrorCategory.DATA, ErrorSeverity.MEDIUM
        
        # 依赖错误
        if any(dep_err in error_type for dep_err in ["ImportError", "ModuleNotFoundError"]):
            return ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH
        
        # 默认为未知错误，中等严重程度
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """记录错误到日志文件
        
        Args:
            error_info: 错误信息对象
        """
        # 记录到应用日志
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(log_level, f"错误 [{error_info.category.value}]: {error_info.message} (来源: {error_info.source})")
        
        # 将错误信息序列化为JSON并保存到文件
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(error_info.timestamp))
        error_file = self.log_dir / f"error_{timestamp_str}_{error_info.error_type}.json"
        
        error_data = {
            "message": error_info.message,
            "error_type": error_info.error_type,
            "timestamp": error_info.timestamp,
            "category": error_info.category.value,
            "severity": error_info.severity.name,
            "source": error_info.source,
            "traceback": error_info.traceback,
            "context": error_info.context,
            "system_info": self.system_info
        }
        
        try:
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"错误详情已记录到 {error_file}")
        except Exception as e:
            logger.error(f"记录错误详情失败: {e}")
    
    def _try_recover(self, error_info: ErrorInfo) -> bool:
        """尝试从错误中恢复
        
        Args:
            error_info: 错误信息对象
            
        Returns:
            bool: 是否成功恢复
        """
        if error_info.recovery_attempts >= self.max_retries:
            logger.warning(f"错误已达到最大重试次数 ({self.max_retries})，不再尝试恢复")
            return False
        
        # 获取对应类别的恢复策略
        strategies = self.recovery_strategies.get(error_info.category, [self._fallback_recovery])
        
        # 递增恢复尝试次数
        error_info.recovery_attempts += 1
        
        # 尝试每个恢复策略
        for strategy in strategies:
            try:
                logger.info(f"尝试恢复错误 (尝试 {error_info.recovery_attempts}/{self.max_retries}): {error_info.message}")
                if strategy(error_info):
                    error_info.resolved = True
                    logger.info(f"错误已成功恢复: {error_info.message}")
                    return True
            except Exception as e:
                logger.error(f"恢复策略执行失败: {e}")
        
        logger.warning(f"所有恢复策略均失败，错误未解决: {error_info.message}")
        return False
    
    # 不同类型的恢复策略
    def _network_recovery(self, error_info: ErrorInfo) -> bool:
        """网络错误恢复策略"""
        # 实现网络重连逻辑
        logger.info("执行网络错误恢复策略")
        # 可以实现网络连接重试、切换备用服务器等
        
        # 模拟恢复过程
        time.sleep(1)  # 等待网络恢复
        return "connection refused" not in error_info.message.lower()  # 简单示例
    
    def _api_recovery(self, error_info: ErrorInfo) -> bool:
        """API错误恢复策略"""
        logger.info("执行API错误恢复策略")
        # 可以实现API重试、降级服务等
        
        # 检查是否是认证错误
        if "authentication" in error_info.message.lower() or "unauthorized" in error_info.message.lower():
            logger.info("检测到认证错误，尝试刷新凭证")
            # 实现凭证刷新逻辑
            return False  # 需要实际实现
        
        # 检查是否是速率限制
        if "rate limit" in error_info.message.lower() or "too many requests" in error_info.message.lower():
            wait_time = min(2 ** error_info.recovery_attempts, 60)  # 指数退避，最多等待60秒
            logger.info(f"检测到速率限制，等待 {wait_time} 秒后重试")
            time.sleep(wait_time)
            return True
        
        return False
    
    def _resource_recovery(self, error_info: ErrorInfo) -> bool:
        """资源错误恢复策略"""
        logger.info("执行资源错误恢复策略")
        # 可以实现释放资源、清理缓存等
        
        if "memory" in error_info.message.lower():
            logger.info("检测到内存问题，尝试释放内存")
            # 触发垃圾回收
            import gc
            gc.collect()
            return True
        
        return False
    
    def _logic_recovery(self, error_info: ErrorInfo) -> bool:
        """逻辑错误恢复策略"""
        logger.info("执行逻辑错误恢复策略")
        # 通常逻辑错误需要人工干预
        return False
    
    def _permission_recovery(self, error_info: ErrorInfo) -> bool:
        """权限错误恢复策略"""
        logger.info("执行权限错误恢复策略")
        # 可以尝试提升权限、使用备用凭证等
        return False
    
    def _config_recovery(self, error_info: ErrorInfo) -> bool:
        """配置错误恢复策略"""
        logger.info("执行配置错误恢复策略")
        # 可以尝试加载备用配置、使用默认值等
        return False
    
    def _data_recovery(self, error_info: ErrorInfo) -> bool:
        """数据错误恢复策略"""
        logger.info("执行数据错误恢复策略")
        # 可以尝试数据修复、使用缓存数据等
        return False
    
    def _timeout_recovery(self, error_info: ErrorInfo) -> bool:
        """超时错误恢复策略"""
        logger.info("执行超时错误恢复策略")
        # 可以实现延长超时时间、切换到轻量级服务等
        
        # 使用指数退避算法
        wait_time = min(2 ** error_info.recovery_attempts, 30)  # 最多等待30秒
        logger.info(f"等待 {wait_time} 秒后重试")
        time.sleep(wait_time)
        return True
    
    def _dependency_recovery(self, error_info: ErrorInfo) -> bool:
        """依赖错误恢复策略"""
        logger.info("执行依赖错误恢复策略")
        # 可以尝试安装依赖、使用备用依赖等
        return False
    
    def _fallback_recovery(self, error_info: ErrorInfo) -> bool:
        """通用恢复策略，作为其他策略的后备"""
        logger.info("执行通用恢复策略")
        # 通用恢复逻辑，例如简单的重试
        time.sleep(1)
        return False
    
    def get_error_report(self) -> Dict[str, Any]:
        """生成错误报告
        
        Returns:
            Dict[str, Any]: 包含错误统计信息的报告
        """
        if not self.errors:
            return {"total_errors": 0, "categories": {}, "severity": {}}
        
        # 统计错误类别
        categories = {}
        for error in self.errors:
            cat = error.category.value
            if cat in categories:
                categories[cat] += 1
            else:
                categories[cat] = 1
        
        # 统计错误严重程度
        severity = {}
        for error in self.errors:
            sev = error.severity.name
            if sev in severity:
                severity[sev] += 1
            else:
                severity[sev] = 1
        
        # 统计恢复情况
        resolved = sum(1 for error in self.errors if error.resolved)
        
        return {
            "total_errors": len(self.errors),
            "resolved_errors": resolved,
            "resolution_rate": resolved / len(self.errors) if self.errors else 0,
            "categories": categories,
            "severity": severity,
            "latest_error": {
                "message": self.errors[-1].message,
                "type": self.errors[-1].error_type,
                "source": self.errors[-1].source,
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.errors[-1].timestamp))
            } if self.errors else None
        }
    
    def clear_resolved_errors(self) -> int:
        """清除已解决的错误记录
        
        Returns:
            int: 清除的错误数量
        """
        resolved_count = sum(1 for error in self.errors if error.resolved)
        self.errors = [error for error in self.errors if not error.resolved]
        logger.info(f"已清除 {resolved_count} 个已解决的错误记录")
        return resolved_count

# 创建全局错误处理器实例
_error_handler: Optional[ErrorHandler] = None

def get_error_handler(log_dir: Optional[str] = None, max_retries: int = 3) -> ErrorHandler:
    """获取或创建全局错误处理器实例
    
    Args:
        log_dir: 错误日志目录
        max_retries: 最大重试次数
    
    Returns:
        ErrorHandler: 错误处理器实例
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(log_dir, max_retries)
    return _error_handler

def handle_exception(source: str, context: Dict[str, Any] = None,
                    severity: ErrorSeverity = None) -> Callable:
    """错误处理装饰器
    
    Args:
        source: 错误来源
        context: 错误上下文
        severity: 错误严重程度
    
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                error_info = handler.handle_error(e, source, context, severity)
                if error_info.resolved:
                    # 如果错误已解决，尝试重新执行函数
                    return func(*args, **kwargs)
                else:
                    # 否则重新抛出异常
                    raise
        return wrapper
    return decorator

# 测试函数
def main():
    parser = argparse.ArgumentParser(description='错误处理测试工具')
    parser.add_argument('--error-type', type=str, default='network',
                       choices=['network', 'api', 'timeout', 'resource', 'data'],
                       help='要测试的错误类型')
    parser.add_argument('--verbose', '-v', action='store_true', help='启用详细日志')
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 初始化错误处理器
    handler = get_error_handler()
    
    # 测试不同类型的错误
    try:
        if args.error_type == 'network':
            raise ConnectionError("模拟网络连接错误")
        elif args.error_type == 'api':
            raise ValueError("API调用失败: 无效的认证令牌")
        elif args.error_type == 'timeout':
            raise TimeoutError("操作超时")
        elif args.error_type == 'resource':
            raise MemoryError("内存不足")
        elif args.error_type == 'data':
            raise ValueError("数据解析错误: 无效的JSON格式")
        else:
            raise RuntimeError("未知错误")
            
    except Exception as e:
        # 处理错误
        error_info = handler.handle_error(e, "错误测试模块", {"test_mode": True})
        
        # 打印错误报告
        report = handler.get_error_report()
        print(f"\n错误报告:")
        print(f"总错误数: {report['total_errors']}")
        print(f"已解决错误数: {report['resolved_errors']}")
        print(f"解决率: {report['resolution_rate']*100:.1f}%")
        print(f"错误类别统计: {report['categories']}")
        print(f"错误严重程度统计: {report['severity']}")
        
        if error_info.resolved:
            print(f"\n错误已成功恢复: {error_info.message}")
        else:
            print(f"\n错误未能恢复: {error_info.message}")

if __name__ == "__main__":
    import argparse
    main() 