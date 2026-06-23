import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship

from app.models.database import Base


class Learner(Base):
    __tablename__ = "learners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    education_background = Column(String(50), nullable=False, comment="学历背景")
    major = Column(String(100), nullable=False, comment="专业方向")
    work_experience_years = Column(Float, default=0, comment="工作年限")
    self_assessment = Column(JSON, nullable=True, comment="技能自评 {skill: level}")
    learning_style = Column(String(20), nullable=True, comment="学习风格: visual/theory/practice")
    goals = Column(JSON, nullable=True, comment="学习目标列表")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    resources = relationship("Resource", back_populates="learner", lazy="selectin")

    def __repr__(self):
        return f"<Learner(id={self.id}, major={self.major})>"
