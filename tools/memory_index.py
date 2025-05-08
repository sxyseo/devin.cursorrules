#!/usr/bin/env python3
"""
记忆银行向量索引工具

这个脚本提供了对记忆银行内容进行向量索引和语义搜索的功能。
使用BERT嵌入模型将记忆内容转换为向量，并支持相似度搜索。
"""

import os
import sys
import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
import datetime
import re

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("请安装必要的依赖: pip install numpy scikit-learn sentence-transformers", file=sys.stderr)
    sys.exit(1)

# 定义记忆银行的根目录
MEMORY_BANK_DIR = Path("memory-bank")
INDEX_DIR = MEMORY_BANK_DIR / "index"
EMBEDDING_CACHE_FILE = INDEX_DIR / "embeddings.pkl"
CHUNK_INDEX_FILE = INDEX_DIR / "chunks.json"

# 核心文件列表
CORE_FILES = [
    "projectbrief.md",
    "productContext.md",
    "systemPatterns.md",
    "techContext.md",
    "activeContext.md",
    "progress.md"
]

# 将Markdown文件分块的最小和最大尺寸
MIN_CHUNK_SIZE = 100  # 字符
MAX_CHUNK_SIZE = 1000  # 字符

# 默认的嵌入模型
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # 多语言支持

class MemoryChunk:
    """表示记忆银行中的一个内容块"""
    
    def __init__(self, content: str, file_path: str, start_pos: int, end_pos: int, 
                 embedding: Optional[np.ndarray] = None, section: str = ""):
        self.content = content
        self.file_path = file_path
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.embedding = embedding
        self.section = section
        self.last_updated = datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """将对象转换为字典，用于序列化"""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "section": self.section,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryChunk':
        """从字典创建对象，用于反序列化"""
        return cls(
            content=data["content"],
            file_path=data["file_path"],
            start_pos=data["start_pos"],
            end_pos=data["end_pos"],
            section=data.get("section", ""),
            embedding=None  # 嵌入向量在单独的文件中
        )
    
    def __str__(self) -> str:
        return f"MemoryChunk(file='{self.file_path}', section='{self.section}', len={len(self.content)})"

