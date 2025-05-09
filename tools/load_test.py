#!/usr/bin/env python3
"""
MCP服务负载测试脚本

对MCP服务进行压力测试，测试其在高并发请求下的性能和稳定性。
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import statistics
import aiohttp
import websockets
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from pathlib import Path
from tabulate import tabulate
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('load_test')

# 添加父目录到系统路径以便导入工具模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 服务地址
HTTP_SERVICE_URL = os.environ.get("MCP_HTTP_URL", "http://localhost:8000")
WS_SERVICE_URL = os.environ.get("MCP_WS_URL", "ws://localhost:8765")

class LoadTest:
    """MCP服务负载测试"""
    
    def __init__(self, http_url=HTTP_SERVICE_URL, ws_url=WS_SERVICE_URL):
        """初始化负载测试类
        
        Args:
            http_url: HTTP接口URL
            ws_url: WebSocket接口URL
        """
        self.http_url = http_url
        self.ws_url = ws_url
        self.results = {
            "http": {},
            "ws": {}
        }
        self.metrics = {
            "http": {},
            "ws": {}
        }
    
    async def http_health_request(self, session):
        """发送HTTP健康检查请求
        
        Args:
            session: aiohttp会话
        
        Returns:
            响应时间(秒)
        """
        start_time = time.time()
        try:
            async with session.get(f"{self.http_url}/health") as response:
                await response.text()
                return time.time() - start_time, response.status == 200
        except Exception as e:
            logger.error(f"HTTP健康检查请求失败: {e}")
            return time.time() - start_time, False
    
    async def http_tool_request(self, session, tool_name, params):
        """发送HTTP工具调用请求
        
        Args:
            session: aiohttp会话
            tool_name: 工具名称
            params: 请求参数
        
        Returns:
            响应时间(秒)
        """
        start_time = time.time()
        try:
            async with session.post(f"{self.http_url}/tools/{tool_name}", json=params) as response:
                await response.text()
                return time.time() - start_time, response.status == 200
        except Exception as e:
            logger.error(f"HTTP工具请求失败: {e}")
            return time.time() - start_time, False
    
    async def ws_connection(self):
        """建立WebSocket连接并注册智能体
        
        Returns:
            tuple: (websocket连接, 是否成功)
        """
        try:
            websocket = await websockets.connect(self.ws_url)
            # 接收欢迎消息
            welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            # 发送注册消息
            register_msg = {
                "type": "register",
                "agent_type": "planner",
                "agent_id": f"load-test-{int(time.time())}-{id(websocket)}"
            }
            await websocket.send(json.dumps(register_msg))
            
            # 接收注册确认
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            return websocket, True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return None, False
    
    async def ws_message_request(self, websocket):
        """通过WebSocket发送消息请求
        
        Args:
            websocket: WebSocket连接
        
        Returns:
            响应时间(秒)
        """
        start_time = time.time()
        try:
            # 发送消息
            message = {
                "type": "ping",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(message))
            
            # 接收响应
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            return time.time() - start_time, True
        except Exception as e:
            logger.error(f"WebSocket消息请求失败: {e}")
            return time.time() - start_time, False
    
    async def ws_task_request(self, websocket):
        """通过WebSocket发送任务创建请求
        
        Args:
            websocket: WebSocket连接
        
        Returns:
            响应时间(秒)
        """
        start_time = time.time()
        try:
            # 发送任务创建消息
            task_msg = {
                "type": "create_task",
                "description": f"负载测试任务 {time.strftime('%Y%m%d%H%M%S')}",
                "priority": "low"
            }
            await websocket.send(json.dumps(task_msg))
            
            # 接收响应
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            return time.time() - start_time, True
        except Exception as e:
            logger.error(f"WebSocket任务请求失败: {e}")
            return time.time() - start_time, False
    
    async def http_load_test(self, requests_per_second, duration, endpoints=None):
        """进行HTTP负载测试
        
        Args:
            requests_per_second: 每秒请求数
            duration: 测试持续时间(秒)
            endpoints: 要测试的端点列表，默认为None(测试所有端点)
        """
        if endpoints is None:
            endpoints = [
                ("health", {}),
                ("memory_list", {}),
                ("task_create", {"description": "负载测试任务", "priority": "low"}),
                ("task_list", {})
            ]
        
        logger.info(f"开始HTTP负载测试: {requests_per_second} 请求/秒, 持续 {duration} 秒")
        
        # 创建客户端会话
        async with aiohttp.ClientSession() as session:
            total_requests = requests_per_second * duration
            tasks = []
            
            # 创建所有请求任务
            for _ in range(total_requests):
                for endpoint, params in endpoints:
                    if endpoint == "health":
                        tasks.append(self.http_health_request(session))
                    else:
                        tool_name = endpoint.replace("_", "_")
                        tasks.append(self.http_tool_request(session, tool_name, params))
            
            # 控制请求速率
            chunk_size = requests_per_second * len(endpoints)
            with tqdm(total=len(tasks), desc="HTTP请求进度") as pbar:
                for i in range(0, len(tasks), chunk_size):
                    chunk = tasks[i:i+chunk_size]
                    results = await asyncio.gather(*chunk, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            response_time, success = result
                            if "response_times" not in self.results["http"]:
                                self.results["http"]["response_times"] = []
                            if "success_count" not in self.results["http"]:
                                self.results["http"]["success_count"] = 0
                            if "error_count" not in self.results["http"]:
                                self.results["http"]["error_count"] = 0
                            
                            self.results["http"]["response_times"].append(response_time)
                            
                            if success:
                                self.results["http"]["success_count"] += 1
                            else:
                                self.results["http"]["error_count"] += 1
                    
                    pbar.update(len(chunk))
                    
                    # 控制请求速率
                    if i + chunk_size < len(tasks):
                        await asyncio.sleep(1)
        
        # 计算统计数据
        if "response_times" in self.results["http"]:
            times = self.results["http"]["response_times"]
            self.metrics["http"] = {
                "total_requests": len(times),
                "success_rate": self.results["http"]["success_count"] / len(times) * 100 if len(times) > 0 else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0,
                "avg_time": statistics.mean(times) if times else 0,
                "median_time": statistics.median(times) if times else 0,
                "p95_time": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else 0,
                "p99_time": sorted(times)[int(len(times) * 0.99)] if len(times) > 100 else 0,
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
                "requests_per_second": len(times) / duration if duration > 0 else 0
            }
        
        logger.info("HTTP负载测试完成")
    
    async def ws_load_test(self, connections, messages_per_connection, interval=1.0):
        """进行WebSocket负载测试
        
        Args:
            connections: 并发连接数
            messages_per_connection: 每个连接发送的消息数
            interval: 消息发送间隔(秒)
        """
        logger.info(f"开始WebSocket负载测试: {connections} 连接, 每个连接 {messages_per_connection} 消息")
        
        # 创建所有WebSocket连接
        websockets_list = []
        for _ in range(connections):
            websocket, success = await self.ws_connection()
            if success:
                websockets_list.append(websocket)
        
        if not websockets_list:
            logger.error("无法建立任何WebSocket连接，测试中止")
            return
        
        logger.info(f"成功建立 {len(websockets_list)} 个WebSocket连接")
        
        try:
            # 为每个连接发送消息
            with tqdm(total=len(websockets_list) * messages_per_connection, desc="WebSocket消息进度") as pbar:
                for _ in range(messages_per_connection):
                    tasks = []
                    for websocket in websockets_list:
                        tasks.append(self.ws_message_request(websocket))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            response_time, success = result
                            if "response_times" not in self.results["ws"]:
                                self.results["ws"]["response_times"] = []
                            if "success_count" not in self.results["ws"]:
                                self.results["ws"]["success_count"] = 0
                            if "error_count" not in self.results["ws"]:
                                self.results["ws"]["error_count"] = 0
                            
                            self.results["ws"]["response_times"].append(response_time)
                            
                            if success:
                                self.results["ws"]["success_count"] += 1
                            else:
                                self.results["ws"]["error_count"] += 1
                    
                    pbar.update(len(tasks))
                    
                    # 控制发送速率
                    await asyncio.sleep(interval)
            
            # 任务创建测试
            logger.info("开始WebSocket任务创建测试")
            with tqdm(total=len(websockets_list), desc="WebSocket任务创建进度") as pbar:
                tasks = []
                for websocket in websockets_list:
                    tasks.append(self.ws_task_request(websocket))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, tuple) and len(result) == 2:
                        response_time, success = result
                        if "task_response_times" not in self.results["ws"]:
                            self.results["ws"]["task_response_times"] = []
                        if "task_success_count" not in self.results["ws"]:
                            self.results["ws"]["task_success_count"] = 0
                        if "task_error_count" not in self.results["ws"]:
                            self.results["ws"]["task_error_count"] = 0
                        
                        self.results["ws"]["task_response_times"].append(response_time)
                        
                        if success:
                            self.results["ws"]["task_success_count"] += 1
                        else:
                            self.results["ws"]["task_error_count"] += 1
                
                pbar.update(len(tasks))
        
        finally:
            # 关闭所有WebSocket连接
            for websocket in websockets_list:
                try:
                    await websocket.close()
                except:
                    pass
        
        # 计算统计数据
        if "response_times" in self.results["ws"]:
            times = self.results["ws"]["response_times"]
            total_duration = messages_per_connection * interval
            self.metrics["ws"] = {
                "total_connections": connections,
                "successful_connections": len(websockets_list),
                "total_messages": len(times),
                "success_rate": self.results["ws"]["success_count"] / len(times) * 100 if len(times) > 0 else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0,
                "avg_time": statistics.mean(times) if times else 0,
                "median_time": statistics.median(times) if times else 0,
                "p95_time": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else 0,
                "p99_time": sorted(times)[int(len(times) * 0.99)] if len(times) > 100 else 0,
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
                "messages_per_second": len(times) / total_duration if total_duration > 0 else 0
            }
        
        if "task_response_times" in self.results["ws"]:
            task_times = self.results["ws"]["task_response_times"]
            if task_times:
                self.metrics["ws"].update({
                    "task_min_time": min(task_times),
                    "task_max_time": max(task_times),
                    "task_avg_time": statistics.mean(task_times),
                    "task_median_time": statistics.median(task_times),
                    "task_success_rate": self.results["ws"]["task_success_count"] / len(task_times) * 100
                })
        
        logger.info("WebSocket负载测试完成")
    
    def display_results(self):
        """显示测试结果"""
        # 显示HTTP测试结果
        if "http" in self.metrics and self.metrics["http"]:
            print("\n" + "="*50)
            print("HTTP负载测试结果:")
            print("="*50)
            
            http_data = [
                ["总请求数", self.metrics["http"].get("total_requests", 0)],
                ["成功率", f"{self.metrics['http'].get('success_rate', 0):.2f}%"],
                ["每秒请求数", f"{self.metrics['http'].get('requests_per_second', 0):.2f}"],
                ["最小响应时间", f"{self.metrics['http'].get('min_time', 0)*1000:.2f} ms"],
                ["最大响应时间", f"{self.metrics['http'].get('max_time', 0)*1000:.2f} ms"],
                ["平均响应时间", f"{self.metrics['http'].get('avg_time', 0)*1000:.2f} ms"],
                ["中位响应时间", f"{self.metrics['http'].get('median_time', 0)*1000:.2f} ms"],
                ["95百分位响应时间", f"{self.metrics['http'].get('p95_time', 0)*1000:.2f} ms"],
                ["99百分位响应时间", f"{self.metrics['http'].get('p99_time', 0)*1000:.2f} ms"],
                ["标准差", f"{self.metrics['http'].get('std_dev', 0)*1000:.2f} ms"]
            ]
            
            print(tabulate(http_data, tablefmt="grid"))
        
        # 显示WebSocket测试结果
        if "ws" in self.metrics and self.metrics["ws"]:
            print("\n" + "="*50)
            print("WebSocket负载测试结果:")
            print("="*50)
            
            ws_data = [
                ["尝试连接数", self.metrics["ws"].get("total_connections", 0)],
                ["成功连接数", self.metrics["ws"].get("successful_connections", 0)],
                ["总消息数", self.metrics["ws"].get("total_messages", 0)],
                ["消息成功率", f"{self.metrics['ws'].get('success_rate', 0):.2f}%"],
                ["每秒消息数", f"{self.metrics['ws'].get('messages_per_second', 0):.2f}"],
                ["最小响应时间", f"{self.metrics['ws'].get('min_time', 0)*1000:.2f} ms"],
                ["最大响应时间", f"{self.metrics['ws'].get('max_time', 0)*1000:.2f} ms"],
                ["平均响应时间", f"{self.metrics['ws'].get('avg_time', 0)*1000:.2f} ms"],
                ["中位响应时间", f"{self.metrics['ws'].get('median_time', 0)*1000:.2f} ms"],
                ["95百分位响应时间", f"{self.metrics['ws'].get('p95_time', 0)*1000:.2f} ms"],
                ["99百分位响应时间", f"{self.metrics['ws'].get('p99_time', 0)*1000:.2f} ms"],
                ["标准差", f"{self.metrics['ws'].get('std_dev', 0)*1000:.2f} ms"]
            ]
            
            if "task_avg_time" in self.metrics["ws"]:
                ws_data.extend([
                    ["任务创建成功率", f"{self.metrics['ws'].get('task_success_rate', 0):.2f}%"],
                    ["任务最小响应时间", f"{self.metrics['ws'].get('task_min_time', 0)*1000:.2f} ms"],
                    ["任务最大响应时间", f"{self.metrics['ws'].get('task_max_time', 0)*1000:.2f} ms"],
                    ["任务平均响应时间", f"{self.metrics['ws'].get('task_avg_time', 0)*1000:.2f} ms"],
                    ["任务中位响应时间", f"{self.metrics['ws'].get('task_median_time', 0)*1000:.2f} ms"]
                ])
            
            print(tabulate(ws_data, tablefmt="grid"))
    
    def generate_report(self, output_dir="./reports"):
        """生成测试报告
        
        Args:
            output_dir: 报告输出目录
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"load_test_report_{report_time}.json")
        plot_file = os.path.join(output_dir, f"load_test_plot_{report_time}.png")
        
        # 保存测试数据
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "http_url": self.http_url,
                "ws_url": self.ws_url,
                "metrics": self.metrics,
                "results": {
                    "http": {
                        k: v for k, v in self.results["http"].items() 
                        if k != "response_times"  # 不保存原始响应时间数组，可能很大
                    },
                    "ws": {
                        k: v for k, v in self.results["ws"].items()
                        if k not in ["response_times", "task_response_times"]
                    }
                }
            }, f, indent=2)
        
        logger.info(f"测试报告已保存至: {report_file}")
        
        # 生成响应时间分布图
        try:
            plt.figure(figsize=(12, 10))
            sns.set_style("whitegrid")
            
            # 设置子图
            plt.subplot(2, 1, 1)
            if "http" in self.results and "response_times" in self.results["http"]:
                http_times = [t * 1000 for t in self.results["http"]["response_times"]]  # 转换为毫秒
                if http_times:
                    sns.histplot(http_times, kde=True, color="blue")
                    plt.title("HTTP响应时间分布")
                    plt.xlabel("响应时间 (ms)")
                    plt.ylabel("频率")
            
            plt.subplot(2, 1, 2)
            if "ws" in self.results and "response_times" in self.results["ws"]:
                ws_times = [t * 1000 for t in self.results["ws"]["response_times"]]  # 转换为毫秒
                if ws_times:
                    sns.histplot(ws_times, kde=True, color="green")
                    plt.title("WebSocket响应时间分布")
                    plt.xlabel("响应时间 (ms)")
                    plt.ylabel("频率")
            
            plt.tight_layout()
            plt.savefig(plot_file)
            logger.info(f"响应时间分布图已保存至: {plot_file}")
        except Exception as e:
            logger.error(f"生成响应时间分布图失败: {e}")
    
    async def run_test(self, http_rps=10, http_duration=60, ws_connections=5, ws_messages=20, ws_interval=1.0):
        """运行负载测试
        
        Args:
            http_rps: HTTP每秒请求数
            http_duration: HTTP测试持续时间(秒)
            ws_connections: WebSocket并发连接数
            ws_messages: 每个WebSocket连接发送的消息数
            ws_interval: WebSocket消息发送间隔(秒)
        """
        logger.info(f"开始MCP服务负载测试")
        logger.info(f"HTTP URL: {self.http_url}")
        logger.info(f"WebSocket URL: {self.ws_url}")
        
        # 检查服务可用性
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.http_url}/health", timeout=5) as response:
                    if response.status != 200:
                        logger.error(f"HTTP服务不可用，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"连接HTTP服务失败: {e}")
            return False
        
        try:
            websocket = await websockets.connect(self.ws_url, timeout=5)
            await websocket.close()
        except Exception as e:
            logger.error(f"连接WebSocket服务失败: {e}")
            return False
        
        logger.info("服务可用性检查通过")
        
        # 运行HTTP负载测试
        await self.http_load_test(http_rps, http_duration)
        
        # 运行WebSocket负载测试
        await self.ws_load_test(ws_connections, ws_messages, ws_interval)
        
        # 显示结果
        self.display_results()
        
        # 生成报告
        self.generate_report()
        
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务负载测试")
    parser.add_argument("--http-url", default=HTTP_SERVICE_URL, help="HTTP接口URL")
    parser.add_argument("--ws-url", default=WS_SERVICE_URL, help="WebSocket接口URL")
    parser.add_argument("--http-rps", type=int, default=10, help="HTTP每秒请求数")
    parser.add_argument("--http-duration", type=int, default=60, help="HTTP测试持续时间(秒)")
    parser.add_argument("--ws-connections", type=int, default=5, help="WebSocket并发连接数")
    parser.add_argument("--ws-messages", type=int, default=20, help="每个WebSocket连接发送的消息数")
    parser.add_argument("--ws-interval", type=float, default=1.0, help="WebSocket消息发送间隔(秒)")
    args = parser.parse_args()
    
    # 创建测试实例
    test = LoadTest(http_url=args.http_url, ws_url=args.ws_url)
    
    try:
        # 运行测试
        success = asyncio.run(test.run_test(
            http_rps=args.http_rps,
            http_duration=args.http_duration,
            ws_connections=args.ws_connections,
            ws_messages=args.ws_messages,
            ws_interval=args.ws_interval
        ))
        
        # 退出码
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 