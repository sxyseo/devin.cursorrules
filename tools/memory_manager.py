#!/usr/bin/env python3
"""
记忆银行管理工具

这个脚本提供了管理记忆银行的功能，包括读取、创建和更新记忆文件。
记忆银行是一组Markdown文件，用于存储项目的上下文和知识。
"""

import os
import sys
import argparse
import datetime
from pathlib import Path
import shutil
import json
from typing import Dict, List, Optional, Union

# 定义记忆银行的根目录
MEMORY_BANK_DIR = Path("memory-bank")

# 核心文件列表
CORE_FILES = [
    "projectbrief.md",
    "productContext.md",
    "systemPatterns.md",
    "techContext.md",
    "activeContext.md",
    "progress.md"
]

# 文件默认模板
DEFAULT_TEMPLATES = {
    "projectbrief.md": """# 项目简介

## 项目目标
<!-- 描述项目的主要目标和愿景 -->

## 核心需求
<!-- 列出项目的核心需求 -->

## 范围边界
<!-- 明确说明项目的范围和边界 -->

## 关键成功指标
<!-- 定义项目成功的关键指标 -->

*最后更新: {date}*
""",
    
    "productContext.md": """# 产品上下文

## 为什么存在这个项目
<!-- 解释这个项目存在的原因 -->

## 解决什么问题
<!-- 详细描述项目解决的问题 -->

## 期望的工作方式
<!-- 说明产品应该如何工作 -->

## 用户体验目标
<!-- 描述产品的用户体验目标 -->

*最后更新: {date}*
""",
    
    "systemPatterns.md": """# 系统架构与模式

## 整体架构
<!-- 描述系统的整体架构 -->

## 关键技术决策
<!-- 列出已做出的关键技术决策 -->

## 设计模式
<!-- 描述系统中使用的设计模式 -->

## 组件关系
<!-- 解释系统组件之间的关系 -->

*最后更新: {date}*
""",
    
    "techContext.md": """# 技术上下文

## 使用的技术栈
<!-- 列出项目使用的技术栈 -->

## 开发环境
<!-- 描述开发环境设置 -->

## 技术约束
<!-- 列出技术约束 -->

## 依赖关系
<!-- 描述项目的依赖关系 -->

*最后更新: {date}*
""",
    
    "activeContext.md": """# 当前工作上下文

## 当前工作重点
<!-- 描述当前的工作重点 -->

## 最近变更
<!-- 列出最近的变更 -->

## 下一步计划
<!-- 描述下一步的计划 -->

## 活动决策
<!-- 记录正在考虑的决策 -->

*最后更新: {date}*
""",
    
    "progress.md": """# 项目进度

## 已完成工作
<!-- 列出已完成的工作 -->

## 正在进行
<!-- 描述正在进行的工作 -->

## 待办事项
<!-- 列出待办事项 -->

## 已知问题
<!-- 记录已知的问题 -->

*最后更新: {date}*
"""
}

def ensure_memory_bank_dir() -> None:
    """确保记忆银行目录存在，如果不存在则创建"""
    MEMORY_BANK_DIR.mkdir(exist_ok=True)
    (MEMORY_BANK_DIR / "extensions").mkdir(exist_ok=True)

def read_file(file_path: Path) -> str:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}", file=sys.stderr)
        return f"无法读取文件 {file_path}: {e}"

