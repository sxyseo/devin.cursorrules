# 多智能体框架API文档

本文档详细说明了多智能体协作框架中核心工具模块的API和使用方法。

## 记忆管理模块 (`memory_manager.py`)

### 概述
记忆管理模块提供了对记忆银行的基本操作，包括文件读取、创建、更新、备份和恢复等。

### 类和方法

#### `ensure_memory_bank_dir()`
确保记忆银行目录存在，如果不存在则创建。

#### `read_memory(file_name: Optional[str] = None) -> Union[str, Dict[str, str]]`
读取记忆银行中的文件内容。

参数:
- `file_name`: 要读取的文件名，如果为None，则读取所有核心文件

返回:
- 如果指定了文件名，返回文件内容；否则返回文件名到内容的字典

#### `create_memory_file(file_name: str, template: Optional[str] = None, overwrite: bool = False) -> bool`
创建记忆银行文件。

参数:
- `file_name`: 要创建的文件名
- `template`: 文件模板，如果为None则使用默认模板
- `overwrite`: 是否覆盖现有文件

返回:
- 创建是否成功

#### `update_memory_file(file_name: str, content: Optional[str] = None, append: bool = False) -> bool`
更新记忆银行文件。

参数:
- `file_name`: 要更新的文件名
- `content`: 新的文件内容，如果为None则从标准输入读取
- `append`: 是否追加到现有内容

返回:
- 更新是否成功

#### `backup_memory_bank(backup_name: Optional[str] = None) -> bool`
备份记忆银行。

参数:
- `backup_name`: 备份名称，如果为None则使用当前时间

返回:
- 备份是否成功

#### `restore_memory_bank(backup_name: str) -> bool`
恢复记忆银行。

参数:
- `backup_name`: 备份名称

返回:
- 恢复是否成功

#### `initialize_memory_bank(project_name: str, description: str) -> bool`
初始化记忆银行。

参数:
- `project_name`: 项目名称
- `description`: 项目描述

返回:
- 初始化是否成功

#### `list_memory_files() -> List[str]`
列出记忆银行中的所有文件。

返回:
- 文件路径列表

### 命令行接口

```bash
# 初始化记忆银行
python tools/memory_manager.py init --project-name "项目名称" --description "项目描述"

# 读取文件
python tools/memory_manager.py read [file_name]

# 创建文件
python tools/memory_manager.py create <file_name> [--template <template_path>] [--overwrite]

# 更新文件
python tools/memory_manager.py update <file_name> [--content <new_content>] [--append]

# 验证记忆银行
python tools/memory_manager.py validate

# 列出文件
python tools/memory_manager.py list

# 备份记忆银行
python tools/memory_manager.py backup [--name <backup_name>]

# 恢复记忆银行
python tools/memory_manager.py restore <backup_name>
```

## 记忆索引模块 (`memory_index.py`)

### 概述
记忆索引模块提供了基于向量嵌入的语义索引和搜索功能，支持对记忆银行内容进行高效检索。

### 类和方法

#### `class MemoryChunk`
表示记忆银行中的一个内容块。

属性:
- `content`: 内容块的文本
- `file_path`: 内容块所在的文件路径
- `start_pos`: 内容块在文件中的起始位置
- `end_pos`: 内容块在文件中的结束位置
- `embedding`: 内容块的嵌入向量
- `section`: 内容块所属的章节标题
- `last_updated`: 内容块的最后更新时间

#### `class MemoryIndex`
记忆银行索引的主要实现。

方法:
- `load_model() -> None`: 加载嵌入模型
- `extract_sections(content: str) -> List[Tuple[str, str, int, int]]`: 从Markdown内容中提取章节
- `chunk_content(content: str, file_path: str) -> List[MemoryChunk]`: 将内容分成块
- `generate_embeddings() -> None`: 为所有块生成嵌入向量
- `index_memory_bank(force: bool = False) -> None`: 索引记忆银行中的所有文件
- `search(query: str, top_k: int = 5, threshold: float = 0.5) -> List[Tuple[MemoryChunk, float]]`: 语义搜索记忆库
- `exact_search(query: str, case_sensitive: bool = False) -> List[MemoryChunk]`: 精确搜索记忆库

### 命令行接口

```bash
# 创建索引
python tools/memory_index.py index [--force] [--model <model_name>]

# 搜索记忆
python tools/memory_index.py search <query> [--top-k <num_results>] [--threshold <similarity_threshold>] [--exact] [--case-sensitive] [--hide-scores]
```

## 记忆同步模块 (`memory_sync.py`)

### 概述
记忆同步模块提供了记忆银行的增量同步和版本管理功能，支持自动同步和版本快照。

