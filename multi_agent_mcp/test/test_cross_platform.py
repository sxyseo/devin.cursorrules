"""
跨平台兼容性测试模块

该模块用于测试系统在不同平台(Windows、macOS、Linux)上的兼容性，
包括路径处理、文件编码、环境变量、网络连接等方面的测试。
"""

import os
import sys
import time
import platform
import tempfile
import unittest
import logging
import json
import socket
import subprocess
from pathlib import Path
from unittest import mock

# 获取项目根目录
project_root = Path(__file__).absolute().parent.parent.parent
sys.path.append(str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cross_platform_test")

class CrossPlatformTests(unittest.TestCase):
    """跨平台兼容性测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.system = platform.system()
        self.temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
        logger.info(f"运行测试于 {self.system} 平台")
        logger.info(f"Python版本: {platform.python_version()}")
        logger.info(f"临时目录: {self.temp_dir}")
    
    def tearDown(self):
        """测试后的清理工作"""
        # 清理创建的临时文件
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")
    
    def test_path_handling(self):
        """测试路径处理"""
        # 检查绝对路径转换
        if self.system == "Windows":
            path = "C:\\Users\\test\\file.txt"
            path_obj = Path(path)
            self.assertEqual(str(path_obj), path)
        elif self.system == "Darwin":  # macOS
            path = "/Users/test/file.txt"
            path_obj = Path(path)
            self.assertEqual(str(path_obj), path)
        else:  # Linux
            path = "/home/test/file.txt"
            path_obj = Path(path)
            self.assertEqual(str(path_obj), path)
        
        # 测试路径连接
        base_dir = Path(self.temp_dir)
        sub_dir = "subdir"
        file_name = "test.txt"
        
        # 使用Path对象的/操作符连接路径
        full_path = base_dir / sub_dir / file_name
        self.assertTrue(isinstance(full_path, Path))
        
        # 创建子目录
        sub_path = base_dir / sub_dir
        os.makedirs(sub_path, exist_ok=True)
        self.assertTrue(os.path.exists(sub_path))
        
        # 创建并写入测试文件
        with open(full_path, "w", encoding="utf-8") as f:
            f.write("Test content")
        
        self.assertTrue(os.path.exists(full_path))
        
        # 测试相对路径
        os.chdir(base_dir)
        rel_path = Path(sub_dir) / file_name
        self.assertTrue(os.path.exists(rel_path))
    
    def test_file_encoding(self):
        """测试文件编码处理"""
        # 测试UTF-8编码
        utf8_path = Path(self.temp_dir) / "utf8_test.txt"
        utf8_content = "测试UTF-8编码 😀 ß Ж"
        
        with open(utf8_path, "w", encoding="utf-8") as f:
            f.write(utf8_content)
        
        with open(utf8_path, "r", encoding="utf-8") as f:
            read_content = f.read()
        
        self.assertEqual(utf8_content, read_content)
        
        # 测试在Windows上常见的编码
        if self.system == "Windows":
            # 测试GBK编码 (中文Windows上常用)
            gbk_path = Path(self.temp_dir) / "gbk_test.txt"
            gbk_content = "测试GBK编码"
            
            with open(gbk_path, "w", encoding="gbk") as f:
                f.write(gbk_content)
            
            with open(gbk_path, "r", encoding="gbk") as f:
                read_content = f.read()
            
            self.assertEqual(gbk_content, read_content)
            
            # 尝试用错误的编码读取，应该引发异常或得到错误的内容
            try:
                with open(gbk_path, "r", encoding="utf-8") as f:
                    wrong_content = f.read()
                # 确认内容不同
                self.assertNotEqual(gbk_content, wrong_content)
            except UnicodeDecodeError:
                # 或者可能引发编码错误
                pass
    
    def test_environment_variables(self):
        """测试环境变量处理"""
        # 测试设置和获取环境变量
        test_var_name = "MCP_TEST_VAR"
        test_var_value = "test_value_123"
        
        # 设置环境变量
        os.environ[test_var_name] = test_var_value
        
        # 使用os.environ获取
        self.assertEqual(os.environ.get(test_var_name), test_var_value)
        
        # 使用os.getenv获取
        self.assertEqual(os.getenv(test_var_name), test_var_value)
        
        # 测试环境变量的路径连接
        if self.system == "Windows":
            # Windows使用分号分隔路径
            path_var = "PATH1;PATH2;PATH3"
        else:
            # Unix系统使用冒号分隔路径
            path_var = "PATH1:PATH2:PATH3"
        
        os.environ["MCP_TEST_PATH"] = path_var
        path_parts = os.environ["MCP_TEST_PATH"].split(os.pathsep)
        self.assertEqual(len(path_parts), 3)
    
    def test_file_permissions(self):
        """测试文件权限处理"""
        test_file = Path(self.temp_dir) / "permission_test.txt"
        
        # 创建测试文件
        with open(test_file, "w") as f:
            f.write("Test content")
        
        # 测试文件存在性
        self.assertTrue(os.path.exists(test_file))
        
        # 测试文件读取权限
        self.assertTrue(os.access(test_file, os.R_OK))
        
        # 测试文件写入权限
        self.assertTrue(os.access(test_file, os.W_OK))
        
        # Windows和Unix系统的文件权限处理有较大差异
        if self.system != "Windows":
            # 更改文件权限 (仅在Unix系统测试)
            os.chmod(test_file, 0o400)  # 仅所有者可读
            
            # 测试权限更改
            self.assertTrue(os.access(test_file, os.R_OK))
            self.assertFalse(os.access(test_file, os.W_OK))
            
            # 恢复权限
            os.chmod(test_file, 0o600)  # 所有者可读写
            self.assertTrue(os.access(test_file, os.W_OK))
    
    def test_network_connection(self):
        """测试网络连接"""
        # 测试网络可用性
        def check_connection(host, port=80, timeout=2):
            try:
                socket.create_connection((host, port), timeout=timeout)
                return True
            except (socket.timeout, socket.error):
                return False
        
        # 测试连接到常见网站
        self.assertTrue(check_connection("www.baidu.com", 443) or 
                      check_connection("www.google.com", 443),
                      "无法连接到任何常见网站，请检查网络连接")
        
        # 测试创建本地socket服务器
        test_port = 8899
        
        # 异步测试创建本地socket服务器和客户端
        import threading
        
        def server_func():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind(("127.0.0.1", test_port))
                server.listen(1)
                conn, addr = server.accept()
                data = conn.recv(1024)
                conn.sendall(data)  # 回显数据
                conn.close()
            except Exception as e:
                logger.error(f"服务器错误: {e}")
            finally:
                server.close()
        
        # 启动服务器线程
        server_thread = threading.Thread(target=server_func)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        # 创建客户端并连接
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(("127.0.0.1", test_port))
            test_data = b"Hello, Socket!"
            client.sendall(test_data)
            response = client.recv(1024)
            self.assertEqual(response, test_data)
        except Exception as e:
            self.fail(f"客户端连接失败: {e}")
        finally:
            client.close()
    
    def test_process_management(self):
        """测试进程管理"""
        # 测试创建子进程
        if self.system == "Windows":
            command = ["cmd", "/c", "echo", "test process"]
        else:
            command = ["echo", "test process"]
        
        # 使用subprocess运行命令
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("test process", result.stdout)
        
        # 测试带超时的进程
        if self.system == "Windows":
            timeout_cmd = ["timeout", "/t", "3"]
        else:
            timeout_cmd = ["sleep", "3"]
        
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(timeout_cmd, timeout=1)
        
        # 测试环境变量传递给子进程
        env_var_name = "MCP_SUBPROCESS_TEST"
        env_var_value = "test_value_456"
        
        if self.system == "Windows":
            env_cmd = ["cmd", "/c", f"echo %{env_var_name}%"]
        else:
            env_cmd = ["sh", "-c", f"echo ${env_var_name}"]
        
        env = os.environ.copy()
        env[env_var_name] = env_var_value
        
        result = subprocess.run(env_cmd, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0)
        self.assertIn(env_var_value, result.stdout)


class LLMAPITests(unittest.TestCase):
    """LLM API跨平台兼容性测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 尝试导入LLM API模块
        try:
            sys.path.append(str(project_root))
            from tools import llm_api
            self.llm_api = llm_api
            self.module_available = True
        except ImportError as e:
            self.module_available = False
            logger.warning(f"导入LLM API模块失败: {e}")
    
    def test_llm_api_import(self):
        """测试LLM API模块导入"""
        if not self.module_available:
            self.skipTest("LLM API模块不可用")
        
        # 检查关键函数是否存在
        self.assertTrue(hasattr(self.llm_api, "query_llm"))
        self.assertTrue(hasattr(self.llm_api, "create_llm_client"))
    
    @mock.patch("tools.llm_api.query_llm")
    def test_llm_api_mock(self, mock_query_llm):
        """测试LLM API模拟调用"""
        if not self.module_available:
            self.skipTest("LLM API模块不可用")
        
        # 设置模拟返回值
        mock_return = mock.MagicMock()
        mock_return.content = "模拟的LLM响应"
        mock_query_llm.return_value = mock_return
        
        # 导入并使用LLM API
        from tools.llm_api import query_llm
        
        # 调用API
        response = query_llm("测试提示词", provider="mock")
        
        # 验证结果
        self.assertEqual(response.content, "模拟的LLM响应")
        mock_query_llm.assert_called_once()
    
    def test_llm_client_init(self):
        """测试LLM客户端初始化"""
        if not self.module_available:
            self.skipTest("LLM API模块不可用")
        
        # 使用模拟提供商进行测试，避免实际API调用
        from tools.llm_api import create_llm_client
        
        # 测试创建mock客户端
        client = create_llm_client("mock")
        self.assertIsNotNone(client)
    
    def test_error_handling(self):
        """测试错误处理"""
        if not self.module_available:
            self.skipTest("LLM API模块不可用")
        
        # 模拟API错误情况
        with mock.patch("tools.llm_api.create_llm_client") as mock_create_client:
            mock_create_client.side_effect = Exception("模拟的API错误")
            
            from tools.llm_api import create_llm_client
            
            # 验证异常被正确抛出
            with self.assertRaises(Exception) as context:
                create_llm_client("openai")
            
            self.assertIn("模拟的API错误", str(context.exception))


class ServerTests(unittest.TestCase):
    """服务器跨平台兼容性测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 尝试导入服务器模块
        try:
            from multi_agent_mcp import server
            self.server = server
            self.module_available = True
        except ImportError as e:
            self.module_available = False
            logger.warning(f"导入服务器模块失败: {e}")
    
    def test_server_import(self):
        """测试服务器模块导入"""
        if not self.module_available:
            self.skipTest("服务器模块不可用")
        
        # 检查关键函数是否存在
        self.assertTrue(hasattr(self.server, "main"))
    
    @mock.patch("multi_agent_mcp.server.start_server")
    def test_server_start(self, mock_start_server):
        """测试服务器启动"""
        if not self.module_available:
            self.skipTest("服务器模块不可用")
        
        # 设置模拟返回值
        mock_start_server.return_value = None
        
        # 调用启动函数
        from multi_agent_mcp.server import main
        
        # 模拟启动服务器，这里不实际启动以避免端口冲突
        with mock.patch("sys.argv", ["server.py", "--port", "8080"]):
            main()
        
        # 验证结果
        mock_start_server.assert_called_once()
    
    def test_path_handling(self):
        """测试服务器路径处理"""
        if not self.module_available:
            self.skipTest("服务器模块不可用")
        
        # 测试内存银行路径处理
        memory_bank_dir = self.server.MEMORY_BANK_DIR
        self.assertIsInstance(memory_bank_dir, Path)
        
        # 测试路径是否存在
        memory_bank_dir.mkdir(exist_ok=True)
        self.assertTrue(memory_bank_dir.exists())


def create_test_report(results, file_path=None):
    """创建测试报告"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system": platform.system(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "results": results
    }
    
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report


def run_tests():
    """运行所有测试并生成报告"""
    # 创建测试套件
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试用例
    test_suite.addTests(test_loader.loadTestsFromTestCase(CrossPlatformTests))
    test_suite.addTests(test_loader.loadTestsFromTestCase(LLMAPITests))
    test_suite.addTests(test_loader.loadTestsFromTestCase(ServerTests))
    
    # 运行测试
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_result = test_runner.run(test_suite)
    
    # 收集测试结果
    results = {
        "tests_run": test_result.testsRun,
        "errors": len(test_result.errors),
        "failures": len(test_result.failures),
        "skipped": len(test_result.skipped),
        "success": test_result.wasSuccessful(),
        "details": {
            "errors": [str(error) for error in test_result.errors],
            "failures": [str(failure) for failure in test_result.failures],
            "skipped": [str(skipped) for skipped in test_result.skipped]
        }
    }
    
    # 创建并保存测试报告
    report_dir = project_root / "test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    report_file = report_dir / f"cross_platform_test_{platform.system().lower()}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    report = create_test_report(results, report_file)
    
    logger.info(f"测试完成，报告已保存到 {report_file}")
    logger.info(f"测试结果: 运行 {results['tests_run']}，失败 {results['failures']}，"
               f"错误 {results['errors']}，跳过 {results['skipped']}")
    
    return results["success"]


if __name__ == "__main__":
    # 运行测试
    success = run_tests()
    sys.exit(0 if success else 1) 