def write_file(file_path: Path, content: str) -> bool:
    """写入文件内容"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文件 {file_path} 时出错: {e}", file=sys.stderr)
        return False

def validate_memory_bank() -> Dict[str, bool]:
    """验证记忆银行文件的完整性"""
    result = {}
    for file_name in CORE_FILES:
        file_path = MEMORY_BANK_DIR / file_name
        result[file_name] = file_path.exists()
    return result

def read_memory(file_name: Optional[str] = None) -> Union[str, Dict[str, str]]:
    """读取记忆银行中的文件

    Args:
        file_name: 要读取的文件名，如果为None，则读取所有核心文件

    Returns:
        如果指定了文件名，返回文件内容；否则返回文件名到内容的字典
    """
    ensure_memory_bank_dir()
    
    if file_name:
        if '/' in file_name or '\\' in file_name:
            file_path = MEMORY_BANK_DIR / file_name
        else:
            file_path = MEMORY_BANK_DIR / file_name
        
        if not file_path.exists():
            return f"文件 {file_name} 不存在"
        
        return read_file(file_path)
    else:
        # 读取所有核心文件
        result = {}
        for core_file in CORE_FILES:
            file_path = MEMORY_BANK_DIR / core_file
            if file_path.exists():
                result[core_file] = read_file(file_path)
            else:
                result[core_file] = f"文件 {core_file} 不存在"
        
        # 读取扩展目录中的文件
        ext_dir = MEMORY_BANK_DIR / "extensions"
        if ext_dir.exists():
            for ext_file in ext_dir.glob("*.md"):
                file_name = f"extensions/{ext_file.name}"
                result[file_name] = read_file(ext_file)
        
        return result

def create_memory_file(file_name: str, template: Optional[str] = None, overwrite: bool = False) -> bool:
    """创建记忆银行文件

    Args:
        file_name: 要创建的文件名
        template: 文件模板，如果为None则使用默认模板
        overwrite: 是否覆盖现有文件

    Returns:
        创建是否成功
    """
    ensure_memory_bank_dir()
    
    if '/' in file_name or '\\' in file_name:
        parts = file_name.replace('\\', '/').split('/')
        dir_path = MEMORY_BANK_DIR.joinpath(*parts[:-1])
        dir_path.mkdir(exist_ok=True, parents=True)
        file_path = MEMORY_BANK_DIR / file_name
    else:
        file_path = MEMORY_BANK_DIR / file_name
    
    if file_path.exists() and not overwrite:
        print(f"文件 {file_name} 已存在，使用 --overwrite 选项覆盖", file=sys.stderr)
        return False
    
    if template is None:
        base_name = file_path.name
        if base_name in DEFAULT_TEMPLATES:
            template = DEFAULT_TEMPLATES[base_name].format(date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            template = f"# {Path(file_name).stem.replace('_', ' ').title()}\n\n<!-- 添加内容 -->\n\n*最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    
    return write_file(file_path, template)

def update_memory_file(file_name: str, content: Optional[str] = None, append: bool = False) -> bool:
    """更新记忆银行文件

    Args:
        file_name: 要更新的文件名
        content: 新的文件内容，如果为None则从标准输入读取
        append: 是否追加到现有内容

    Returns:
        更新是否成功
    """
    ensure_memory_bank_dir()
    
    if '/' in file_name or '\\' in file_name:
        file_path = MEMORY_BANK_DIR / file_name
    else:
        file_path = MEMORY_BANK_DIR / file_name
    
    if not file_path.exists():
        print(f"文件 {file_name} 不存在，请先创建", file=sys.stderr)
        return False
    
    if content is None:
        print("请输入文件内容 (Ctrl+D 或 Ctrl+Z 结束):")
        try:
            content = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n已取消", file=sys.stderr)
            return False
    
    if append:
        existing_content = read_file(file_path)
        content = existing_content + "\n\n" + content
    
    # 更新最后更新时间
    timestamp = f"*最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    if "*最后更新:" in content:
        content = content.replace("*最后更新:*", timestamp)
    else:
        content = content + "\n\n" + timestamp
    
    return write_file(file_path, content)

def backup_memory_bank(backup_name: Optional[str] = None) -> bool:
    """备份记忆银行

    Args:
        backup_name: 备份名称，如果为None则使用当前时间

    Returns:
        备份是否成功
    """
    if not MEMORY_BANK_DIR.exists():
        print("记忆银行目录不存在，无法备份", file=sys.stderr)
        return False
    
    if backup_name is None:
        backup_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_dir = Path(f"memory-bank-backup-{backup_name}")
    try:
        shutil.copytree(MEMORY_BANK_DIR, backup_dir)
        print(f"已备份记忆银行到 {backup_dir}")
        return True
    except Exception as e:
        print(f"备份记忆银行失败: {e}", file=sys.stderr)
        return False

def restore_memory_bank(backup_name: str) -> bool:
    """恢复记忆银行

    Args:
        backup_name: 备份名称

    Returns:
        恢复是否成功
    """
    backup_dir = Path(f"memory-bank-backup-{backup_name}")
    if not backup_dir.exists():
        print(f"备份 {backup_name} 不存在", file=sys.stderr)
        return False
    
    try:
        if MEMORY_BANK_DIR.exists():
            # 创建当前记忆银行的备份
            current_backup = f"memory-bank-before-restore-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(MEMORY_BANK_DIR, Path(current_backup))
            print(f"已备份当前记忆银行到 {current_backup}")
            
            # 删除当前记忆银行
            shutil.rmtree(MEMORY_BANK_DIR)
        
        # 恢复备份
        shutil.copytree(backup_dir, MEMORY_BANK_DIR)
        print(f"已从 {backup_dir} 恢复记忆银行")
        return True
    except Exception as e:
        print(f"恢复记忆银行失败: {e}", file=sys.stderr)
        return False

def initialize_memory_bank(project_name: str, description: str) -> bool:
    """初始化记忆银行

    Args:
        project_name: 项目名称
        description: 项目描述

    Returns:
        初始化是否成功
    """
    ensure_memory_bank_dir()
    
    # 检查是否已经初始化
    validation = validate_memory_bank()
    if all(validation.values()):
        print("记忆银行已经初始化", file=sys.stderr)
        return False
    
    # 创建缺少的核心文件
    for file_name in CORE_FILES:
        if not validation.get(file_name, False):
            if file_name == "projectbrief.md":
                # 为项目简介添加项目名称和描述
                template = DEFAULT_TEMPLATES[file_name].format(date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                template = template.replace("# 项目简介", f"# {project_name}")
                template = template.replace("<!-- 描述项目的主要目标和愿景 -->", description)
                create_memory_file(file_name, template, overwrite=True)
            else:
                create_memory_file(file_name, overwrite=True)
    
    # 创建配置文件
    config = {
        "project_name": project_name,
        "created_at": datetime.datetime.now().isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    
    with open(MEMORY_BANK_DIR / "config.json", 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"已初始化记忆银行，项目名称: {project_name}")
    return True

def list_memory_files() -> List[str]:
    """列出记忆银行中的所有文件"""
    ensure_memory_bank_dir()
    
    files = []
    for file_path in MEMORY_BANK_DIR.glob("**/*.md"):
        rel_path = file_path.relative_to(MEMORY_BANK_DIR)
        files.append(str(rel_path))
    
    return sorted(files)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="记忆银行管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 初始化命令
    init_parser = subparsers.add_parser("init", help="初始化记忆银行")
    init_parser.add_argument("--project-name", required=True, help="项目名称")
    init_parser.add_argument("--description", required=True, help="项目描述")
    
    # 读取命令
    read_parser = subparsers.add_parser("read", help="读取记忆文件")
    read_parser.add_argument("file", nargs="?", help="要读取的文件名，如果为'all'则读取所有文件")
    
    # 创建命令
    create_parser = subparsers.add_parser("create", help="创建记忆文件")
    create_parser.add_argument("file", help="要创建的文件名")
    create_parser.add_argument("--template", help="文件模板路径")
    create_parser.add_argument("--overwrite", action="store_true", help="是否覆盖现有文件")
    
    # 更新命令
    update_parser = subparsers.add_parser("update", help="更新记忆文件")
    update_parser.add_argument("file", help="要更新的文件名")
    update_parser.add_argument("--content", help="新的文件内容")
    update_parser.add_argument("--append", action="store_true", help="是否追加到现有内容")
    
    # 验证命令
    subparsers.add_parser("validate", help="验证记忆银行的完整性")
    
    # 列表命令
    subparsers.add_parser("list", help="列出记忆银行中的所有文件")
    
    # 备份命令
    backup_parser = subparsers.add_parser("backup", help="备份记忆银行")
    backup_parser.add_argument("--name", help="备份名称")
    
    # 恢复命令
    restore_parser = subparsers.add_parser("restore", help="恢复记忆银行")
    restore_parser.add_argument("name", help="备份名称")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    if args.command == "init":
        initialize_memory_bank(args.project_name, args.description)
    
    elif args.command == "read":
        if args.file == "all" or args.file is None:
            memory_contents = read_memory()
            for file_name, content in memory_contents.items():
                print(f"\n=== {file_name} ===\n")
                print(content)
                print("\n" + "=" * (len(file_name) + 8) + "\n")
        else:
            content = read_memory(args.file)
            print(content)
    
    elif args.command == "create":
        template = None
        if args.template:
            with open(args.template, 'r', encoding='utf-8') as f:
                template = f.read()
        
        success = create_memory_file(args.file, template, args.overwrite)
        if success:
            print(f"已创建文件 {args.file}")
    
    elif args.command == "update":
        success = update_memory_file(args.file, args.content, args.append)
        if success:
            print(f"已更新文件 {args.file}")
    
    elif args.command == "validate":
        validation = validate_memory_bank()
        all_valid = all(validation.values())
        
        print("记忆银行验证结果:")
        for file_name, exists in validation.items():
            status = "存在" if exists else "缺失"
            print(f"- {file_name}: {status}")
        
        if all_valid:
            print("\n记忆银行完整")
        else:
            missing_files = [f for f, exists in validation.items() if not exists]
            print(f"\n记忆银行不完整，缺少以下文件: {', '.join(missing_files)}")
            print("可以使用 'memory_manager.py init' 命令初始化记忆银行")
    
    elif args.command == "list":
        files = list_memory_files()
        print("记忆银行文件列表:")
        for file in files:
            print(f"- {file}")
    
    elif args.command == "backup":
        backup_memory_bank(args.name)
    
    elif args.command == "restore":
        restore_memory_bank(args.name)
    
    else:
        print("未指定命令，使用 -h 查看帮助", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 