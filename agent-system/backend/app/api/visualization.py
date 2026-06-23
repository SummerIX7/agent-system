from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.core.store import get_session

router = APIRouter(prefix="/api", tags=["可视化数据"])


class KnowledgePoint(BaseModel):
    name: str
    score: float
    level: str


class BlindSpot(BaseModel):
    name: str
    severity: float


class VisualizationData(BaseModel):
    knowledge_points: List[KnowledgePoint]
    blind_spots: List[BlindSpot]
    learning_path: List[dict]
    match_curve: Optional[dict] = None
    agent_logs: List[dict] = []


@router.get("/visualization/{session_id}", response_model=VisualizationData)
async def get_visualization(session_id: str):
    """获取可视化数据（雷达图、盲区、匹配曲线）"""
    session = get_session(session_id)
    profile = session.get("profile", {})

    # 从画像中提取知识点
    knowledge_points = [
        KnowledgePoint(
            name=kp.get("name", ""),
            score=kp.get("score", 0),
            level=kp.get("level", "beginner"),
        )
        for kp in profile.get("knowledge_points", [])
    ]

    # 从画像中提取盲区
    blind_spots = [
        BlindSpot(name=bs, severity=0.7)
        for bs in profile.get("blind_spots", [])
    ]

    # 生成学习路径（基于知识点掌握度）
    learning_path = []
    for kp in profile.get("knowledge_points", []):
        learning_path.append({
            "title": kp.get("name", ""),
            "completed": kp.get("score", 0) >= 60,
            "score": kp.get("score", 0),
        })

    # 匹配曲线数据
    match_curve = None
    if knowledge_points:
        match_curve = {
            "learner_level": profile.get("recommended_difficulty", "beginner"),
            "resources": [
                {"name": kp.name, "difficulty": kp.score / 20, "match": min(1.0, kp.score / 80)}
                for kp in knowledge_points
            ],
        }

    # Agent 日志
    agent_logs = session.get("agent_logs", [])

    return VisualizationData(
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        learning_path=learning_path,
        match_curve=match_curve,
        agent_logs=agent_logs,
    )


@router.get("/history/{learner_id}")
async def get_history(learner_id: str):
    """获取学习历史记录"""
    from app.core.store import _sessions

    history = []
    for sid, session in _sessions.items():
        if session.get("learner_id") == learner_id or session.get("profile", {}).get("id") == learner_id:
            # 画像记录
            if session.get("profile"):
                history.append({
                    "title": "完成学情诊断",
                    "date": session.get("created_at", ""),
                    "description": f"识别了 {len(session['profile'].get('knowledge_points', []))} 个知识点",
                    "tags": ["画像构建", "学情诊断"],
                })

            # 资源生成记录
            for res in session.get("resources", []):
                history.append({
                    "title": f"生成{res.get('type', '')}",
                    "date": res.get("created_at", ""),
                    "description": f"主题: {res.get('topic', '')}",
                    "tags": ["资源生成", res.get("type", "")],
                })

            # 反馈记录
            for fb in session.get("feedback", []):
                history.append({
                    "title": f"答题 {'✓' if fb.get('is_correct') else '✗'}",
                    "date": fb.get("created_at", ""),
                    "description": fb.get("question", ""),
                    "tags": ["反馈", "正确" if fb.get("is_correct") else "错误"],
                })

    return history
