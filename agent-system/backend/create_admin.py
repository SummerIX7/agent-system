"""创建默认管理员账号"""
import asyncio
from app.core.auth import hash_password
from app.models.database import async_session
from app.models.user import User
from sqlalchemy import select


async def main():
    async with async_session() as db:
        # 检查是否已存在管理员
        stmt = select(User).where(User.role == "admin")
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"管理员账号已存在: {existing.username}")
            return

        user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            email="admin@example.com",
            role="admin",
        )
        db.add(user)
        await db.commit()
        print("管理员账号创建成功!")
        print("  用户名: admin")
        print("  密码:   admin123")
        print("  ⚠️  请登录后立即修改密码！")


if __name__ == "__main__":
    asyncio.run(main())
