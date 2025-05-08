#!/usr/bin/env python3
"""
记忆银行同步工具

这个脚本提供了记忆银行的自动同步功能，包括增量同步和数据一致性检查。
使用LZ4压缩算法进行记忆固化，并维护版本控制。
"""

import os
import sys
import argparse
import time
import json
import datetime
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
import threading
import signal

try:
    import lz4.frame
except ImportError:
    print("请安装必要的依赖: pip install lz4", file=sys.stderr)
    print("或使用: pip install -e .[sync]", file=sys.stderr)
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("memory_sync")

# 定义记忆银行的根目录
MEMORY_BANK_DIR = Path("memory-bank")
SYNC_DIR = MEMORY_BANK_DIR / "sync"
VERSIONS_DIR = MEMORY_BANK_DIR / "versions"
SYNC_STATE_FILE = SYNC_DIR / "sync_state.json"

# 核心文件列表
CORE_FILES = [
    "projectbrief.md",
    "productContext.md",
    "systemPatterns.md",
    "techContext.md",
    "activeContext.md",
    "progress.md"
]

# 同步状态定义
class SyncState:
    """记忆银行同步状态"""
    
    def __init__(self, state_file: Path = SYNC_STATE_FILE):
        self.state_file = state_file
        self.file_hashes: Dict[str, str] = {}
        self.last_sync: str = ""
        self.last_version: str = ""
        self.sync_count: int = 0
        self.load()
    
    def load(self) -> bool:
        """从文件加载同步状态"""
        if not self.state_file.exists():
            return False
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.file_hashes = data.get("file_hashes", {})
                self.last_sync = data.get("last_sync", "")
                self.last_version = data.get("last_version", "")
                self.sync_count = data.get("sync_count", 0)
                return True
        except Exception as e:
            logger.error(f"加载同步状态时出错: {e}")
            return False
    
    def save(self) -> bool:
        """保存同步状态到文件"""
        try:
            self.state_file.parent.mkdir(exist_ok=True, parents=True)
            
            data = {
                "file_hashes": self.file_hashes,
                "last_sync": self.last_sync,
                "last_version": self.last_version,
                "sync_count": self.sync_count
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"保存同步状态时出错: {e}")
            return False

