#!/usr/bin/env python3
"""
MCP服务器测试脚本

用于测试MCP服务器的基本功能，包括记忆银行、任务管理等。
"""

import asyncio
import json
import sys
import time
import requests
from pathlib import Path

# 服务器地址
SERVER_URL = "http://127.0.0.1:8000"

def test_health():
    """测试健康检查功能"""
    try:
        resp = requests.get(f"{SERVER_URL}/health")
        if resp.status_code == 200:
            print("✅ 健康检查成功")
            print(f"健康状态: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ 健康检查失败，状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查出错: {e}")
        return False

def test_read_memory():
    """测试读取记忆功能"""
    try:
        # 使用GET请求访问工具页面
        resp = requests.get(f"{SERVER_URL}/tools")
        if resp.status_code == 200:
            print("✅ 获取工具列表成功")
        else:
            print(f"❌ 获取工具列表失败，状态码: {resp.status_code}")
        
        # 发送POST请求
        resp = requests.post(
            f"{SERVER_URL}/tools/read_memory",
            json={"file_path": "activeContext.md"}
        )
        if resp.status_code == 200:
            print("✅ 读取记忆成功")
            try:
                content = json.loads(resp.text)
                print(f"记忆内容: {json.dumps(content, indent=2, ensure_ascii=False)}")
            except:
                print(f"记忆内容: {resp.text[:200]}...")
            return True
        else:
            print(f"❌ 读取记忆失败，状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 读取记忆出错: {e}")
        return False

def test_create_task():
    """测试创建任务功能"""
    try:
        resp = requests.post(
            f"{SERVER_URL}/tools/create_task",
            json={"description": "测试任务 - " + time.strftime("%Y-%m-%d %H:%M:%S")}
        )
        if resp.status_code == 200:
            print("✅ 创建任务成功")
            try:
                content = json.loads(resp.text)
                print(f"任务信息: {json.dumps(content, indent=2, ensure_ascii=False)}")
                return content.get("task_id", "") if isinstance(content, dict) else ""
            except:
                print(f"任务信息: {resp.text}")
                return ""
        else:
            print(f"❌ 创建任务失败，状态码: {resp.status_code}")
            # 尝试备用方法：直接获取URL
            try:
                resp = requests.get(f"{SERVER_URL}/tools")
                print("✅ 获取工具列表成功")
            except Exception as e2:
                print(f"获取工具列表也失败: {e2}")
            return ""
    except Exception as e:
        print(f"❌ 创建任务出错: {e}")
        return ""

def test_list_tasks():
    """测试列出任务功能"""
    try:
        # 尝试一次GET请求，检查服务器是否在线
        try:
            resp_check = requests.get(f"{SERVER_URL}/health", timeout=2)
            print(f"服务器状态检查: {resp_check.status_code}")
        except:
            print("服务器状态检查失败，继续测试")
        
        # 实际测试
        resp = requests.post(f"{SERVER_URL}/tools/list_tasks")
        if resp.status_code == 200:
            print("✅ 列出任务成功")
            try:
                content = json.loads(resp.text)
                print(f"任务列表: {json.dumps(content, indent=2, ensure_ascii=False)}")
            except:
                print(f"任务列表: {resp.text[:200]}...")
            return True
        else:
            print(f"❌ 列出任务失败，状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 列出任务出错: {e}")
        return False

def test_analyze_task():
    """测试分析任务功能"""
    try:
        resp = requests.post(
            f"{SERVER_URL}/tools/analyze_task",
            json={"task_description": "创建一个用户认证系统，包括注册、登录和密码重置功能"}
        )
        if resp.status_code == 200:
            print("✅ 分析任务成功")
            try:
                content = json.loads(resp.text)
                print(f"任务分析: {json.dumps(content, indent=2, ensure_ascii=False)}")
            except:
                print(f"任务分析: {resp.text[:200]}...")
            return True
        else:
            print(f"❌ 分析任务失败，状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 分析任务出错: {e}")
        return False

def test_call_llm():
    """测试调用LLM功能"""
    try:
        try:
            # 先尝试使用GET获取健康状态，确保服务器正常
            check_resp = requests.get(f"{SERVER_URL}/health", timeout=2)
            print(f"服务器健康状态: {check_resp.status_code}")
        except:
            print("服务器健康检查请求失败，继续测试")
        
        resp = requests.post(
            f"{SERVER_URL}/tools/call_llm",
            json={
                "prompt": "简要介绍一下多智能体协作框架的优势",
                "provider": "openai"
            }
        )
        if resp.status_code == 200:
            print("✅ 调用LLM成功")
            print(f"LLM响应: {resp.text[:200]}...")
            return True
        else:
            print(f"❌ 调用LLM失败，状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 调用LLM出错: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("开始测试MCP服务器功能...")
    print("-" * 50)
    
    # 测试健康检查
    print("\n[1/6] 测试健康检查")
    health_ok = test_health()
    
    if not health_ok:
        print("⚠️ 健康检查失败，但会继续测试其他功能")
    
    # 测试读取记忆
    print("\n[2/6] 测试读取记忆")
    memory_ok = test_read_memory()
    
    # 测试创建任务
    print("\n[3/6] 测试创建任务")
    task_id = test_create_task()
    
    # 测试列出任务
    print("\n[4/6] 测试列出任务")
    tasks_ok = test_list_tasks()
    
    # 测试分析任务
    print("\n[5/6] 测试分析任务")
    analyze_ok = test_analyze_task()
    
    # 测试调用LLM
    print("\n[6/6] 测试调用LLM")
    llm_ok = test_call_llm()
    
    # 输出总结
    print("\n测试完成！")
    print("测试结果:")
    print(f"健康检查: {'✅ 通过' if health_ok else '❌ 失败'}")
    print(f"读取记忆: {'✅ 通过' if memory_ok else '❌ 失败'}")
    print(f"创建任务: {'✅ 通过' if task_id else '❌ 失败'}")
    print(f"列出任务: {'✅ 通过' if tasks_ok else '❌ 失败'}")
    print(f"分析任务: {'✅ 通过' if analyze_ok else '❌ 失败'}")
    print(f"调用LLM: {'✅ 通过' if llm_ok else '❌ 失败'}")
    
    # 计算测试通过率
    total_tests = 6
    passed_tests = sum([health_ok, memory_ok, bool(task_id), tasks_ok, analyze_ok, llm_ok])
    pass_rate = passed_tests / total_tests * 100
    print(f"\n通过率: {pass_rate:.1f}% ({passed_tests}/{total_tests})")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    run_all_tests() 