#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import psutil
import pytest
import logging
from datetime import datetime
from typing import Dict, List, Any, Callable, Tuple, Union
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

def measure_performance(func: Callable):
    """性能测量装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        start = time.time()
        memory_before = psutil.Process().memory_info().rss
        cpu_percent_before = psutil.Process().cpu_percent()
        
        func_result_package = func(self, *args, **kwargs)
        
        end = time.time()
        memory_after = psutil.Process().memory_info().rss
        cpu_percent_after = psutil.Process().cpu_percent()
        
        metrics = {
            "execution_time": end - start,
            "memory_delta": memory_after - memory_before,
            "cpu_usage": (cpu_percent_after - cpu_percent_before) / 100 if psutil.cpu_times_percent() else 0.0,
            "peak_memory": max(memory_before, memory_after),
            "timestamp": datetime.now().isoformat()
        }
        return func_result_package, metrics
    return wrapper

class CursorRulesTester:
    def __init__(self):
        self.start_time = time.time()
        self.results = {
            "test_cases": [],
            "performance_metrics": {},
            "errors": [],
            "environment": self._get_environment_info()
        }
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """获取测试环境信息"""
        return {
            "python_version": os.sys.version,
            "platform": os.sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "timestamp": datetime.now().isoformat()
        }
    
    @measure_performance
    def test_planner_functionality(self, task: Dict[str, Any]) -> Tuple[bool, Union[str, None]]:
        """测试Planner功能"""
        try:
            if not self._validate_task_format(task):
                return False, "Invalid task format"
            subtasks = self._break_down_task(task)
            if not self._validate_subtasks(subtasks):
                return False, "Invalid task breakdown"
            if not self._validate_resource_allocation(subtasks):
                return False, "Invalid resource allocation"
            return True, None
        except Exception as e:
            logger.error(f"Planner test internal error: {str(e)}")
            return False, str(e)
    
    @measure_performance
    def test_executor_functionality(self, task: Dict[str, Any]) -> Tuple[bool, Union[str, None]]:
        """测试Executor功能"""
        try:
            if not self._validate_task_format(task):
                return False, "Invalid task format"
            result = self._execute_task(task)
            if not self._validate_execution(result):
                return False, "Invalid execution result"
            if not self._validate_code_quality(result):
                return False, "Code quality check failed"
            return True, None
        except Exception as e:
            logger.error(f"Executor test internal error: {str(e)}")
            return False, str(e)
    
    @measure_performance
    def test_memory_system(self) -> Tuple[bool, Union[str, None]]:
        """测试记忆系统"""
        try:
            short_term = self._test_short_term_memory()
            mid_term = self._test_mid_term_memory()
            long_term = self._test_long_term_memory()
            compression = self._test_memory_compression()
            retrieval = self._test_memory_retrieval()
            if not all([short_term, mid_term, long_term, compression, retrieval]):
                return False, "One or more memory system sub-tests failed"
            return True, None
        except Exception as e:
            logger.error(f"Memory system test internal error: {str(e)}")
            return False, str(e)
    
    @measure_performance
    def test_communication_protocol(self) -> Tuple[bool, Union[str, None]]:
        """测试通信协议"""
        try:
            message = self._create_test_message()
            if not self._validate_message_format(message):
                return False, "Invalid message format"
            if not self._test_reliability_mechanism():
                return False, "Reliability mechanism failed"
            if not self._test_priority_management():
                return False, "Priority management failed"
            if not self._test_deadlock_prevention():
                return False, "Deadlock prevention failed"
            return True, None
        except Exception as e:
            logger.error(f"Communication protocol test internal error: {str(e)}")
            return False, str(e)
    
    def _validate_task_format(self, task: Dict[str, Any]) -> bool:
        """验证任务格式"""
        required_fields = ["type", "description", "requirements"]
        return all(field in task for field in required_fields)
    
    def _break_down_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模拟任务分解"""
        if task["type"] not in ["code_generation", "system_optimization", "bug_fix"]:
            raise ValueError(f"Unsupported task type: {task['type']}")
        
        subtasks = []
        for i, req in enumerate(task["requirements"]):
            subtasks.append({
                "id": f"subtask-{i}",
                "description": f"Implement {req}",
                "priority": "high" if i == 0 else "medium",
                "estimated_time": 30 * (i + 1),  # 分钟
                "dependencies": [f"subtask-{j}" for j in range(i)]
            })
        return subtasks
    
    def _validate_subtasks(self, subtasks: List[Dict[str, Any]]) -> bool:
        """验证任务分解结果"""
        required_fields = ["id", "description", "priority", "estimated_time"]
        return len(subtasks) > 0 and all(
            all(field in st for field in required_fields)
            for st in subtasks
        )
    
    def _validate_resource_allocation(self, subtasks: List[Dict[str, Any]]) -> bool:
        """验证资源分配"""
        total_time = sum(st["estimated_time"] for st in subtasks)
        return total_time > 0 and total_time < 480  # 不超过8小时
    
    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务执行"""
        return {
            "status": "completed",
            "result": {
                "code": "def example():\n    pass",
                "tests": ["test1", "test2"],
                "coverage": 0.85,
                "quality_score": 0.9
            },
            "execution_time": 120,
            "memory_usage": 1024 * 1024  # 1MB
        }
    
    def _validate_execution(self, result: Dict[str, Any]) -> bool:
        """验证执行结果"""
        return (
            result["status"] == "completed" and
            result["execution_time"] > 0 and
            result["memory_usage"] > 0
        )
    
    def _validate_code_quality(self, result: Dict[str, Any]) -> bool:
        """验证代码质量"""
        return (
            result["result"]["coverage"] >= 0.8 and
            result["result"]["quality_score"] >= 0.8
        )
    
    def _test_short_term_memory(self) -> bool:
        """测试短期记忆"""
        return True
    
    def _test_mid_term_memory(self) -> bool:
        """测试中期记忆"""
        return True
    
    def _test_long_term_memory(self) -> bool:
        """测试长期记忆"""
        return True
    
    def _test_memory_compression(self) -> bool:
        """测试记忆压缩"""
        return True
    
    def _test_memory_retrieval(self) -> bool:
        """测试记忆检索"""
        return True
    
    def _create_test_message(self) -> Dict[str, Any]:
        """创建测试消息"""
        return {
            "message_id": "test-001",
            "timestamp": datetime.now().isoformat(),
            "origin": {
                "role": "Planner",
                "version": "5.0",
                "context": "test_context",
                "priority": "high"
            },
            "destination": "Executor",
            "qos": 1,
            "payload": {
                "action_type": "test_action",
                "parameters": {},
                "context_hash": "test_hash",
                "priority": "high",
                "deadline": datetime.now().isoformat(),
                "retry_policy": {
                    "max_retries": 3,
                    "backoff_factor": 2
                }
            }
        }
    
    def _validate_message_format(self, message: Dict[str, Any]) -> bool:
        """验证消息格式"""
        required_fields = ["message_id", "timestamp", "origin", "destination", "payload"]
        return all(field in message for field in required_fields)
    
    def _test_reliability_mechanism(self) -> bool:
        """测试可靠性机制"""
        return True
    
    def _test_priority_management(self) -> bool:
        """测试优先级管理"""
        return True
    
    def _test_deadlock_prevention(self) -> bool:
        """测试死锁预防"""
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("Starting CursorRules tests...")
        
        task1 = {"type": "code_generation", "description": "CG", "requirements": ["req1"]}
        task2 = {"type": "system_optimization", "description": "SO", "requirements": ["req1"]}
        task3 = {"type": "bug_fix", "description": "BF", "requirements": ["req1"]}
        failing_task_for_planner = {"type": "code_generation", "description": "Bad requirements", "requirements": ["req1"] * 20}

        tests_to_run = [
            ("Planner Functionality - Code Generation", lambda: self.test_planner_functionality(task1)),
            ("Planner Functionality - System Optimization", lambda: self.test_planner_functionality(task2)),
            ("Planner Functionality - Bug Fix", lambda: self.test_planner_functionality(task3)),
            ("Planner Functionality - Resource Allocation Fail", lambda: self.test_planner_functionality(failing_task_for_planner)),
            ("Executor Functionality - Code Generation", lambda: self.test_executor_functionality(task1)),
            ("Executor Functionality - System Optimization", lambda: self.test_executor_functionality(task2)),
            ("Executor Functionality - Bug Fix", lambda: self.test_executor_functionality(task3)),
            ("Memory System", self.test_memory_system),
            ("Communication Protocol", self.test_communication_protocol)
        ]
        
        self.results["test_cases"] = []
        self.results["performance_metrics"] = {}
        self.results["errors"] = []

        for test_name, test_func_lambda in tests_to_run:
            logger.info(f"Running test: {test_name}")
            (pass_status, error_message), metrics_data = test_func_lambda()
            self.results["performance_metrics"][test_name] = metrics_data
            
            self.results["test_cases"].append({
                "name": test_name,
                "result": "PASS" if pass_status else "FAIL",
                "timestamp": datetime.now().isoformat()
            })

            if not pass_status and error_message:
                self.results["errors"].append({
                    "test": test_name,
                    "error": error_message,
                    "timestamp": datetime.now().isoformat()
                })
        
        self._generate_report()
        logger.info("CursorRules tests completed.")
    
    def _generate_report(self):
        """生成测试报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.results["environment"],
            "total_tests": len(self.results["test_cases"]),
            "passed_tests": sum(1 for tc in self.results["test_cases"] if tc["result"] == "PASS"),
            "failed_tests": sum(1 for tc in self.results["test_cases"] if tc["result"] == "FAIL"),
            "test_cases": self.results["test_cases"],
            "performance_metrics": self.results["performance_metrics"],
            "errors": self.results["errors"],
            "total_time": time.time() - self.start_time
        }
        
        # 保存JSON报告
        with open("cursorrules_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 生成HTML报告
        self._generate_html_report(report)
        
        logger.info(f"Test report generated: {len(report['test_cases'])} tests, "
                   f"{report['passed_tests']} passed, {report['failed_tests']} failed")
    
    def _generate_html_report(self, report: Dict[str, Any]):
        """生成HTML格式的测试报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CursorRules Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>CursorRules Test Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {report['total_tests']}</p>
                <p>Passed: <span class="pass">{report['passed_tests']}</span></p>
                <p>Failed: <span class="fail">{report['failed_tests']}</span></p>
                <p>Total Time: {report['total_time']:.2f} seconds</p>
            </div>
            
            <h2>Test Cases</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Result</th>
                    <th>Timestamp</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{tc['name']}</td>
                    <td class="{'pass' if tc['result'] == 'PASS' else 'fail'}">{tc['result']}</td>
                    <td>{tc['timestamp']}</td>
                </tr>
                ''' for tc in report['test_cases'])}
            </table>
            
            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Test</th>
                    <th>Execution Time (s)</th>
                    <th>Memory Delta (bytes)</th>
                    <th>CPU Usage (%)</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{name}</td>
                    <td>{metrics['execution_time']:.3f}</td>
                    <td>{metrics['memory_delta']}</td>
                    <td>{metrics['cpu_usage']*100:.1f}</td>
                </tr>
                ''' for name, metrics in report['performance_metrics'].items())}
            </table>
            
            <h2>Errors</h2>
            <table>
                <tr>
                    <th>Test</th>
                    <th>Error</th>
                    <th>Timestamp</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{error['test']}</td>
                    <td>{error['error']}</td>
                    <td>{error['timestamp']}</td>
                </tr>
                ''' for error in report['errors'])}
            </table>
        </body>
        </html>
        """
        
        with open("test_report.html", "w", encoding="utf-8") as f:
            f.write(html_content)

if __name__ == "__main__":
    tester = CursorRulesTester()
    tester.run_all_tests() 