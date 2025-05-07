# 工具集模块

本目录包含多智能体协作框架的核心工具集，提供LLM API调用、web浏览、搜索引擎、工具选择和环境监控等功能。

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