class MemorySyncer:
    """记忆银行同步器"""
    
    def __init__(self, interval: int = 30, compress: bool = True, auto_version: bool = True):
        """
        初始化同步器
        
        Args:
            interval: 同步间隔（分钟）
            compress: 是否使用LZ4压缩
            auto_version: 是否自动创建版本
        """
        self.interval = interval
        self.compress = compress
        self.auto_version = auto_version
        self.state = SyncState()
        self.running = False
        self.timer = None
        self.stop_event = threading.Event()
        
        # 计算文件列表
        self.files_to_sync = self._get_memory_files()
    
    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        SYNC_DIR.mkdir(exist_ok=True, parents=True)
        VERSIONS_DIR.mkdir(exist_ok=True, parents=True)
    
    def _get_memory_files(self) -> List[str]:
        """获取记忆银行中的所有文件"""
        files = []
        
        # 首先包含核心文件
        for file_name in CORE_FILES:
            file_path = MEMORY_BANK_DIR / file_name
            if file_path.exists():
                rel_path = file_path.relative_to(MEMORY_BANK_DIR)
                files.append(str(rel_path))
        
        # 然后包含扩展目录中的文件
        ext_dir = MEMORY_BANK_DIR / "extensions"
        if ext_dir.exists():
            for file_path in ext_dir.glob("**/*.md"):
                rel_path = file_path.relative_to(MEMORY_BANK_DIR)
                files.append(str(rel_path))
        
        return sorted(files)
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件的哈希值"""
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"计算文件哈希值时出错: {file_path}, {e}")
            return ""
    
    def _get_changed_files(self) -> Dict[str, str]:
        """获取已更改的文件及其哈希值"""
        changed_files = {}
        
        for rel_path in self.files_to_sync:
            file_path = MEMORY_BANK_DIR / rel_path
            if not file_path.exists():
                continue
            
            # 计算当前哈希值
            current_hash = self._compute_file_hash(file_path)
            if not current_hash:
                continue
            
            # 与上次同步的哈希值比较
            if rel_path not in self.state.file_hashes or self.state.file_hashes[rel_path] != current_hash:
                changed_files[rel_path] = current_hash
        
        return changed_files
    
    def _compress_file(self, source_path: Path, target_path: Path) -> bool:
        """使用LZ4压缩文件"""
        try:
            with open(source_path, 'rb') as f:
                data = f.read()
            
            compressed_data = lz4.frame.compress(data)
            
            with open(target_path, 'wb') as f:
                f.write(compressed_data)
            
            return True
        except Exception as e:
            logger.error(f"压缩文件时出错: {source_path}, {e}")
            return False
    
    def _decompress_file(self, source_path: Path, target_path: Path) -> bool:
        """使用LZ4解压缩文件"""
        try:
            with open(source_path, 'rb') as f:
                compressed_data = f.read()
            
            decompressed_data = lz4.frame.decompress(compressed_data)
            
            with open(target_path, 'wb') as f:
                f.write(decompressed_data)
            
            return True
        except Exception as e:
            logger.error(f"解压缩文件时出错: {source_path}, {e}")
            return False
    
    def _create_version(self, timestamp: str = None) -> str:
        """创建记忆库的版本快照"""
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        version_dir = VERSIONS_DIR / timestamp
        version_dir.mkdir(exist_ok=True, parents=True)
        
        # 复制所有文件到版本目录
        success = True
        for rel_path in self.files_to_sync:
            source_path = MEMORY_BANK_DIR / rel_path
            if not source_path.exists():
                continue
            
            target_path = version_dir / rel_path
            target_path.parent.mkdir(exist_ok=True, parents=True)
            
            try:
                # 如果启用压缩，则使用LZ4压缩
                if self.compress:
                    compressed_path = target_path.with_suffix(target_path.suffix + ".lz4")
                    if not self._compress_file(source_path, compressed_path):
                        success = False
                else:
                    shutil.copy2(source_path, target_path)
            except Exception as e:
                logger.error(f"创建版本快照时出错: {rel_path}, {e}")
                success = False
        
        # 保存版本元数据
        metadata = {
            "timestamp": timestamp,
            "compressed": self.compress,
            "files": self.files_to_sync,
            "prev_version": self.state.last_version
        }
        
        with open(version_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        if success:
            logger.info(f"已创建版本快照: {timestamp}")
            self.state.last_version = timestamp
            self.state.save()
        
        return timestamp
    
    def _restore_version(self, version: str) -> bool:
        """从版本快照恢复记忆库"""
        version_dir = VERSIONS_DIR / version
        if not version_dir.exists():
            logger.error(f"版本不存在: {version}")
            return False
        
        # 读取版本元数据
        try:
            with open(version_dir / "metadata.json", 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"读取版本元数据时出错: {version}, {e}")
            return False
        
        compressed = metadata.get("compressed", False)
        files = metadata.get("files", [])
        
        # 备份当前记忆库
        backup_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = MEMORY_BANK_DIR.with_name(f"{MEMORY_BANK_DIR.name}_backup_{backup_timestamp}")
        
        try:
            # 创建当前记忆库的备份
            shutil.copytree(MEMORY_BANK_DIR, backup_dir)
            logger.info(f"已备份当前记忆库: {backup_dir}")
        except Exception as e:
            logger.error(f"备份记忆库时出错: {e}")
            return False
        
        # 恢复文件
        success = True
        for rel_path in files:
            source_path = version_dir / rel_path
            compressed_path = source_path.with_suffix(source_path.suffix + ".lz4")
            target_path = MEMORY_BANK_DIR / rel_path
            
            # 确保目标目录存在
            target_path.parent.mkdir(exist_ok=True, parents=True)
            
            try:
                if compressed and compressed_path.exists():
                    # 使用LZ4解压缩
                    if not self._decompress_file(compressed_path, target_path):
                        success = False
                elif source_path.exists():
                    # 直接复制
                    shutil.copy2(source_path, target_path)
                else:
                    logger.warning(f"版本中缺少文件: {rel_path}")
            except Exception as e:
                logger.error(f"恢复文件时出错: {rel_path}, {e}")
                success = False
        
        if success:
            logger.info(f"已恢复到版本: {version}")
            
            # 更新同步状态
            self.state.file_hashes = {}
            for rel_path in self.files_to_sync:
                file_path = MEMORY_BANK_DIR / rel_path
                if file_path.exists():
                    self.state.file_hashes[rel_path] = self._compute_file_hash(file_path)
            
            self.state.last_sync = datetime.datetime.now().isoformat()
            self.state.save()
        else:
            logger.error(f"恢复版本时出错: {version}")
            logger.info(f"可以从备份恢复: {backup_dir}")
        
        return success
    
    def _check_consistency(self) -> Dict[str, str]:
        """检查数据一致性，返回不一致的文件"""
        inconsistent_files = {}
        
        for rel_path, stored_hash in self.state.file_hashes.items():
            file_path = MEMORY_BANK_DIR / rel_path
            if not file_path.exists():
                inconsistent_files[rel_path] = "文件丢失"
                continue
            
            current_hash = self._compute_file_hash(file_path)
            if current_hash != stored_hash:
                inconsistent_files[rel_path] = "哈希值不匹配"
        
        return inconsistent_files
    
    def sync(self, force: bool = False) -> bool:
        """执行同步操作
        
        Args:
            force: 是否强制同步所有文件
            
        Returns:
            同步是否成功
        """
        self.ensure_dirs()
        
        # 获取已更改的文件
        if force:
            changed_files = {rel_path: self._compute_file_hash(MEMORY_BANK_DIR / rel_path) 
                            for rel_path in self.files_to_sync 
                            if (MEMORY_BANK_DIR / rel_path).exists()}
        else:
            changed_files = self._get_changed_files()
        
        # 如果没有文件更改，则跳过
        if not changed_files:
            logger.info("没有文件更改，跳过同步")
            return True
        
        # 同步更改的文件
        logger.info(f"开始同步 {len(changed_files)} 个文件...")
        
        # 更新哈希值
        for rel_path, file_hash in changed_files.items():
            self.state.file_hashes[rel_path] = file_hash
        
        # 更新同步状态
        self.state.last_sync = datetime.datetime.now().isoformat()
        self.state.sync_count += 1
        
        # 创建版本快照
        if self.auto_version:
            version_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._create_version(version_timestamp)
        
        # 保存同步状态
        self.state.save()
        
        logger.info(f"同步完成，已更新 {len(changed_files)} 个文件")
        return True
    
    def start_auto_sync(self) -> None:
        """启动自动同步线程"""
        if self.running:
            logger.warning("自动同步已在运行中")
            return
        
        self.running = True
        self.stop_event.clear()
        
        def sync_worker():
            while not self.stop_event.is_set():
                try:
                    # 执行同步
                    logger.info(f"执行定时同步，间隔 {self.interval} 分钟")
                    self.sync()
                except Exception as e:
                    logger.error(f"自动同步时出错: {e}")
                
                # 等待下一次同步
                for _ in range(self.interval * 60):  # 转换为秒
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        # 启动同步线程
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
        
        logger.info(f"已启动自动同步，间隔 {self.interval} 分钟")
    
    def stop_auto_sync(self) -> None:
        """停止自动同步线程"""
        if not self.running:
            logger.warning("自动同步未在运行")
            return
        
        self.stop_event.set()
        self.running = False
        
        logger.info("已停止自动同步")
    
    def list_versions(self) -> List[Dict]:
        """列出所有版本"""
        versions = []
        
        if not VERSIONS_DIR.exists():
            return versions
        
        for version_dir in sorted(VERSIONS_DIR.glob("*"), key=lambda x: x.name, reverse=True):
            if not version_dir.is_dir():
                continue
            
            metadata_file = version_dir / "metadata.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    versions.append({
                        "version": version_dir.name,
                        "timestamp": metadata.get("timestamp", version_dir.name),
                        "compressed": metadata.get("compressed", False),
                        "file_count": len(metadata.get("files", [])),
                        "prev_version": metadata.get("prev_version", "")
                    })
            except Exception as e:
                logger.error(f"读取版本元数据时出错: {version_dir.name}, {e}")
        
        return versions

def signal_handler(sig, frame):
    """信号处理器，用于优雅退出"""
    print("\n正在退出...")
    sys.exit(0)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="记忆银行同步工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 同步命令
    sync_parser = subparsers.add_parser("sync", help="执行同步操作")
    sync_parser.add_argument("--force", action="store_true", help="强制同步所有文件")
    sync_parser.add_argument("--no-version", action="store_true", help="不创建版本快照")
    sync_parser.add_argument("--no-compress", action="store_true", help="不使用LZ4压缩")
    
    # 自动同步命令
    auto_parser = subparsers.add_parser("auto", help="启动自动同步")
    auto_parser.add_argument("--interval", type=int, default=30, help="同步间隔（分钟），默认为30")
    auto_parser.add_argument("--no-version", action="store_true", help="不创建版本快照")
    auto_parser.add_argument("--no-compress", action="store_true", help="不使用LZ4压缩")
    
    # 检查一致性命令
    subparsers.add_parser("check", help="检查数据一致性")
    
    # 版本命令
    version_parser = subparsers.add_parser("version", help="管理版本")
    version_parser.add_argument("--list", action="store_true", help="列出所有版本")
    version_parser.add_argument("--create", action="store_true", help="创建版本快照")
    version_parser.add_argument("--restore", metavar="VERSION", help="从版本恢复")
    version_parser.add_argument("--no-compress", action="store_true", help="不使用LZ4压缩")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    if args.command == "sync":
        syncer = MemorySyncer(
            compress=not args.no_compress,
            auto_version=not args.no_version
        )
        syncer.sync(args.force)
    
    elif args.command == "auto":
        # 设置信号处理器，优雅退出
        signal.signal(signal.SIGINT, signal_handler)
        
        syncer = MemorySyncer(
            interval=args.interval,
            compress=not args.no_compress,
            auto_version=not args.no_version
        )
        
        # 先执行一次同步
        syncer.sync()
        
        # 启动自动同步
        syncer.start_auto_sync()
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            syncer.stop_auto_sync()
            print("\n已停止自动同步")
    
    elif args.command == "check":
        syncer = MemorySyncer()
        inconsistent_files = syncer._check_consistency()
        
        if inconsistent_files:
            print("发现不一致的文件:")
            for rel_path, reason in inconsistent_files.items():
                print(f"- {rel_path}: {reason}")
        else:
            print("数据一致性检查通过")
    
    elif args.command == "version":
        syncer = MemorySyncer(compress=not args.no_compress)
        
        if args.list:
            versions = syncer.list_versions()
            if versions:
                print("版本列表:")
                for v in versions:
                    print(f"- {v['version']} ({'压缩' if v['compressed'] else '未压缩'}, {v['file_count']} 个文件)")
            else:
                print("没有找到版本")
        
        elif args.create:
            version = syncer._create_version()
            print(f"已创建版本快照: {version}")
        
        elif args.restore:
            success = syncer._restore_version(args.restore)
            if success:
                print(f"已成功恢复到版本: {args.restore}")
            else:
                print(f"恢复版本时出错: {args.restore}")
                return 1
    
    else:
        print("未指定命令，使用 -h 查看帮助", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 