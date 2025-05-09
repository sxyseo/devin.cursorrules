# 多智能体协作框架工具集

此目录包含多智能体协作框架的核心工具和组件。

## 核心组件

- `planner.py` - Planner智能体实现，负责高级任务分析、规划和资源调度
- `executor.py` - Executor智能体实现，负责执行Planner分配的任务
- `communication_manager.py` - 智能体通信管理器，实现可靠的消息传递
- `memory_manager.py` - 记忆管理模块，管理记忆银行文件
- `memory_index.py` - 记忆索引模块，提供向量化记忆存储和检索
- `memory_sync.py` - 记忆同步模块，实现记忆的持久化和版本控制
- `plan_exec_llm.py` - LLM规划执行接口，用于任务分析和计划生成
- `llm_api.py` - LLM API接口，支持多种LLM提供商
- `token_tracker.py` - Token使用跟踪器，记录LLM API调用的token使用情况
- `error_handler.py` - 错误处理模块，实现错误分类、诊断和自动恢复

## 新增组件

- `mcp_service.py` - 多通道协议(MCP)服务，为Cursor提供多智能体调用接口
- `cursor_connect.py` - Cursor连接客户端，连接到MCP服务并提供Cursor功能

## 工具组件

- `web_scraper.py` - 网页抓取工具，提供网页内容提取功能
- `search_engine.py` - 搜索引擎接口，提供网络搜索功能
- `screenshot_utils.py` - 截图工具，提供网页截图功能

## 测试工具

- `test_agents.py` - 智能体测试工具，用于测试Planner和Executor的功能
- `test_cross_platform.py` - 跨平台测试工具，验证系统在不同平台的兼容性

## 使用方法

### 启动MCP服务

MCP服务提供WebSocket接口，允许多个智能体进行通信和协作：

```bash
python tools/mcp_service.py --host localhost --port 8765
```

参数说明：
- `--host`: 服务主机地址，默认为localhost
- `--port`: 服务端口，默认为8765

### 使用Cursor连接客户端

Cursor连接客户端提供与MCP服务的通信功能，支持交互式和程序化使用：

```bash
# 交互式模式
python tools/cursor_connect.py --interactive

# 作为客户端库使用
python tools/cursor_connect.py
```

参数说明：
- `--host`: MCP服务主机地址，默认为localhost
- `--port`: MCP服务端口，默认为8765
- `--interactive`: 启动交互式应用

### 使用Planner和Executor

直接启动Planner和Executor智能体：

```bash
# 启动Planner
python tools/planner.py

# 启动Executor
python tools/executor.py
```

## 内部架构

### 智能体通信

智能体通过`CommunicationManager`进行通信，支持不同的QoS级别和消息优先级。通信架构确保消息的可靠传递和完整性验证。

### 记忆管理

记忆管理系统包括三个核心模块：
- `memory_manager.py`: 管理记忆银行文件的读写
- `memory_index.py`: 提供记忆的向量化索引和语义搜索
- `memory_sync.py`: 实现记忆的同步、版本化和持久化

### 任务规划与执行

任务规划和执行由Planner和Executor协作完成：
- Planner使用三层决策引擎（战略、战术、操作）进行任务分解和资源分配
- Executor使用专用执行器处理不同类型的任务，如代码、测试和文档

### MCP服务架构

MCP服务使用WebSocket提供实时通信，支持：
- 智能体注册和发现
- 任务创建和状态查询
- 智能体间消息传递
- 事件通知和广播

## API文档

详细的API文档请参阅`memory-bank/extensions/api_docs.md`。

## 模块说明

### 1. LLM API (`llm_api.py`)

提供与各种LLM服务商进行交互的统一接口。

```bash
# 命令行使用示例
.venv/bin/python tools/llm_api.py --prompt "你的提示文本" --provider "anthropic"
```

支持的提供商：
- OpenAI (gpt-4o, gpt-4-turbo, o1等)
- Anthropic (claude-3.5-sonnet等)
- Gemini
- Azure OpenAI
- DeepSeek
- 本地模型

### 2. Web爬虫 (`web_scraper.py`)

用于抓取网页内容，支持批量URL处理。

```bash
# 命令行使用示例
.venv/bin/python tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
```

### 3. 搜索引擎 (`search_engine.py`)

封装搜索引擎API，提供搜索功能。

```bash
# 命令行使用示例
.venv/bin/python tools/search_engine.py "搜索关键词"
```

### 4. 截图工具 (`screenshot_utils.py`)

用于获取网页截图，支持视觉分析。

```bash
# 命令行使用示例
.venv/bin/python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
```

### 5. 工具选择器 (`tool_selector.py`) - 新增！

根据任务复杂度和优先级智能选择合适的LLM模型，并提供环境监控能力。

```bash
# 检查环境
.venv/bin/python tools/tool_selector.py check-env [--json]

# 选择最佳模型
.venv/bin/python tools/tool_selector.py select-model \
  --complexity medium \
  --priority high \
  [--min-performance 0.8] \
  [--budget 1.0] \
  [--json]
```

#### 5.1 LLM选择器 (LLMSelector类)

提供基于任务复杂度和优先级的智能模型选择能力：

- **低复杂度任务**：选择性价比较高的Claude 3.5 Sonnet
- **中等复杂度任务**：平衡性能和成本，选择GPT-4o
- **高复杂度任务**：优先考虑性能，选择OpenAI o1

此外，还提供成本控制、响应时间跟踪和使用统计等功能，帮助用户优化LLM使用成本。

#### 5.2 环境监控器 (EnvironmentMonitor类)

提供全面的环境诊断和监控能力：

- Python环境检查（版本兼容性）
- 磁盘空间监控
- 内存使用分析
- CPU使用率监控
- 依赖包完整性验证

## 测试信息

所有工具模块均有对应的单元测试：

```bash
# 运行单个模块测试
.venv/bin/python -m pytest tests/test_llm_api.py -v

# 运行所有测试
bash run_tests.sh
```

### 工具集成测试报告

最新的工具集成测试已全部通过，详见 `tools_test_summary.md`。测试覆盖了LLM工具选择和环境感知的核心功能，验证了系统的可靠性和准确性。

## 配置和环境变量

工具模块使用以下环境变量：

```
# LLM API密钥
OPENAI_API_KEY=你的OpenAI密钥
ANTHROPIC_API_KEY=你的Anthropic密钥
GOOGLE_API_KEY=你的Google API密钥
AZURE_OPENAI_API_KEY=你的Azure OpenAI密钥
AZURE_OPENAI_MODEL_DEPLOYMENT=部署名称

# 搜索引擎API
SEARCH_API_KEY=你的搜索API密钥

# 测试环境标志
TEST_ENV=development
```

环境变量可以存放在项目根目录的`.env`或`.env.local`文件中。 