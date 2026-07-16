"""Learner 上下文回填与 agent 日志持久化到 DB。"""

from __future__ import annotations

import json
import logging

from app.core.store.session import _update_field, get_session, update_session

logger = logging.getLogger(__name__)


async def resolve_learner_context(session_id: str, db_session) -> dict:
    """
    确保 session store 中有完整的用户上下文（learner_id + profile）。
    从 session_id（格式 user-{userId}）推导用户，DB 回填 session store。
    返回填充后的 session dict。
    """
    session = get_session(session_id)

    # 已有 learner_id 且 profile 完整 → 热缓存命中
    if session.get("learner_id") and session.get("profile", {}).get("knowledge_points"):
        return session

    learner_id = session.get("learner_id", "")
    learner = None

    # 从 session_id 推导用户
    if not learner_id and session_id.startswith("user-"):
        try:
            from app.models.learner import Learner as LearnerModel
            from sqlalchemy import select as _select
            user_id = int(session_id.split("-", 1)[1])
            stmt = _select(LearnerModel).where(LearnerModel.user_id == user_id)
            r = await db_session.execute(stmt)
            learner = r.scalar_one_or_none()
            if learner:
                learner_id = str(learner.id)
                update_session(session_id, {"learner_id": learner_id})
        except (ValueError, IndexError):
            pass

    # 从 learner_id 查 DB 回填 profile
    if learner_id and learner_id != "unknown" and not session.get("profile", {}).get("knowledge_points"):
        try:
            from app.models.learner import Learner as LearnerModel
            from sqlalchemy import select as _select
            if not learner:
                stmt = _select(LearnerModel).where(LearnerModel.id == int(learner_id))
                r = await db_session.execute(stmt)
                learner = r.scalar_one_or_none()
            if learner:
                profile = {
                    "id": str(learner.id),
                    "education_background": learner.education_background or "",
                    "major": learner.major or "",
                    "work_experience_years": learner.work_experience_years or 0,
                    "self_assessment": learner.self_assessment or {},
                    "learning_style": learner.learning_style or "practice",
                    "goals": learner.goals or [],
                    "knowledge_points": learner.knowledge_points or [],
                    "blind_spots": learner.blind_spots or [],
                    "overall_level": learner.overall_level or "beginner",
                    "recommended_difficulty": learner.recommended_difficulty or "beginner",
                }
                update_session(session_id, {"profile": profile})
                session["profile"] = profile
                # 同时回填 learning_path
                if learner.learning_path:
                    _persist_in_session_resources(session_id, learner.learning_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("[resolve_context] 回填失败: %s", e)

    return get_session(session_id)


def _persist_in_session_resources(session_id: str, learning_path: dict) -> None:
    """将 learning_path 回填到 session store 的 resources 列表中"""
    session = get_session(session_id)
    resources = session.get("resources", [])
    if isinstance(resources, str):
        try:
            resources = json.loads(resources)
        except Exception:
            resources = []
    found = False
    for i, res in enumerate(resources):
        if res.get("type") == "learning_path":
            resources[i] = {**res, "content": learning_path}
            found = True
            break
    if not found:
        resources.append({"type": "learning_path", "content": learning_path, "topic": "", "difficulty": "beginner"})
    update_session(session_id, {"resources": resources})


async def flush_agent_logs_to_db(session_id: str, db_session) -> int:
    """
    将 session store 中缓存的 agent_logs 批量写入数据库。
    工作流完成后调用，确保 Agent 执行记录持久化。
    返回写入条数。
    """
    from app.models.agent_state import AgentLog

    session = get_session(session_id)
    logs = session.get("agent_logs", [])
    if not logs:
        return 0

    count = 0
    for log in logs:
        db_session.add(AgentLog(
            session_id=session_id,
            agent_name=log.get("agent_name", ""),
            status=log.get("status", "completed"),
            message=log.get("message", ""),
            progress=log.get("progress", 0),
        ))
        count += 1

    await db_session.flush()
    return count
