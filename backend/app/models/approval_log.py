from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(Integer, ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True, comment="学员ID")
    action = Column(String(20), nullable=False, comment="操作: submit | approve | reject")
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="操作人ID")
    reason = Column(Text, nullable=True, comment="备注/理由")
    created_at = Column(DateTime, default=_utcnow, index=True)

    # 关联
    learner = relationship("Learner", lazy="selectin")
    operator = relationship("User", lazy="selectin")

    def __repr__(self):
        return f"<ApprovalLog(id={self.id}, learner_id={self.learner_id}, action={self.action})>"
