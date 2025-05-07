"""
Tools package for various utilities including LLM API integration, web scraping, token tracking, 
model selection, and environment monitoring.
"""

# 导出工具选择器和环境监控功能
try:
    from .tool_selector import (
        LLMSelector, EnvironmentMonitor, 
        get_llm_selector, get_environment_monitor
    )
except ImportError:
    pass  # 允许在tool_selector.py不存在时也能导入其他模块 