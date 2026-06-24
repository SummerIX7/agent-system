import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship

from app.models.database import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    learner_id = Column(
        String(36), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False
    )
    session_id = Column(String(36), nullable=False, index=True, comment="会话 ID")
    resource_type = Column(
        Enum("lecture", "guide", "project", "test", name="resource_type_enum"),
        nullable=False,
        comment="资源类型",
    )
    content = Column(Text, nullable=False, comment="生成内容")
    topic = Column(String(200), nullable=False, comment="主题")
    difficulty = Column(String(20), nullable=True, comment="难度等级")
    sources = Column(JSON, nullable=True, comment="知识溯源列表")
    review_score = Column(Float, nullable=True, comment="审核评分 0-1")
    review_passed = Column(
        Enum("pending", "passed", "failed", name="review_status_enum"),
        default="pending",
        comment="审核状态",
    )
    retry_count = Column(Float, default=0, comment="重试次数")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    learner = relationship("Learner", back_populates="resources")

    def __repr__(self):
        return f"<Resource(id={self.id}, type={self.resource_type}, topic={self.topic})>"
