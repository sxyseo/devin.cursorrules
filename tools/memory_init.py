#!/usr/bin/env python3
"""
记忆银行初始化工具

创建记忆银行的基本目录结构和默认文件。
"""

import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Optional

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('memory_init')

# 记忆银行的路径
script_dir = Path(__file__).parent
memory_bank_dir = script_dir.parent / "memory-bank"

# 核心文件模板
TEMPLATES = {
    "projectbrief.md": """# 项目简介

## 项目概述
[项目名称] 是一个 [简短描述]，旨在 [项目目标]。

## 核心需求
- 需求1：[描述]
- 需求2：[描述]
- 需求3：[描述]

## 项目范围
[描述项目范围，包括内容和不包括的内容]

## 关键利益相关者
- [利益相关者1]
- [利益相关者2]

## 成功标准
1. [标准1]
2. [标准2]
3. [标准3]

## 时间线
- 开始日期：[日期]
- 计划完成日期：[日期]
- 主要里程碑：
  - [里程碑1]：[日期]
  - [里程碑2]：[日期]
""",

    "productContext.md": """# 产品上下文

## 解决的问题
[详细描述该产品解决的主要问题]

## 目标用户
[描述目标用户群体及其特征]

## 用户体验目标
1. [用户体验目标1]
2. [用户体验目标2]
3. [用户体验目标3]

## 主要功能流程
1. [流程1]
2. [流程2]
3. [流程3]

## 竞争产品分析
[描述竞争产品及差异化优势]

## 设计原则
- [原则1]
- [原则2]
- [原则3]
""",

    "systemPatterns.md": """# 系统模式

## 架构概览
[描述高级系统架构]

## 核心组件
1. [组件1]：[描述]
2. [组件2]：[描述]
3. [组件3]：[描述]

## 设计模式
- [模式1]：[用途和实现]
- [模式2]：[用途和实现]
- [模式3]：[用途和实现]

## 数据流
[描述系统中主要数据流向]

## 技术决策
- [决策1]：[理由]
- [决策2]：[理由]
- [决策3]：[理由]

## 扩展点
[描述系统的可扩展性和扩展点]
""",

    "techContext.md": """# 技术上下文

## 技术栈
- 前端：[技术/框架]
- 后端：[技术/框架]
- 数据库：[技术]
- 部署：[环境/平台]

## 开发环境
[描述开发环境设置]

## 构建与部署流程
[描述CI/CD流程]

## 依赖管理
[描述依赖管理策略]

## 测试策略
- 单元测试：[工具/框架]
- 集成测试：[工具/框架]
- 端到端测试：[工具/框架]

## 技术约束
[描述任何技术限制或约束]
""",

    "activeContext.md": """# 活动上下文

## 当前工作重点
[描述当前正在处理的主要任务]

## 最近变更
- [日期]：[变更1]
- [日期]：[变更2]
- [日期]：[变更3]

## 近期问题与解决方案
- 问题1：[描述] -> 解决方案：[描述]
- 问题2：[描述] -> 解决方案：[描述]

## 下一步计划
1. [任务1]
2. [任务2]
3. [任务3]

## 决策点
- [决策1]：[背景和理由]
- [决策2]：[背景和理由]
""",

    "progress.md": """# 进度跟踪

## 已完成工作
- [✓] [任务1]
- [✓] [任务2]

## 进行中工作
- [ ] [任务3]
- [ ] [任务4]

## 待开始工作
- [ ] [任务5]
- [ ] [任务6]

## 已知问题
- [问题1]：[状态]
- [问题2]：[状态]

## 里程碑进度
- [里程碑1]：[状态] ([日期])
- [里程碑2]：[状态] ([日期])
"""
}

def create_memory_bank(project_name: Optional[str] = None, description: Optional[str] = None) -> bool:
    """
    创建记忆银行的基本目录结构和默认文件
    
    Args:
        project_name: 项目名称
        description: 项目描述
    
    Returns:
        bool: 是否成功创建
    """
    try:
        # 创建记忆银行主目录
        memory_bank_dir.mkdir(exist_ok=True)
        logger.info(f"已创建记忆银行主目录：{memory_bank_dir}")
        
        # 创建扩展目录
        extensions_dir = memory_bank_dir / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        logger.info(f"已创建扩展目录：{extensions_dir}")
        
        # 创建核心文件
        for filename, template in TEMPLATES.items():
            file_path = memory_bank_dir / filename
            
            # 如果文件不存在，创建它
            if not file_path.exists():
                # 替换模板中的项目名称和描述
                content = template
                if project_name:
                    content = content.replace("[项目名称]", project_name)
                if description:
                    content = content.replace("[简短描述]", description)
                
                # 写入文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"已创建核心文件：{filename}")
            else:
                logger.info(f"文件已存在，跳过：{filename}")
        
        # 创建元数据文件
        metadata = {
            "created_at": datetime.datetime.now().isoformat(),
            "project_name": project_name or "未命名项目",
            "description": description or "无描述",
            "version": "1.0.0"
        }
        
        metadata_path = memory_bank_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info("记忆银行初始化完成！")
        return True
    
    except Exception as e:
        logger.error(f"创建记忆银行时出错：{e}")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="初始化记忆银行")
    parser.add_argument("--project-name", help="项目名称")
    parser.add_argument("--description", help="项目描述")
    
    args = parser.parse_args()
    
    success = create_memory_bank(
        project_name=args.project_name,
        description=args.description
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 