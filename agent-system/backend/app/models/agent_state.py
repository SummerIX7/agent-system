from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from app.models.database import Base, JsonText


def _utcnow() -> datetime:
    """返回当前 UTC 时间"""
    return datetime.now(timezone.utc)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True, comment="会话 ID")
    agent_name = Column(String(50), nullable=False, comment="Agent 名称")
    status = Column(
        Enum("idle", "running", "completed", "error", name="agent_status_enum"),
        nullable=False,
        default="idle",
        comment="状态",
    )
    message = Column(String(500), nullable=True, comment="状态消息")
    progress = Column(Float, default=0, comment="进度 0-100")
    input_data = Column(JsonText, nullable=True, comment="输入数据")
    output_data = Column(JsonText, nullable=True, comment="输出数据")
    created_at = Column(DateTime, default=_utcnow)

    def __repr__(self):
        return f"<AgentLog(agent={self.agent_name}, status={self.status})>"


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True, comment="会话 ID")
    learner_id = Column(Integer, ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True, comment="学习者 ID")
    topic = Column(String(200), nullable=False, comment="题目主题")
    question = Column(String(500), nullable=False, comment="题目内容")
    user_answer = Column(Text, nullable=True, comment="用户答案")
    correct_answer = Column(Text, nullable=True, comment="正确答案")
    is_correct = Column(Integer, nullable=True, comment="是否正确 0/1")
    heuristic_question = Column(String(500), nullable=True, comment="启发式追问")
    created_at = Column(DateTime, default=_utcnow)

    def __repr__(self):
        return f"<FeedbackRecord(topic={self.topic}, is_correct={self.is_correct})>"
