# 技术上下文

## 使用的技术栈

### 核心技术
- **Python 3.10+**：主要开发语言
- **LZ4**：高效压缩算法，用于记忆数据压缩
- **BERT/Sentence Transformers**：用于语义嵌入和记忆检索
- **大型语言模型**：
  - Anthropic Claude-3-5-Sonnet
  - OpenAI GPT-4o
  - OpenAI o1-128k
  - DeepSeek-R1

### 工具库
- **Vector Database**：用于记忆索引和检索
- **JSON Schema**：用于结构化消息格式定义
- **MQTT/ZeroMQ**：智能体间通信协议
- **asyncio**：异步操作处理
- **Logging**：日志记录和监控

### 可视化组件
- **Mermaid**：用于流程图和架构图生成
- **Matplotlib/Seaborn**：数据可视化
- **Prometheus/Grafana**：性能监控和指标追踪

## 开发环境
- **操作系统**：跨平台兼容（Windows, Linux, MacOS）
- **IDE**：VS Code 配合 Python 扩展
- **环境管理**：
  - Python虚拟环境（venv）
  - 依赖管理使用pip/uv
- **版本控制**：Git 配合 GitHub Actions
- **测试框架**：pytest 自动化测试

## 技术约束

### 性能约束
- 智能体响应时间不超过2秒
- 记忆检索延迟不超过100ms
- 支持同时处理至少10个并行任务
- 内存占用不超过2GB
- 磁盘存储需求不超过10GB

### 兼容性约束
- 支持Python 3.10及以上版本
- 支持主流云平台部署（AWS, Azure, GCP）
- 支持Docker容器化部署
- API需保持向后兼容性

### 安全约束
- API密钥安全存储
- 记忆数据加密存储
- 通信消息完整性验证
- 权限分级控制

## 依赖关系

### 核心依赖
```
lz4==4.4.4
sentence-transformers==4.1.0
pydantic>=2.3.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
ujson>=5.6.0
cryptography>=39.0.0
```

### 开发依赖
```
pytest>=7.4.0
black>=23.3.0
isort>=5.12.0
mypy>=1.2.0
coverage>=7.0.0
```

### 外部服务依赖
- OpenAI API
- Anthropic API
- DeepSeek API
- MongoDB/Redis（可选，用于分布式部署）
- Slack（用于告警集成）

### 工具依赖关系图
```
memory_manager.py
├── memory_index.py
│   └── sentence_transformers
├── memory_sync.py
│   └── lz4
└── token_tracker.py

llm_api.py
├── openai
├── anthropic
└── deepseek

agent_monitor.py
├── prometheus_client
└── aiohttp
```

*最后更新: 2025-05-08 12:29:51*
