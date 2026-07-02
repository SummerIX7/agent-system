import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.models.database import Base


def _utcnow() -> datetime:
    """返回当前 UTC 时间"""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    email = Column(String(100), nullable=True, comment="邮箱")
    role = Column(String(20), default="learner", nullable=False, index=True, comment="角色: learner | admin")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关联：一个用户对应一个画像
    learner = relationship("Learner", back_populates="user", uselist=False, lazy="selectin", foreign_keys="Learner.user_id")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
