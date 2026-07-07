from datetime import datetime, timedelta
from typing import Optional
import hashlib

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.database import get_db

# JWT Bearer 方案
security = HTTPBearer()

# JWT 配置
settings = get_settings()
SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时


def hash_password(password: str) -> str:
    """密码加密（直接使用 bcrypt）"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（直接使用 bcrypt）"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI 依赖：从 JWT token 获取当前用户"""
    from app.models.user import User

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的 token")

    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


async def require_admin(
    current_user = Depends(get_current_user),
):
    """FastAPI 依赖：要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


def make_session_id(user_id: int, created_at) -> str:
    """
    生成与账户周期绑定的 session_id。
    格式：user-{id}-{created_at_hash 前 8 位}

    同一用户的 created_at 永久不变（除非删库重建），所以 session_id 稳定，
    退出再登录能续接 Redis 里的学习记录。
    删库重建后新用户即使复用了同一个 user_id，created_at 也不同，
    session_id 随之变化，读不到旧用户残留在 Redis 里的脏数据。
    """
    if created_at is None:
        return f"user-{user_id}"
    epoch = hashlib.md5(str(created_at).encode("utf-8")).hexdigest()[:8]
    return f"user-{user_id}-{epoch}"


async def validate_session_ownership(
    session_id: str,
    current_user = Depends(get_current_user),
):
    """
    FastAPI 依赖：校验 session_id 属于当前登录用户。
    session_id 必须与当前用户的账户周期（user_id + created_at）匹配。
    管理员可以访问任意 session。
    """
    if current_user.role == "admin":
        return session_id
    expected = make_session_id(current_user.id, current_user.created_at)
    if session_id != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"无权访问会话 {session_id}，该会话不属于当前用户",
        )
    return session_id
