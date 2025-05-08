# 多智能体框架部署指南

## 环境要求

### 系统要求
- 操作系统：支持Windows 10+、macOS 10.15+、Ubuntu 20.04+
- Python版本：Python 3.10或更高版本
- 存储空间：至少1GB可用磁盘空间
- 内存：至少4GB RAM（推荐8GB或以上）
- 网络：稳定的互联网连接（需访问LLM API）

### 依赖要求
- Python基础库：numpy, scipy, matplotlib
- 嵌入模型：sentence-transformers
- 压缩库：lz4
- 矢量数据库（二选一）：
  - FAISS（本地部署）
  - Chroma（支持本地或远程）

## 安装步骤

### 1. 基础环境安装
```bash
# 创建Python虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 更新pip
python -m pip install -U pip
```

### 2. 安装依赖
```bash
# 安装基础依赖
pip install numpy scipy matplotlib

# 安装嵌入模型和压缩库
pip install sentence-transformers lz4

# 安装向量数据库
# 选项1: FAISS
pip install faiss-cpu
# 选项2: Chroma
pip install chromadb
```

### 3. 环境变量配置
创建`.env`文件，设置必要的环境变量：
```
# LLM API密钥
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 记忆库配置
MEMORY_BANK_DIR=memory-bank
VECTOR_DB_TYPE=faiss  # 或 chroma
VECTOR_DB_PATH=memory-bank/vector_db
```

### 4. 初始化记忆银行
```bash
# 创建记忆银行目录
mkdir -p memory-bank/extensions

# 初始化记忆银行
python tools/memory_manager.py init --project-name "项目名称" --description "项目描述"
```

### 5. 创建向量索引
```bash
# 为记忆银行建立索引
python tools/memory_index.py index --model "paraphrase-multilingual-MiniLM-L12-v2"
```

## 操作指南

### 记忆银行管理
```bash
# 列出所有记忆文件
python tools/memory_manager.py list

# 读取特定文件内容
python tools/memory_manager.py read progress.md

# 读取所有文件
python tools/memory_manager.py read all

# 创建新的记忆文件
python tools/memory_manager.py create extensions/custom_file.md

# 更新文件内容
python tools/memory_manager.py update progress.md --content "内容更新"

# 验证记忆银行完整性
python tools/memory_manager.py validate
```

### 记忆同步与版本控制
```bash
# 手动执行同步
python tools/memory_sync.py sync

# 强制同步所有文件
python tools/memory_sync.py sync --force

# 启动自动同步（30分钟间隔）
python tools/memory_sync.py auto --interval 30

# 查看版本列表
python tools/memory_sync.py version --list

# 创建版本快照
python tools/memory_sync.py version --create

# 恢复到特定版本
python tools/memory_sync.py version --restore 20250508_121338
```

### 记忆检索
```bash
# 语义搜索
python tools/memory_index.py search "智能体通信协议" --top-k 3 --threshold 0.6

# 精确搜索
python tools/memory_index.py search "记忆银行结构" --exact
```

## 故障排除

### 常见问题

1. **索引创建失败**
   - 检查是否安装了sentence-transformers库
   - 验证记忆银行目录是否存在并有访问权限
   - 检查磁盘空间是否充足

2. **记忆同步错误**
   - 检查文件写入权限
   - 验证LZ4是否正确安装
   - 检查版本目录是否有访问权限

3. **记忆检索返回不相关结果**
   - 尝试调整阈值参数（--threshold）
   - 考虑重建索引（--force参数）
   - 确认使用的是适当的语言模型

### 日志和调试
- 日志文件位于`logs/`目录
- 设置环境变量`DEBUG=1`可启用详细日志记录
- 使用`--verbose`参数获取更详细的命令输出

## 最佳实践

1. **定期同步**
   - 建议设置自动同步，间隔不超过30分钟
   - 在重要更改后手动执行同步

2. **版本管理**
   - 在重大更改前创建版本快照
   - 保留至少3个最近版本以便回退

3. **记忆组织**
   - 将相关信息分组到同一文件中
   - 使用清晰的章节结构和标题
   - 对核心概念使用一致的术语

4. **性能优化**
   - 对大型记忆库考虑使用FAISS索引
   - 定期清理不再需要的旧版本
   - 监控向量数据库大小，必要时进行压缩

5. **安全考虑**
   - 不要在记忆文件中存储敏感凭据
   - 限制记忆库访问权限
   - 定期备份重要记忆数据

*最后更新: 2025-05-08 12:49:57* 