class MemoryIndex:
    """记忆银行索引"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.chunks: List[MemoryChunk] = []
        self.embeddings: Optional[np.ndarray] = None
        self.model = None  # 延迟加载模型
    
    def load_model(self) -> None:
        """加载嵌入模型"""
        if self.model is None:
            print(f"加载嵌入模型: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
    
    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        INDEX_DIR.mkdir(exist_ok=True, parents=True)
    
    def read_file(self, file_path: Path) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}", file=sys.stderr)
            return ""
    
    def extract_sections(self, content: str) -> List[Tuple[str, str, int, int]]:
        """从Markdown内容中提取章节"""
        # 查找所有标题
        headers = re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        sections = []
        last_pos = 0
        
        # 如果找不到标题，则将整个内容作为一个块
        headers_found = False
        
        for match in headers:
            headers_found = True
            header_level = len(match.group(1))
            header_text = match.group(2).strip()
            start_pos = match.start()
            
            # 添加上一个标题到当前标题之间的内容
            if last_pos < start_pos and last_pos > 0:
                prev_header_end = content.find('\n', last_pos)
                if prev_header_end == -1:
                    prev_header_end = last_pos + len(content[last_pos:])
                prev_content = content[prev_header_end:start_pos].strip()
                
                # 获取上一个标题文本
                prev_header_match = re.search(r'^(#{1,6})\s+(.+)$', content[last_pos:prev_header_end], re.MULTILINE)
                prev_header_text = prev_header_match.group(2).strip() if prev_header_match else ""
                
                sections.append((prev_header_text, prev_content, prev_header_end, start_pos))
            
            last_pos = start_pos
        
        # 添加最后一个标题到文件末尾的内容
        if headers_found and last_pos > 0:
            last_header_end = content.find('\n', last_pos)
            if last_header_end == -1:
                last_header_end = last_pos + len(content[last_pos:])
            last_content = content[last_header_end:].strip()
            
            # 获取最后一个标题文本
            last_header_match = re.search(r'^(#{1,6})\s+(.+)$', content[last_pos:last_header_end], re.MULTILINE)
            last_header_text = last_header_match.group(2).strip() if last_header_match else ""
            
            sections.append((last_header_text, last_content, last_header_end, len(content)))
        
        # 如果没有找到标题，将整个内容作为一个块
        if not headers_found:
            sections.append(("", content, 0, len(content)))
        
        return sections
    
    def chunk_content(self, content: str, file_path: str) -> List[MemoryChunk]:
        """将内容分成块"""
        chunks = []
        
        # 提取章节
        sections = self.extract_sections(content)
        
        for section_title, section_content, start_pos, end_pos in sections:
            # 如果章节太短，直接作为一个块
            if len(section_content) <= MAX_CHUNK_SIZE:
                if len(section_content) >= MIN_CHUNK_SIZE:
                    chunks.append(MemoryChunk(
                        content=section_content,
                        file_path=file_path,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        section=section_title
                    ))
                continue
            
            # 否则，按段落分块
            paragraphs = re.split(r'\n\s*\n', section_content)
            current_chunk = ""
            chunk_start = start_pos
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # 如果当前段落太长，单独作为块
                if len(para) > MAX_CHUNK_SIZE:
                    # 如果当前块有内容，先添加
                    if len(current_chunk) >= MIN_CHUNK_SIZE:
                        para_start = section_content.find(current_chunk, 0)
                        if para_start != -1:
                            para_start += start_pos
                            chunks.append(MemoryChunk(
                                content=current_chunk,
                                file_path=file_path,
                                start_pos=para_start,
                                end_pos=para_start + len(current_chunk),
                                section=section_title
                            ))
                        current_chunk = ""
                    
                    # 长段落再细分
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    sub_chunk = ""
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) <= MAX_CHUNK_SIZE:
                            sub_chunk += " " + sentence if sub_chunk else sentence
                        else:
                            if len(sub_chunk) >= MIN_CHUNK_SIZE:
                                para_start = section_content.find(sub_chunk, 0)
                                if para_start != -1:
                                    para_start += start_pos
                                    chunks.append(MemoryChunk(
                                        content=sub_chunk,
                                        file_path=file_path,
                                        start_pos=para_start,
                                        end_pos=para_start + len(sub_chunk),
                                        section=section_title
                                    ))
                            sub_chunk = sentence
                    
                    # 添加最后一个子块
                    if len(sub_chunk) >= MIN_CHUNK_SIZE:
                        para_start = section_content.find(sub_chunk, 0)
                        if para_start != -1:
                            para_start += start_pos
                            chunks.append(MemoryChunk(
                                content=sub_chunk,
                                file_path=file_path,
                                start_pos=para_start,
                                end_pos=para_start + len(sub_chunk),
                                section=section_title
                            ))
                    
                # 正常情况下，合并段落成块
                elif len(current_chunk) + len(para) + 2 <= MAX_CHUNK_SIZE:  # +2 for newlines
                    current_chunk += "\n\n" + para if current_chunk else para
                else:
                    # 当前块已满，添加到结果中
                    if len(current_chunk) >= MIN_CHUNK_SIZE:
                        para_start = section_content.find(current_chunk, 0)
                        if para_start != -1:
                            para_start += start_pos
                            chunks.append(MemoryChunk(
                                content=current_chunk,
                                file_path=file_path,
                                start_pos=para_start,
                                end_pos=para_start + len(current_chunk),
                                section=section_title
                            ))
                    current_chunk = para
            
            # 添加最后一个块
            if current_chunk and len(current_chunk) >= MIN_CHUNK_SIZE:
                para_start = section_content.find(current_chunk, 0)
                if para_start != -1:
                    para_start += start_pos
                    chunks.append(MemoryChunk(
                        content=current_chunk,
                        file_path=file_path,
                        start_pos=para_start,
                        end_pos=para_start + len(current_chunk),
                        section=section_title
                    ))
        
        return chunks
    
    def generate_embeddings(self) -> None:
        """为所有块生成嵌入向量"""
        self.load_model()
        
        contents = [chunk.content for chunk in self.chunks]
        print(f"为 {len(contents)} 个内容块生成嵌入向量...")
        
        embeddings = self.model.encode(contents, show_progress_bar=True)
        self.embeddings = np.array(embeddings)
        
        # 将嵌入向量分配给块
        for i, chunk in enumerate(self.chunks):
            chunk.embedding = self.embeddings[i]
    
    def index_memory_bank(self, force: bool = False) -> None:
        """索引记忆银行中的所有文件"""
        self.ensure_dirs()
        
        # 如果不强制重建索引，尝试加载现有索引
        if not force and self.load_index():
            print("已加载现有索引")
            return
        
        print("开始索引记忆银行...")
        self.chunks = []
        
        # 索引核心文件
        for file_name in CORE_FILES:
            file_path = MEMORY_BANK_DIR / file_name
            if file_path.exists():
                print(f"索引文件: {file_name}")
                content = self.read_file(file_path)
                chunks = self.chunk_content(content, file_name)
                self.chunks.extend(chunks)
        
        # 索引扩展目录
        ext_dir = MEMORY_BANK_DIR / "extensions"
        if ext_dir.exists():
            for ext_file in ext_dir.glob("*.md"):
                rel_path = f"extensions/{ext_file.name}"
                print(f"索引文件: {rel_path}")
                content = self.read_file(ext_file)
                chunks = self.chunk_content(content, rel_path)
                self.chunks.extend(chunks)
        
        # 生成嵌入向量
        self.generate_embeddings()
        
        # 保存索引
        self.save_index()
        
        print(f"索引完成，共索引了 {len(self.chunks)} 个内容块")
    
    def save_index(self) -> None:
        """保存索引到文件"""
        self.ensure_dirs()
        
        # 保存内容块信息（不包括嵌入向量）
        chunks_data = []
        for chunk in self.chunks:
            chunks_data.append(chunk.to_dict())
        
        with open(CHUNK_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        # 单独保存嵌入向量
        if self.embeddings is not None:
            with open(EMBEDDING_CACHE_FILE, 'wb') as f:
                pickle.dump(self.embeddings, f)
        
        print(f"索引已保存到 {INDEX_DIR}")
    
    def load_index(self) -> bool:
        """从文件加载索引"""
        if not CHUNK_INDEX_FILE.exists() or not EMBEDDING_CACHE_FILE.exists():
            return False
        
        try:
            # 加载内容块信息
            with open(CHUNK_INDEX_FILE, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            self.chunks = [MemoryChunk.from_dict(data) for data in chunks_data]
            
            # 加载嵌入向量
            with open(EMBEDDING_CACHE_FILE, 'rb') as f:
                self.embeddings = pickle.load(f)
            
            # 将嵌入向量分配给块
            for i, chunk in enumerate(self.chunks):
                if i < len(self.embeddings):
                    chunk.embedding = self.embeddings[i]
            
            return True
        except Exception as e:
            print(f"加载索引时出错: {e}", file=sys.stderr)
            return False
    
    def search(self, query: str, top_k: int = 5, threshold: float = 0.5) -> List[Tuple[MemoryChunk, float]]:
        """搜索记忆银行"""
        if not self.chunks or self.embeddings is None:
            if not self.load_index():
                print("索引不存在，请先运行 'index' 命令", file=sys.stderr)
                return []
        
        self.load_model()
        
        # 生成查询的嵌入向量
        query_embedding = self.model.encode([query])[0]
        
        # 计算相似度
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        
        # 找出相似度最高的块
        results = []
        for i in range(len(similarities)):
            if similarities[i] >= threshold:
                results.append((self.chunks[i], similarities[i]))
        
        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 top_k 个结果
        return results[:top_k]
    
    def exact_search(self, query: str, case_sensitive: bool = False) -> List[MemoryChunk]:
        """精确搜索记忆银行"""
        if not self.chunks:
            if not self.load_index():
                print("索引不存在，请先运行 'index' 命令", file=sys.stderr)
                return []
        
        results = []
        
        # 如果不区分大小写，转换查询为小写
        if not case_sensitive:
            query = query.lower()
        
        for chunk in self.chunks:
            content = chunk.content
            if not case_sensitive:
                content = content.lower()
            
            if query in content:
                results.append(chunk)
        
        return results

def format_search_results(results: List[Tuple[MemoryChunk, float]], show_scores: bool = True) -> str:
    """格式化搜索结果"""
    if not results:
        return "没有找到匹配的结果"
    
    output = []
    for i, (chunk, score) in enumerate(results):
        output.append(f"\n===== 结果 {i+1} " + ("=" * 50))
        output.append(f"文件: {chunk.file_path}")
        if chunk.section:
            output.append(f"章节: {chunk.section}")
        if show_scores:
            output.append(f"相似度: {score:.4f}")
        output.append("\n" + chunk.content + "\n")
    
    return "\n".join(output)

def format_exact_results(results: List[MemoryChunk]) -> str:
    """格式化精确搜索结果"""
    if not results:
        return "没有找到匹配的结果"
    
    output = []
    for i, chunk in enumerate(results):
        output.append(f"\n===== 结果 {i+1} " + ("=" * 50))
        output.append(f"文件: {chunk.file_path}")
        if chunk.section:
            output.append(f"章节: {chunk.section}")
        output.append("\n" + chunk.content + "\n")
    
    return "\n".join(output)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="记忆银行向量索引工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 索引命令
    index_parser = subparsers.add_parser("index", help="索引记忆银行")
    index_parser.add_argument("--force", action="store_true", help="强制重建索引")
    index_parser.add_argument("--model", default=DEFAULT_MODEL, help=f"嵌入模型名称，默认为 {DEFAULT_MODEL}")
    
    # 搜索命令
    search_parser = subparsers.add_parser("search", help="语义搜索记忆银行")
    search_parser.add_argument("query", help="搜索查询")
    search_parser.add_argument("--top-k", type=int, default=5, help="返回的结果数量")
    search_parser.add_argument("--threshold", type=float, default=0.5, help="相似度阈值")
    search_parser.add_argument("--exact", action="store_true", help="使用精确匹配而不是语义搜索")
    search_parser.add_argument("--case-sensitive", action="store_true", help="区分大小写（仅用于精确搜索）")
    search_parser.add_argument("--hide-scores", action="store_true", help="隐藏相似度分数")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    if args.command == "index":
        index = MemoryIndex(args.model)
        index.index_memory_bank(args.force)
    
    elif args.command == "search":
        index = MemoryIndex()
        
        if args.exact:
            results = index.exact_search(args.query, args.case_sensitive)
            print(format_exact_results(results))
        else:
            results = index.search(args.query, args.top_k, args.threshold)
            print(format_search_results(results, not args.hide_scores))
    
    else:
        print("未指定命令，使用 -h 查看帮助", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 