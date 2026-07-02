from pydantic import BaseModel
from typing import Any, Dict, List, Optional


# === 知识溯源 ===

class SourceReference(BaseModel):
    source_type: str = "document"  # book / paper / standard / website
    source_name: str = ""
    author: str = ""
    publisher: str = ""
    year: str = ""
    chapter: str = ""
    url: str = ""
    confidence: float = 0.0


# === 学习者画像 ===

class KnowledgePoint(BaseModel):
    name: str
    level: str = "beginner"
    score: float = 0
    confidence: float = 0


class BlindSpot(BaseModel):
    name: str
    severity: float = 0.5


class LearnerProfileInput(BaseModel):
    education_background: str
    major: str
    work_experience_years: float = 0
    self_assessment: Dict[str, str] = {}
    learning_style: str = "practice"
    goals: List[str] = []


class LearnerProfile(BaseModel):
    id: int
    session_id: str = ""
    education_background: str
    major: str
    work_experience_years: float
    self_assessment: Dict[str, str]
    learning_style: str
    goals: List[str]
    knowledge_points: List[KnowledgePoint] = []
    blind_spots: List[str] = []
    overall_level: str = "beginner"
    recommended_difficulty: str = "beginner"
    learning_path: Optional[dict] = None
    machine_approval_status: str = "none"


# === 资源生成 ===

class GenerateRequest(BaseModel):
    session_id: str
    topic: str
    resource_types: List[str] = ["lecture", "guide", "test"]
    profile: Optional[Dict] = None  # 学习者画像（可选，不传则从 store 查找）


class ResourceOutput(BaseModel):
    type: str
    content: str | list | dict
    topic: str = ""
    difficulty: str = "beginner"
    sources: List[dict] = []


# === 审核结果 ===

class ReviewResult(BaseModel):
    passed: bool = False
    score: float = 0.0
    issues: List[str] = []
    suggestions: List[str] = []


# === 反馈 ===

class FeedbackInput(BaseModel):
    session_id: str
    topic: str
    question: str
    user_answer: str
    correct_answer: str
    round: int = 1                    # 当前追问轮次（1=首次答错，2/3=追问轮）
    heuristic_context: str = ""       # 之前的追问内容（用于上下文连贯）


class FeedbackResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    heuristic_question: Optional[str] = None
    topic: str
    correctness: float
    round: int = 1                    # 当前轮次
    reveal_answer: bool = False       # 是否应展示正确答案（达到最大轮次时为 True）


# === 实操题批改 ===

class PracticalFeedbackInput(BaseModel):
    session_id: str
    topic: str
    question: str
    user_answer: str                  # 用户提交的自由文本答案（G 代码、操作步骤等）
    correct_answer: str               # 参考答案
    explanation: str = ""             # 评分标准和要点


class PracticalFeedbackResponse(BaseModel):
    score: int                        # 0-100 分
    is_correct: bool                  # score >= 60 为 True
    feedback: str                     # 详细批改反馈
    key_points: List[str] = []        # 关键要点/扣分项
    reference_answer: str = ""        # 参考答案


# === 可视化 ===

class VisualizationData(BaseModel):
    knowledge_points: List[dict] = []
    blind_spots: List[dict] = []
    learning_path: List[dict] = []
    match_curve: Optional[dict] = None
    agent_logs: List[dict] = []
    metrics: Optional[dict] = None
    learning_path_meta: Optional[dict] = None


# === 学习路径 ===

class PathStage(BaseModel):
    stage: int
    title: str
    topics: List[str] = []
    estimated_hours: float = 0
    difficulty: str = "beginner"
    prerequisites: List[str] = []
    resources_type: List[str] = ["lecture", "guide"]
    completed: bool = False

class LearningPath(BaseModel):
    path: List[PathStage] = []
    total_estimated_hours: float = 0
    current_stage: int = 1


# === 试题 ===

class Question(BaseModel):
    question: str
    question_type: str  # multiple_choice / true_false / practical
    options: List[str] = []
    correct_answer: str = ""
    explanation: str = ""

class QuestionSet(BaseModel):
    topic: str
    difficulty: str = "beginner"
    questions: List[Question] = []


# === 辩论 ===

class DebateRound(BaseModel):
    round: int
    challenger_issues: List[str] = []
    challenger_confidence: float = 0
    defender_responses: List[str] = []
    revised_content: str = ""

class DebateResult(BaseModel):
    content_type: str
    passed: bool = False
    adopted_side: str = ""  # challenger / defender
    reason: str = ""
    final_content: str = ""
    rounds: List[DebateRound] = []
