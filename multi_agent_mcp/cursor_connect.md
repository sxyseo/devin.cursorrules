# Cursor MCP连接指南

本指南将帮助你将多智能体协作框架MCP服务器与Cursor集成，让你的AI助手拥有记忆银行和智能任务管理能力。

## 准备工作

1. 确保已安装Python 3.10或更高版本
2. 安装MCP SDK：`pip install mcp[cli]`
3. 将多智能体协作框架MCP服务器从Github克隆或下载到本地

## 配置Cursor

1. 打开Cursor应用程序
2. 找到Cursor的MCP配置文件:

### Windows用户
配置文件位置: `%APPDATA%\Cursor\cursor_desktop_config.json`

可以使用以下PowerShell命令打开:
```powershell
notepad $env:APPDATA\Cursor\cursor_desktop_config.json
```

### macOS用户
配置文件位置: `~/Library/Application Support/Cursor/cursor_desktop_config.json`

可以使用以下命令打开:
```bash
open -a TextEdit ~/Library/Application\ Support/Cursor/cursor_desktop_config.json
```

### Linux用户
配置文件位置: `~/.config/Cursor/cursor_desktop_config.json`

可以使用以下命令打开:
```bash
nano ~/.config/Cursor/cursor_desktop_config.json
```

## 添加MCP服务器配置

在配置文件中添加以下内容（如果文件不存在，先创建一个空的JSON文件）:

```json
{
  "mcpServers": {
    "multi_agent_mcp": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "D:/path/to/multi_agent_mcp",
      "env": {}
    }
  }
}
```

注意:
- 将 `D:/path/to/multi_agent_mcp` 替换为你的实际路径
- macOS/Linux用户请使用正斜杠格式路径: `/path/to/multi_agent_mcp`

## 配置环境变量（可选）

如果你需要使用LLM功能，可以添加API密钥：

```json
{
  "mcpServers": {
    "multi_agent_mcp": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "D:/path/to/multi_agent_mcp",
      "env": {
        "OPENAI_API_KEY": "your_openai_key",
        "ANTHROPIC_API_KEY": "your_anthropic_key"
      }
    }
  }
}
```

## 启动Cursor

1. 保存配置文件
2. 启动或重启Cursor
3. MCP服务器会在你启动会话时自动启动

## 在Cursor中使用MCP功能

你可以通过自然语言与Claude交互来使用MCP功能：

### 记忆银行功能
- "请读取记忆银行中的activeContext.md文件"
- "帮我更新记忆银行中的progress.md文件，添加今天的进度"
- "列出记忆银行中的所有文件"
- "在记忆银行中搜索关于'多智能体协作'的内容"

### 任务管理功能
- "创建一个新任务：优化网站前端性能"
- "查看任务列表"
- "检查任务T-1234的状态"
- "分析任务：构建一个机器学习推荐系统"

### LLM功能
- "使用deepseek模型回答这个问题：如何优化docker容器性能？"

## 故障排除

如果遇到问题：

1. 检查Cursor日志：
   - Windows: `%APPDATA%\Cursor\logs`
   - macOS: `~/Library/Logs/Cursor`
   - Linux: `~/.config/Cursor/logs`

2. 常见问题解决：
   - 确保路径正确并使用适合你操作系统的路径分隔符
   - 确保Python可用且版本正确
   - 检查API密钥是否正确配置
   - 尝试在命令行手动运行服务器，查看错误消息 