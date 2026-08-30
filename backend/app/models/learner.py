from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.database import Base, JsonText


def _utcnow() -> datetime:
    """返回当前 UTC 时间"""
    return datetime.now(timezone.utc)


class Learner(Base):
    __tablename__ = "learners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="关联用户")
    education_background = Column(String(50), nullable=False, comment="学历背景")
    major = Column(String(100), nullable=False, comment="专业方向")
    work_experience_years = Column(Float, default=0, comment="工作年限")
    career_track = Column(String(30), default="operator", comment="职业方向: operator/setup_tech/programmer")
    current_level = Column(String(20), nullable=True, comment="用户自评当前水平: beginner/intermediate/advanced/expert")
    self_assessment = Column(JsonText, nullable=True, comment="技能自评")
    learning_style = Column(String(20), nullable=True, comment="学习风格: visual/theory/practice")
    goals = Column(JsonText, nullable=True, comment="学习目标列表")

    # 诊断结果字段
    knowledge_points = Column(JsonText, nullable=True, comment="知识点评分列表 [{name, score, level, confidence}]")
    blind_spots = Column(JsonText, nullable=True, comment="知识盲区列表")
    overall_level = Column(String(20), nullable=True, comment="整体水平: beginner/intermediate/advanced/expert")
    recommended_difficulty = Column(String(20), nullable=True, comment="推荐难度: beginner/intermediate/advanced/expert")
    learning_path = Column(JsonText, nullable=True, comment="学习路径 [{stage, title, topics, estimated_hours, difficulty, prerequisites, resources_type}]")
    kg_progress = Column(JsonText, nullable=True, comment="知识图谱学习进度 {completed_nodes: [...], history: [...], percentage: float}")

    # 机台使用审批
    machine_approval_status = Column(String(20), default="none", nullable=False, index=True, comment="机器使用审批: none | pending | approved | rejected")
    machine_approval_at = Column(DateTime, nullable=True, comment="审批时间")
    machine_approval_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关联
    user = relationship("User", back_populates="learner", foreign_keys=[user_id])
    resources = relationship("Resource", back_populates="learner", lazy="selectin")

    def __repr__(self):
        return f"<Learner(id={self.id}, user_id={self.user_id})>"
