# 增强型多智能体协作框架 MCP 服务器

这是一个为 Cursor 设计的增强型多智能体协作框架 MCP 服务器。它实现了记忆银行、智能任务规划和执行等功能，使 Cursor 中的 Claude 具备持久记忆和多智能体协作能力。

## 功能特点

- **记忆银行工具**：读取、更新、列出、搜索和同步记忆文件
- **任务管理工具**：创建任务、获取任务状态、列出所有任务、分析任务
- **LLM 调用工具**：支持 OpenAI、Anthropic、DeepSeek、SiliconFlow 等多种提供商
- **系统工具**：检查系统健康状态
- **多种协议支持**：HTTP、WebSocket、SSE 和 stdio
- **高可用性**：内置模拟模式，即使缺少依赖也能正常工作

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/multi_agent_mcp.git
cd multi_agent_mcp

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 启动服务器

```bash
# 正常模式
python -m multi_agent_mcp --host 127.0.0.1 --port 8000

# 模拟模式 (无需依赖)
python -m multi_agent_mcp --host 127.0.0.1 --port 8000 --simulation
```

### 配置 Cursor

在 Cursor 的配置文件中添加以下内容：

**Windows**: `%APPDATA%\Cursor\cursor_desktop_config.json`  
**macOS**: `~/Library/Application Support/Cursor/cursor_desktop_config.json`  
**Linux**: `~/.config/Cursor/cursor_desktop_config.json`

```json
{
  "agentic_mcp_url": null,
  "agentic_mcp_command": [
    "D:/path/to/venv/python.exe",
    "-m",
    "multi_agent_mcp",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--simulation"
  ],
  "agentic_mcp_cwd": "D:/path/to/multi_agent_mcp",
  "agentic_mcp_env": {
    "PYTHONPATH": "D:/path/to/multi_agent_mcp"
  },
  "agentic_mcp_restart_frequency": 604800
}
```

将路径替换为你实际的安装路径。

### 使用功能

一旦服务器运行并配置在 Cursor 中，你可以通过自然语言使用以下功能：

#### 记忆银行

- 读取记忆文件：`请读取记忆银行中的activeContext.md文件`
- 更新记忆文件：`更新记忆银行中的progress.md文件为以下内容：...`
- 列出记忆文件：`列出记忆银行中的所有文件`
- 搜索记忆内容：`在记忆银行中搜索"多智能体协作"`

#### 任务管理

- 创建任务：`创建一个新任务：优化网站前端性能`
- 获取任务状态：`查看任务123的状态`
- 列出所有任务：`列出所有任务`
- 分析任务：`分析这个任务：实现用户认证系统`

#### LLM 功能

- 调用 LLM：`使用deepseek模型回答这个问题：...`
- 流式调用 LLM：`使用流式模式和anthropic模型回答：...`

#### 系统功能

- 检查健康状态：`检查系统健康状态`

## API 文档

服务器启动后，可以通过访问 `http://127.0.0.1:8000/docs` 查看完整的 API 文档。

## 贡献

欢迎提交 Pull Request 或 Issue。

## 许可证

MIT
