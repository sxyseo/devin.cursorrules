#!/usr/bin/env python3
"""
MCP服务调试工具

提供MCP服务的监控和调试功能，包括实时日志查看、性能监控和组件状态检查等。
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
import threading
import psutil
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('mcp_debug')

# 添加父目录到系统路径以便导入工具模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# MCP服务地址
MCP_SERVICE_URL = os.environ.get("MCP_SERVICE_URL", "http://localhost:8000")

# 全局控制台对象
console = Console()

class MCPDebugger:
    """MCP服务调试器"""
    
    def __init__(self, service_url=MCP_SERVICE_URL):
        """初始化调试器
        
        Args:
            service_url: MCP服务地址
        """
        self.service_url = service_url
        self.console = Console()
        self.logs = []
        self.metrics = {
            "requests": [],
            "response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "timestamps": []
        }
        self.max_history = 100  # 最大历史记录数
        self.mcp_pid = None
        self.running = False
        
        # 查找MCP进程PID
        self._find_mcp_process()
    
    def _find_mcp_process(self):
        """查找MCP服务进程"""
        # 尝试多种可能的进程名称
        possible_names = ["multi_agent_mcp", "python -m multi_agent_mcp", "fastmcp"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 检查进程名
                if any(name in proc.info['name'].lower() for name in possible_names):
                    self.mcp_pid = proc.info['pid']
                    return
                
                # 检查命令行
                if proc.info['cmdline']:
                    cmdline = " ".join(proc.info['cmdline']).lower()
                    if any(name in cmdline for name in possible_names):
                        self.mcp_pid = proc.info['pid']
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    
    def check_service_status(self):
        """检查MCP服务状态"""
        try:
            # 调用健康检查API
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "online", "details": response.json()}
            else:
                return {"status": "error", "details": f"HTTP错误: {response.status_code}"}
        except requests.RequestException as e:
            return {"status": "offline", "details": str(e)}
    
    def call_tool(self, tool_name, params={}):
        """调用MCP工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
        
        Returns:
            工具调用结果
        """
        start_time = time.time()
        try:
            url = f"{self.service_url}/tools/{tool_name}"
            response = requests.post(url, json=params, timeout=10)
            elapsed = time.time() - start_time
            
            # 记录请求信息
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "params": params,
                "status_code": response.status_code,
                "elapsed_time": elapsed
            }
            self.logs.append(log_entry)
            
            # 保持日志大小在限制内
            if len(self.logs) > self.max_history:
                self.logs = self.logs[-self.max_history:]
            
            # 记录指标
            self._record_metrics(elapsed)
            
            if response.status_code == 200:
                return response.text
            else:
                return f"请求失败，状态码: {response.status_code}, 响应: {response.text}"
        except Exception as e:
            elapsed = time.time() - start_time
            
            # 记录错误信息
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "params": params,
                "error": str(e),
                "elapsed_time": elapsed
            }
            self.logs.append(log_entry)
            
            # 记录指标
            self._record_metrics(elapsed)
            
            return f"调用MCP服务失败: {str(e)}"
    
    def _record_metrics(self, response_time):
        """记录性能指标
        
        Args:
            response_time: 响应时间
        """
        timestamp = datetime.now()
        
        # 记录请求计数和响应时间
        self.metrics["requests"].append(1)
        self.metrics["response_times"].append(response_time)
        self.metrics["timestamps"].append(timestamp)
        
        # 记录进程资源使用情况
        if self.mcp_pid:
            try:
                process = psutil.Process(self.mcp_pid)
                with process.oneshot():
                    # 获取内存使用率 (RSS, 单位：MB)
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    self.metrics["memory_usage"].append(memory_mb)
                    
                    # 获取CPU使用率
                    cpu_percent = process.cpu_percent(interval=0.1)
                    self.metrics["cpu_usage"].append(cpu_percent)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.metrics["memory_usage"].append(0)
                self.metrics["cpu_usage"].append(0)
                self.mcp_pid = None  # 进程不存在，重置PID
        else:
            self.metrics["memory_usage"].append(0)
            self.metrics["cpu_usage"].append(0)
            # 尝试重新查找进程
            self._find_mcp_process()
        
        # 保持指标记录在最大历史记录数内
        for key in self.metrics:
            if len(self.metrics[key]) > self.max_history:
                self.metrics[key] = self.metrics[key][-self.max_history:]
    
    def generate_component_table(self):
        """生成组件状态表格"""
        # 获取组件状态
        health_info = self.check_service_status()
        
        # 创建表格
        table = Table(title="MCP组件状态")
        table.add_column("组件名称", style="cyan")
        table.add_column("状态", style="green")
        
        if health_info["status"] == "online" and "details" in health_info:
            details = health_info["details"]
            if "components" in details:
                components = details["components"]
                for component, status in components.items():
                    status_style = "green" if status == "online" else "red"
                    table.add_row(component, Text(status, style=status_style))
        else:
            table.add_row("MCP服务", Text(health_info["status"], style="red"))
        
        return table
    
    def generate_performance_table(self):
        """生成性能指标表格"""
        table = Table(title="性能指标")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="yellow")
        
        # 计算平均响应时间
        if self.metrics["response_times"]:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            table.add_row("平均响应时间", f"{avg_response_time:.4f} 秒")
        else:
            table.add_row("平均响应时间", "N/A")
        
        # 计算请求速率
        if len(self.metrics["timestamps"]) >= 2:
            first_ts = self.metrics["timestamps"][0]
            last_ts = self.metrics["timestamps"][-1]
            duration = (last_ts - first_ts).total_seconds()
            if duration > 0:
                req_rate = len(self.metrics["timestamps"]) / duration
                table.add_row("请求速率", f"{req_rate:.2f} 请求/秒")
            else:
                table.add_row("请求速率", "N/A")
        else:
            table.add_row("请求速率", "N/A")
        
        # 显示最新的内存使用和CPU使用
        if self.metrics["memory_usage"]:
            table.add_row("内存使用", f"{self.metrics['memory_usage'][-1]:.2f} MB")
        else:
            table.add_row("内存使用", "N/A")
        
        if self.metrics["cpu_usage"]:
            table.add_row("CPU使用率", f"{self.metrics['cpu_usage'][-1]:.2f}%")
        else:
            table.add_row("CPU使用率", "N/A")
        
        # MCP进程ID
        if self.mcp_pid:
            table.add_row("进程ID", str(self.mcp_pid))
        else:
            table.add_row("进程ID", "未找到")
        
        return table
    
    def generate_log_table(self, max_entries=10):
        """生成日志表格
        
        Args:
            max_entries: 最大显示条目数
        """
        table = Table(title="最近API调用")
        table.add_column("时间", style="dim")
        table.add_column("工具", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("响应时间", style="yellow")
        
        # 显示最近的日志条目
        recent_logs = self.logs[-max_entries:] if self.logs else []
        for log in recent_logs:
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            tool = log["tool"]
            
            # 确定状态样式
            if "error" in log:
                status = "错误"
                status_style = "red"
            elif "status_code" in log and log["status_code"] == 200:
                status = "成功"
                status_style = "green"
            else:
                status = f"HTTP {log.get('status_code', 'N/A')}"
                status_style = "yellow"
            
            elapsed = f"{log.get('elapsed_time', 0):.4f}s"
            
            table.add_row(
                timestamp, 
                tool, 
                Text(status, style=status_style),
                elapsed
            )
        
        return table
    
    def plot_performance_metrics(self, output_file=None):
        """绘制性能指标图表
        
        Args:
            output_file: 输出文件路径
        """
        if not self.metrics["timestamps"]:
            print("没有足够的性能数据可供绘制")
            return
        
        # 创建图表
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
        
        # 转换时间戳为相对时间（秒）
        start_time = self.metrics["timestamps"][0]
        relative_times = [(ts - start_time).total_seconds() for ts in self.metrics["timestamps"]]
        
        # 绘制响应时间
        ax1.plot(relative_times, self.metrics["response_times"], 'b-')
        ax1.set_title('响应时间')
        ax1.set_ylabel('时间 (秒)')
        ax1.grid(True)
        
        # 绘制内存使用
        ax2.plot(relative_times, self.metrics["memory_usage"], 'g-')
        ax2.set_title('内存使用')
        ax2.set_ylabel('内存 (MB)')
        ax2.grid(True)
        
        # 绘制CPU使用率
        ax3.plot(relative_times, self.metrics["cpu_usage"], 'r-')
        ax3.set_title('CPU使用率')
        ax3.set_xlabel('时间 (秒)')
        ax3.set_ylabel('CPU (%)')
        ax3.grid(True)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示图表
        if output_file:
            plt.savefig(output_file)
            print(f"性能指标图表已保存至: {output_file}")
        else:
            plt.show()
    
    def run_monitoring_dashboard(self):
        """运行实时监控仪表板"""
        self.running = True
        
        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1)
        )
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        layout["left"].split_column(
            Layout(name="components"),
            Layout(name="performance")
        )
        layout["right"].split_column(
            Layout(name="logs")
        )
        
        def get_header():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return Panel(f"MCP服务监控仪表板 - {now}\n服务地址: {self.service_url}", style="bold blue")
        
        # 更新监控数据的线程
        def update_metrics():
            while self.running:
                # 检查服务状态
                self.check_service_status()
                
                # 使用服务健康检查API更新指标
                self.call_tool("check_health")
                
                # 每5秒更新一次
                time.sleep(5)
        
        # 启动更新线程
        update_thread = threading.Thread(target=update_metrics)
        update_thread.daemon = True
        update_thread.start()
        
        try:
            # 创建实时更新的仪表板
            with Live(layout, refresh_per_second=1, screen=True):
                while self.running:
                    # 更新布局组件
                    layout["header"].update(get_header())
                    layout["components"].update(self.generate_component_table())
                    layout["performance"].update(self.generate_performance_table())
                    layout["logs"].update(self.generate_log_table())
                    
                    # 等待刷新
                    time.sleep(1)
        except KeyboardInterrupt:
            print("监控已停止")
        finally:
            self.running = False
    
    def run_load_test(self, requests_per_second=1, duration_seconds=60):
        """运行负载测试
        
        Args:
            requests_per_second: 每秒请求数
            duration_seconds: 测试持续时间（秒）
        """
        console.print(f"开始MCP服务负载测试", style="bold green")
        console.print(f"请求速率: {requests_per_second} 请求/秒", style="bold yellow")
        console.print(f"持续时间: {duration_seconds} 秒", style="bold yellow")
        
        # 测试开始时间
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        # 请求计数器
        request_count = 0
        success_count = 0
        error_count = 0
        
        # 响应时间统计
        response_times = []
        
        # 每个请求之间的延迟（秒）
        delay = 1.0 / requests_per_second
        
        # 测试工具列表和参数
        test_tools = [
            ("read_memory", {"file_path": "activeContext.md"}),
            ("list_memory_files", {}),
            ("search_memory", {"query": "测试", "top_k": 3}),
            ("check_health", {})
        ]
        
        try:
            with console.status("[bold green]正在执行负载测试...") as status:
                while time.time() < end_time:
                    # 选择测试工具
                    tool_index = request_count % len(test_tools)
                    tool_name, params = test_tools[tool_index]
                    
                    # 发送请求
                    result = self.call_tool(tool_name, params)
                    request_count += 1
                    
                    # 统计结果
                    if "错误" in result or "请求失败" in result:
                        error_count += 1
                    else:
                        success_count += 1
                    
                    # 获取最近的响应时间
                    if self.logs and "elapsed_time" in self.logs[-1]:
                        response_times.append(self.logs[-1]["elapsed_time"])
                    
                    # 更新状态消息
                    elapsed = time.time() - start_time
                    status.update(f"[bold green]正在执行负载测试... 已发送 {request_count} 请求，成功 {success_count}，失败 {error_count}，已用时 {elapsed:.1f} 秒")
                    
                    # 等待下一个请求时间
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            console.print("\n负载测试被用户中断", style="bold red")
        
        # 计算测试结果
        total_elapsed = time.time() - start_time
        actual_rps = request_count / total_elapsed if total_elapsed > 0 else 0
        
        # 计算响应时间统计
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # 绘制性能指标图
        output_file = f"mcp_load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.plot_performance_metrics(output_file)
        
        # 打印测试结果
        result_table = Table(title="负载测试结果")
        result_table.add_column("指标", style="cyan")
        result_table.add_column("值", style="yellow")
        
        result_table.add_row("总请求数", str(request_count))
        result_table.add_row("成功请求数", str(success_count))
        result_table.add_row("失败请求数", str(error_count))
        result_table.add_row("成功率", f"{success_count/request_count*100:.2f}%" if request_count > 0 else "N/A")
        result_table.add_row("实际请求速率", f"{actual_rps:.2f} 请求/秒")
        result_table.add_row("平均响应时间", f"{avg_response_time:.4f} 秒")
        result_table.add_row("最小响应时间", f"{min_response_time:.4f} 秒")
        result_table.add_row("最大响应时间", f"{max_response_time:.4f} 秒")
        result_table.add_row("性能指标图表", output_file)
        
        console.print(result_table)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="MCP服务调试工具")
    parser.add_argument("--url", default=MCP_SERVICE_URL, help="MCP服务地址")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 状态检查命令
    status_parser = subparsers.add_parser("status", help="检查MCP服务状态")
    
    # 调用工具命令
    call_parser = subparsers.add_parser("call", help="调用MCP工具")
    call_parser.add_argument("tool", help="工具名称")
    call_parser.add_argument("--params", default="{}", help="工具参数 (JSON格式)")
    
    # 监控命令
    monitor_parser = subparsers.add_parser("monitor", help="运行监控仪表板")
    
    # 负载测试命令
    loadtest_parser = subparsers.add_parser("loadtest", help="运行负载测试")
    loadtest_parser.add_argument("--rps", type=float, default=1.0, help="每秒请求数")
    loadtest_parser.add_argument("--duration", type=int, default=60, help="测试持续时间（秒）")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 初始化调试器
    debugger = MCPDebugger(service_url=args.url)
    
    if args.command == "status":
        # 显示服务状态
        status = debugger.check_service_status()
        console.print(f"MCP服务状态: {status['status']}", style="bold blue")
        
        if status["status"] == "online" and "details" in status:
            # 显示组件表格
            console.print(debugger.generate_component_table())
    
    elif args.command == "call":
        # 调用工具
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            console.print("参数格式错误，应为有效的JSON", style="bold red")
            return
        
        console.print(f"调用工具: {args.tool}", style="bold blue")
        console.print(f"参数: {params}", style="cyan")
        
        result = debugger.call_tool(args.tool, params)
        console.print("结果:", style="green")
        
        # 尝试将结果格式化为JSON
        try:
            json_result = json.loads(result)
            console.print_json(data=json_result)
        except json.JSONDecodeError:
            console.print(result)
    
    elif args.command == "monitor":
        # 运行监控仪表板
        debugger.run_monitoring_dashboard()
    
    elif args.command == "loadtest":
        # 运行负载测试
        debugger.run_load_test(
            requests_per_second=args.rps,
            duration_seconds=args.duration
        )
    
    else:
        # 默认显示状态
        status = debugger.check_service_status()
        console.print(f"MCP服务状态: {status['status']}", style="bold blue")
        
        if status["status"] == "online" and "details" in status:
            # 显示组件表格
            console.print(debugger.generate_component_table())
        
        # 显示可用命令
        console.print("\n可用命令:", style="bold cyan")
        console.print("  status    - 检查MCP服务状态")
        console.print("  call      - 调用MCP工具")
        console.print("  monitor   - 运行监控仪表板")
        console.print("  loadtest  - 运行负载测试")

if __name__ == "__main__":
    main() 