# 多智能体MCP服务器

多智能体MCP（Multi-Agent Message Control Protocol）服务器是一个提供增强型多智能体协作框架的服务，可以通过Cursor等开发工具访问。该框架基于Planner-Executor模式，实现高效任务规划和执行。

## 功能特点

- **记忆银行工具**：读取、更新、列出、搜索和同步记忆文件
- **任务管理工具**：创建任务、获取任务状态、列出所有任务、分析任务
- **LLM调用工具**：支持多种提供商（OpenAI、Anthropic、DeepSeek、SiliconFlow等）
- **系统工具**：检查系统健康状态、运行诊断、执行跨平台测试
- **强大的错误处理**：分类、诊断和自动恢复机制
- **模拟模式**：即使在缺少依赖的情况下也能提供基本功能
- **跨平台兼容**：支持Windows、macOS和Linux

## 快速开始

### 安装

1. 克隆仓库：
```bash
git clone https://github.com/your-username/multi-agent-mcp.git
cd multi-agent-mcp
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

### 配置

创建`.env`文件，设置必要的环境变量：

```
# 基本配置
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO

# LLM提供商API密钥（可选）
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
SILICONFLOW_API_KEY=your_siliconflow_api_key
GOOGLE_API_KEY=your_google_api_key

# 记忆银行设置
MEMORY_BANK_DIR=./memory-bank

# 启用模拟模式（当API密钥不可用时）
ENABLE_SIMULATION_MODE=true
```

### 运行服务器

```bash
# 使用默认配置启动服务器
python -m multi_agent_mcp server

# 指定主机和端口
python -m multi_agent_mcp server --host 0.0.0.0 --port 8080

# 启用模拟模式
python -m multi_agent_mcp server --simulation

# 使用简单HTTP服务器（不依赖FastAPI）
python -m multi_agent_mcp server --protocol simple
```

### 运行测试和诊断

```bash
# 运行跨平台测试
python -m multi_agent_mcp test cross-platform

# 测试LLM API
python -m multi_agent_mcp test llm-api --provider openai

# 运行系统诊断
python -m multi_agent_mcp diagnose
```

## 与Cursor集成

### 配置Cursor

编辑Cursor配置文件，添加MCP服务器配置：

#### Windows
`%APPDATA%\Cursor\cursor_desktop_config.json`

#### macOS
`~/Library/Application Support/Cursor/cursor_desktop_config.json`

#### Linux
`~/.config/Cursor/cursor_desktop_config.json`

### 配置示例

```json
{
  "mcpServers": {
    "multi_agent_mcp": {
      "command": "python",
      "args": ["-m", "multi_agent_mcp", "server", "--simulation"],
      "cwd": "D:/path/to/multi-agent-mcp",
      "env": {
        "MEMORY_BANK_DIR": "D:/path/to/multi-agent-mcp/memory-bank",
        "ENABLE_SIMULATION_MODE": "true"
      }
    }
  }
}
```

## 工具组件

### 错误处理系统

多智能体MCP服务器包含全面的错误处理系统，可以对错误进行分类、诊断并执行自动恢复：

```python
from multi_agent_mcp.tools.error_handler import error_handler, ErrorCategory, ErrorSeverity

# 使用错误处理装饰器
@error_handler.with_error_handling(category=ErrorCategory.API, severity=ErrorSeverity.MEDIUM)
def call_external_api():
    # 函数实现
    pass

# 手动处理错误
try:
    # 代码实现
except Exception as e:
    error_info = error_handler.handle_error(
        e, 
        category=ErrorCategory.NETWORK, 
        severity=ErrorSeverity.HIGH, 
        context={"function": "connect_to_server"}
    )
```

### 系统诊断工具

系统诊断工具可以检查Python环境、系统资源、网络连接和文件系统：

```python
from multi_agent_mcp.tools.system_diagnostics import system_diagnostics

# 运行完整诊断
results = system_diagnostics.run_full_diagnostics()

# 检查Python环境
env_info = system_diagnostics.check_python_environment()

# 检查网络连接
connectivity = system_diagnostics.check_network_connectivity()
```

### 跨平台测试工具

跨平台测试工具可以验证系统在不同平台上的兼容性：

```python
from multi_agent_mcp.tools.cross_platform_test import CrossPlatformTest

# 创建测试实例
tester = CrossPlatformTest()

# 运行所有测试
results = tester.run_all_tests()

# 测试路径处理
path_results = tester.test_path_handling()
```

### LLM API测试工具

LLM API测试工具可以测试不同LLM提供商的API调用：

```python
from multi_agent_mcp.tools.llm_api_test import LLMAPITest

# 创建测试实例
tester = LLMAPITest()

# 测试特定提供商
result = tester.test_provider("openai", "gpt-4o")

# 测试所有提供商
results = tester.test_all_providers(include_models=True)
```

## API参考

### HTTP API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/tools/{tool_name}` | POST | 调用指定的工具 |
| `/health` | GET | 检查服务器健康状态 |
| `/` | GET | 获取服务器信息 |
| `/tools` | GET | 列出可用的工具 |

### 工具列表

| 工具名称 | 描述 |
|---------|------|
| `read_memory` | 读取记忆文件内容 |
| `list_memory_files` | 列出所有记忆文件 |
| `search_memory` | 搜索记忆内容 |
| `update_memory` | 更新记忆文件内容 |
| `create_task` | 创建新任务 |
| `get_task_status` | 获取任务状态 |
| `list_tasks` | 列出所有任务 |
| `analyze_task` | 分析任务并创建子任务 |
| `call_llm` | 调用LLM模型 |
| `check_health` | 检查系统健康状态 |

## 架构

多智能体MCP服务器基于以下架构：

```
                 +----------------+
                 |  MCP服务器     |
                 +-------+--------+
                         |
         +---------------+---------------+
         |               |               |
+--------v-------+ +-----v------+ +-----v------+
|  记忆管理系统  | | 智能体系统 | |  工具系统  |
+----------------+ +------------+ +------------+
         |               |               |
         |      +-------v--------+      |
         |      |  Planner-      |      |
         +----->|  Executor模式  |<-----+
                +----------------+
```

### 组件

- **MCP服务器**：提供HTTP和WebSocket接口，处理客户端请求
- **记忆管理系统**：管理记忆银行，提供持久化存储和检索
- **智能体系统**：实现Planner和Executor角色，处理任务规划和执行
- **工具系统**：提供各种工具，如LLM调用、系统诊断等

## 贡献

欢迎贡献代码、报告问题或提出建议。请遵循以下步骤：

1. Fork仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详情请参阅[LICENSE](LICENSE)文件。

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/)：提供高性能HTTP API
- [OpenAI](https://openai.com/)：提供强大的LLM模型
- [Anthropic](https://www.anthropic.com/)：提供Claude系列模型
- [Cursor](https://cursor.dev/)：提供智能代码编辑器和MCP集成 