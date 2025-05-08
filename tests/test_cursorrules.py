#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import psutil
import pytest
import logging
from datetime import datetime
from typing import Dict, List, Any
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cursorrules_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@pytest.fixture
def task_data():
    return {
        "type": "code_generation",
        "description": "生成一个简单的Python函数",
        "requirements": ["输入验证", "错误处理", "文档注释"]
    }

@pytest.fixture
def tester():
    # 项目根目录的test_cursorrules模块
    from test_cursorrules import CursorRulesTester
    return CursorRulesTester()

def test_planner_functionality(tester, task_data):
    """测试Planner功能"""
    result_package, metrics_data = tester.test_planner_functionality(task_data)
    pass_status, error_msg = result_package
    assert pass_status is True, f"Planner functionality failed, error: {error_msg}"
    assert error_msg is None
    assert "execution_time" in metrics_data

def test_executor_functionality(tester, task_data):
    """测试Executor功能"""
    result_package, metrics_data = tester.test_executor_functionality(task_data)
    pass_status, error_msg = result_package
    assert pass_status is True, f"Executor functionality failed, error: {error_msg}"
    assert error_msg is None
    assert "execution_time" in metrics_data

def test_memory_system(tester):
    """测试记忆系统"""
    result_package, metrics_data = tester.test_memory_system()
    pass_status, error_msg = result_package
    assert pass_status is True, f"Memory system failed, error: {error_msg}"
    assert error_msg is None
    assert "execution_time" in metrics_data

def test_communication_protocol(tester):
    """测试通信协议"""
    result_package, metrics_data = tester.test_communication_protocol()
    pass_status, error_msg = result_package
    assert pass_status is True, f"Communication protocol failed, error: {error_msg}"
    assert error_msg is None
    assert "execution_time" in metrics_data

@pytest.mark.skip(reason="Skipping direct test of _create_test_message, covered by other protocol tests indirectly")
def test_message_format(tester):
    """测试消息格式 (Helper method, consider if direct test needed if covered elsewhere)"""
    message = tester._create_test_message() # This is a helper, not a decorated/tested function by itself
    assert tester._validate_message_format(message) is True

@pytest.mark.skip(reason="Skipping direct test of _break_down_task, covered by planner tests")
def test_task_breakdown(tester, task_data):
    """测试任务分解 (Helper method)"""
    subtasks = tester._break_down_task(task_data)
    assert len(subtasks) > 0
    assert all("id" in st for st in subtasks)

@pytest.mark.skip(reason="Skipping direct test of _execute_task, covered by executor tests")
def test_task_execution(tester, task_data):
    """测试任务执行 (Helper method)"""
    result = tester._execute_task(task_data)
    assert result["status"] == "completed"
    assert "code" in result["result"]
    assert "coverage" in result["result"]

@pytest.mark.skip(reason="Skipping direct test of memory_operations, covered by test_memory_system")
def test_memory_operations(tester):
    """测试记忆操作 (Helper methods)"""
    assert tester._test_short_term_memory() is True
    assert tester._test_mid_term_memory() is True
    assert tester._test_long_term_memory() is True
    assert tester._test_memory_compression() is True
    assert tester._test_memory_retrieval() is True

@pytest.mark.skip(reason="Skipping direct test of _test_reliability_mechanism, covered by protocol tests")
def test_reliability_mechanism(tester):
    """测试可靠性机制 (Helper method)"""
    assert tester._test_reliability_mechanism() is True

def test_performance_metrics_structure(tester, task_data):
    """测试 @measure_performance 返回的指标结构"""
    _ , metrics_data = tester.test_planner_functionality(task_data)
    assert "execution_time" in metrics_data
    assert "memory_delta" in metrics_data
    assert "cpu_usage" in metrics_data
    assert "peak_memory" in metrics_data
    assert "timestamp" in metrics_data

def test_error_handling_invalid_task_format(tester):
    """测试错误处理 - 无效任务格式"""
    invalid_task = {"foo": "bar"}
    result_package, metrics_data = tester.test_planner_functionality(invalid_task)
    pass_status, error_msg = result_package
    assert pass_status is False, "Invalid task format test should fail pass_status."
    assert error_msg == "Invalid task format", f"Expected 'Invalid task format', got '{error_msg}'"

def test_error_handling_unsupported_task_type(tester):
    """测试错误处理 - 不支持的任务类型"""
    unsupported_task = {
        "type": "unsupported_type", 
        "description": "test", 
        "requirements": []
    }
    result_package, metrics_data = tester.test_planner_functionality(unsupported_task)
    pass_status, error_msg = result_package
    assert pass_status is False, "Unsupported task type test should fail pass_status."
    assert "Unsupported task type" in error_msg, f"Expected 'Unsupported task type' in error, got '{error_msg}'"

def test_report_generation(tester, task_data):
    """测试报告生成过程（通过run_all_tests）"""
    tester.run_all_tests() 

    assert os.path.exists("cursorrules_test_report.json")
    with open("cursorrules_test_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)
        assert "test_cases" in report
        assert len(report["test_cases"]) == 9, f"Expected 9 test cases in report, found {len(report['test_cases'])}"
        
        # Verify the intentionally failing test case details
        failing_test_entry = None
        for tc in report["test_cases"]:
            if tc["name"] == "Planner Functionality - Resource Allocation Fail":
                failing_test_entry = tc
                break
        assert failing_test_entry is not None, "Failing test case entry not found in report"
        assert failing_test_entry["result"] == "FAIL", "Failing test case should be marked FAIL"
        
        assert "performance_metrics" in report
        assert len(report["performance_metrics"]) == 9, f"Expected 9 performance metric entries, found {len(report['performance_metrics'])}"
        
        assert "errors" in report
        assert len(report["errors"]) == 1, f"Expected 1 error in report, found {len(report['errors'])}"
        if len(report["errors"]) == 1:
            assert report["errors"][0]["test"] == "Planner Functionality - Resource Allocation Fail", "Error log test name mismatch"
            assert "Invalid resource allocation" in report["errors"][0]["error"], "Error log message mismatch"
        
        assert "environment" in report

    assert os.path.exists("test_report.html")
    with open("test_report.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        assert "<h1>CursorRules Test Report</h1>" in html_content
        assert "Total Tests: 9" in html_content
        assert '<span class="pass">8</span>' in html_content
        assert '<span class="fail">1</span>' in html_content 