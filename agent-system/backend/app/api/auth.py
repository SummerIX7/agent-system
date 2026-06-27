from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


# ========== 请求/响应模型 ==========

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserInfo(BaseModel):
    id: int
    username: str
    email: Optional[str] = None


# ========== 注册 ==========

@router.post("/register", response_model=TokenResponse)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    # 检查用户名是否已存在
    stmt = select(User).where(User.username == req.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email,
    )
    db.add(user)
    await db.flush()

    # 生成 token
    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


# ========== 登录 ==========

@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    # 查找用户
    stmt = select(User).where(User.username == req.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 token
    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


# ========== 获取当前用户 ==========

@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息"""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
    )
