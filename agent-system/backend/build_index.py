#!/usr/bin/env python3
"""
知识库向量索引构建脚本

用法：
    cd agent-system/backend
    python build_index.py

说明：
    - 会自动加载 KNOWLEDGE_BASE_DIRS 配置中的所有知识库目录
    - 每个目录下的 .md 文件会被解析、切分、嵌入并存入 ChromaDB
    - 需要确保 .env 中配置了有效的 EMBEDDING_API_KEY
"""

import sys
from pathlib import Path

# 确保能导入 app 模块
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.knowledge.retriever import KnowledgeRetriever


def main():
    settings = get_settings()

    # 从配置中获取知识库目录列表
    kb_dirs = [d.strip() for d in settings.KNOWLEDGE_BASE_DIRS.split(",") if d.strip()]

    print("=" * 60)
    print("知识库向量索引构建")
    print("=" * 60)
    print(f"ChromaDB 目录: {settings.CHROMA_PERSIST_DIR}")
    print(f"嵌入模型: {settings.EMBEDDING_MODEL}")
    print(f"知识库目录:")
    for d in kb_dirs:
        exists = "" if Path(d).exists() else " (不存在)"
        print(f"  - {d} {exists}")
    print("=" * 60)

    # 创建检索器
    retriever = KnowledgeRetriever()

    # 从所有目录构建索引
    total = retriever.build_index_from_dirs(kb_dirs)

    print()
    print(f" 索引构建完成！共 {total} 个知识块")
    print(f"   ChromaDB 存储位置: {settings.CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
