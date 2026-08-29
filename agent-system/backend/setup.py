#!/usr/bin/env python3
"""
一键部署初始化脚本

用法:
    cd agent-system/backend
    python setup.py

说明:
    1. 创建管理员账号（默认 admin / admin123，可通过 ADMIN_USERNAME /
       ADMIN_PASSWORD 环境变量覆盖；使用演示默认密码时输出警示）
    2. 构建 ChromaDB 知识库向量索引
    3. 需要确保 .env 中配置了数据库连接和 EMBEDDING_API_KEY

首次部署只需执行此脚本即可完成初始化。
"""

import asyncio
import os
import sys
from pathlib import Path

# 确保能导入 app 模块
sys.path.insert(0, str(Path(__file__).parent))

# 管理员初始凭据：演示默认 admin/admin123，生产部署通过环境变量覆盖
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# ── 第 1 步：创建管理员账号 ──
async def create_admin():
    from app.core.auth import hash_password
    from app.models.database import async_session
    from app.models.user import User
    from sqlalchemy import select

    async with async_session() as db:
        stmt = select(User).where(User.role == "admin")
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  [跳过] 管理员账号已存在: {existing.username}")
            return

        user = User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            email="admin@example.com",
            role="admin",
        )
        db.add(user)
        await db.commit()
        print("  [完成] 管理员账号创建成功")
        print(f"         用户名: {ADMIN_USERNAME}")
        print(f"         密码:   {ADMIN_PASSWORD}")
        if ADMIN_PASSWORD == "admin123":
            print("         ⚠️  当前为演示默认密码，仅限本地/演示环境；"
                  "生产部署请通过 ADMIN_PASSWORD 环境变量指定强密码")
        else:
            print("         ⚠️  请登录后妥善保管密码")


# ── 第 2 步：构建知识库索引 ──
def build_index():
    from app.core.config import get_settings
    from app.knowledge.retriever import KnowledgeRetriever

    settings = get_settings()
    kb_dirs = [d.strip() for d in settings.KNOWLEDGE_BASE_DIRS.split(",") if d.strip()]

    print(f"\n  知识库目录:")
    for d in kb_dirs:
        exists = "✓" if Path(d).exists() else "✗ 不存在"
        print(f"    {exists}  {d}")

    missing = [d for d in kb_dirs if not Path(d).exists()]
    if missing:
        print(f"\n  [警告] 以下目录不存在，请检查 .env 中的 KNOWLEDGE_BASE_DIRS:")
        for d in missing:
            print(f"    - {d}")
        print("  可跳过此步骤，稍后放入知识库文件后重新执行: python setup.py")

    retriever = KnowledgeRetriever()
    stats = retriever.build_index_from_dirs(kb_dirs)
    total = stats["total_chunks"]

    print(f"\n  [完成] 知识库索引构建完成，共 {total} 个知识块")
    print(f"         ChromaDB 存储: {settings.CHROMA_PERSIST_DIR}")


# ── 主流程 ──
def main():
    print("=" * 60)
    print("  领域知识个性化生成系统 — 一键部署初始化")
    print("=" * 60)

    # Step 1
    print("\n[1/2] 创建管理员账号")
    print("-" * 40)
    asyncio.run(create_admin())

    # Step 2
    print("\n[2/2] 构建知识库向量索引")
    print("-" * 40)
    build_index()

    print("\n" + "=" * 60)
    print(" 初始化完成！运行以下命令启动服务:")
    print()
    print("    uvicorn main:app --host 0.0.0.0 --port 8000")
    print()
    print("   B 端管理后台:   http://localhost:3001")
    print("   C 端学习平台:   http://localhost:3000")
    print("   API 文档:      http://localhost:8000/docs")
    print("=" * 60)



if __name__ == "__main__":
    main()