### 类和方法

#### `class SyncState`
记忆银行同步状态的实现。

属性:
- `file_hashes`: 文件哈希值字典
- `last_sync`: 上次同步时间
- `last_version`: 上次版本
- `sync_count`: 同步计数

方法:
- `load() -> bool`: 从文件加载同步状态
- `save() -> bool`: 保存同步状态到文件

#### `class MemorySyncer`
记忆银行同步器的主要实现。

方法:
- `_get_changed_files() -> Dict[str, str]`: 获取已更改的文件及其哈希值
- `_compress_file(source_path: Path, target_path: Path) -> bool`: 使用LZ4压缩文件
- `_decompress_file(source_path: Path, target_path: Path) -> bool`: 使用LZ4解压缩文件
- `_create_version(timestamp: str = None) -> str`: 创建记忆库的版本快照
- `_restore_version(version: str) -> bool`: 从版本快照恢复记忆库
- `_check_consistency() -> Dict[str, str]`: 检查数据一致性
- `sync(force: bool = False) -> bool`: 执行同步操作
- `start_auto_sync() -> None`: 启动自动同步线程
- `stop_auto_sync() -> None`: 停止自动同步线程
- `list_versions() -> List[Dict]`: 列出所有版本

### 命令行接口

```bash
# 执行同步
python tools/memory_sync.py sync [--force] [--no-version] [--no-compress]

# 自动同步
python tools/memory_sync.py auto [--interval <minutes>] [--no-version] [--no-compress]

# 检查一致性
python tools/memory_sync.py check

# 版本管理
python tools/memory_sync.py version --list
python tools/memory_sync.py version --create [--no-compress]
python tools/memory_sync.py version --restore <version>
```

## LLM API模块 (`llm_api.py`)

### 概述
LLM API模块提供了与各种大型语言模型API的集成，支持文本和图像输入。

### 主要函数

#### `load_environment() -> None`
加载环境变量。

#### `encode_image_file(image_path: str) -> Tuple[str, str]`
编码图像文件为base64，并确定其MIME类型。

参数:
- `image_path`: 图像文件路径

返回:
- 编码后的base64字符串和MIME类型

#### `create_llm_client(provider="openai") -> Any`
创建LLM客户端。

参数:
- `provider`: LLM提供商，支持OpenAI、Anthropic、Gemini、DeepSeek、SiliconFlow、OpenRouter等

返回:
- LLM客户端对象

#### `query_llm(prompt: str, client=None, model=None, provider="openai", image_path: Optional[str] = None) -> str`
查询LLM并获取响应。

参数:
- `prompt`: 提示文本
- `client`: LLM客户端对象，如果为None则自动创建
- `model`: 模型名称，如果为None则使用默认模型
- `provider`: LLM提供商
- `image_path`: 可选的图像文件路径

返回:
- LLM的响应文本

### 命令行接口

```bash
python tools/llm_api.py --prompt "提示文本" [--provider <provider>] [--model <model>] [--image <image_path>]
```

## 集成使用示例

### 基本记忆管理流程

```python
from tools.memory_manager import initialize_memory_bank, create_memory_file, update_memory_file, read_memory

# 初始化记忆银行
initialize_memory_bank("项目名称", "项目描述")

# 创建记忆文件
create_memory_file("extensions/custom_notes.md", "# 自定义笔记\n\n初始内容")

# 更新记忆文件
update_memory_file("progress.md", "新的进度信息", append=True)

# 读取记忆文件
content = read_memory("progress.md")
print(content)
```

### 记忆检索与LLM集成

```python
from tools.memory_index import MemoryIndex
from tools.llm_api import query_llm

# 创建记忆索引
memory_index = MemoryIndex()
memory_index.index_memory_bank()

# 搜索记忆
results = memory_index.search("智能体通信协议", top_k=3)
relevant_content = "\n".join([chunk.content for chunk, score in results])

# 将检索结果与LLM集成
prompt = f"基于以下相关内容，回答问题：智能体如何通信？\n\n{relevant_content}"
response = query_llm(prompt, provider="anthropic")
print(response)
```

### 记忆同步和版本管理

```python
from tools.memory_sync import MemorySyncer

# 创建同步器
syncer = MemorySyncer(interval=30, compress=True)

# 执行同步
syncer.sync()

# 创建版本快照
version = syncer._create_version()
print(f"已创建版本：{version}")

# 列出所有版本
versions = syncer.list_versions()
for v in versions:
    print(f"版本: {v['version']}, 时间: {v['timestamp']}, 文件数: {v['file_count']}")
```

*最后更新: 2025-05-08 12:56:34* 