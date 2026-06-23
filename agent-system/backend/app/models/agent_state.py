import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, String
from sqlalchemy.dialects.mysql import JSON

from app.models.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    input_data = Column(JSON, nullable=True, comment="输入数据")
    output_data = Column(JSON, nullable=True, comment="输出数据")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AgentLog(agent={self.agent_name}, status={self.status})>"


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False, index=True, comment="会话 ID")
    learner_id = Column(String(36), nullable=False, index=True, comment="学习者 ID")
    topic = Column(String(200), nullable=False, comment="题目主题")
    question = Column(String(500), nullable=False, comment="题目内容")
    user_answer = Column(String(500), nullable=True, comment="用户答案")
    correct_answer = Column(String(500), nullable=True, comment="正确答案")
    is_correct = Column(Float, nullable=True, comment="是否正确 0/1")
    heuristic_question = Column(String(500), nullable=True, comment="启发式追问")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FeedbackRecord(topic={self.topic}, is_correct={self.is_correct})>"
