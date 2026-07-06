from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import Resource


QUESTION_TOPIC_PREFIX = "__practice_questions__"
STATE_TOPIC_PREFIX = "__practice_state__"


def _stage_key(stage: int | None) -> str:
    return "final" if stage is None else str(stage)


def question_topic(level: str, stage: int | None) -> str:
    return f"{QUESTION_TOPIC_PREFIX}:{level}:{_stage_key(stage)}"


def practice_state_topic(level: str | None, stage: int | None) -> str:
    return f"{STATE_TOPIC_PREFIX}:{level or 'unknown'}:{_stage_key(stage)}"


async def save_question_set_to_db(
    db: AsyncSession,
    learner_id: int,
    session_id: str,
    level: str,
    stage: int | None,
    question_set: dict[str, Any],
) -> None:
    """将基础/提升/综合练习题持久化到 resources 表的 test 类型行。"""
    topic = question_topic(level, stage)
    stmt = select(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic == topic,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    content = {
        **(question_set or {}),
        "level": level,
        "stage": stage,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    if row:
        row.session_id = session_id
        row.content = content
        row.difficulty = content.get("difficulty") or row.difficulty
        row.review_passed = "passed"
    else:
        db.add(Resource(
            learner_id=learner_id,
            session_id=session_id,
            resource_type="test",
            content=content,
            topic=topic,
            difficulty=content.get("difficulty") or "beginner",
            stage=stage,
            review_passed="passed",
        ))
    await db.flush()


async def load_question_set_from_db(
    db: AsyncSession,
    learner_id: int,
    level: str,
    stage: int | None,
) -> dict[str, Any] | None:
    topic = question_topic(level, stage)
    stmt = select(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic == topic,
    ).order_by(Resource.created_at.desc(), Resource.id.desc())
    row = (await db.execute(stmt)).scalars().first()
    if not row or not isinstance(row.content, dict):
        return None
    return row.content


async def save_practice_state_to_db(
    db: AsyncSession,
    learner_id: int,
    session_id: str,
    state: dict[str, Any],
) -> None:
    """保存未完成答题进度。按账号+level+stage 覆盖，切换页面/重启后可恢复。"""
    level = state.get("level")
    stage = state.get("stage")
    topic = practice_state_topic(level, stage)
    stmt = select(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic == topic,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    content = {**state, "saved_at": datetime.now(timezone.utc).isoformat()}
    if row:
        row.session_id = session_id
        row.content = content
        row.review_passed = "passed"
    else:
        db.add(Resource(
            learner_id=learner_id,
            session_id=session_id,
            resource_type="test",
            content=content,
            topic=topic,
            difficulty="beginner",
            stage=stage if isinstance(stage, int) else None,
            review_passed="passed",
        ))
    await db.flush()


async def load_practice_state_from_db(
    db: AsyncSession,
    learner_id: int,
    level: str | None,
    stage: int | None,
) -> dict[str, Any] | None:
    topic = practice_state_topic(level, stage)
    stmt = select(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic == topic,
    ).order_by(Resource.created_at.desc(), Resource.id.desc())
    row = (await db.execute(stmt)).scalars().first()
    if not row or not isinstance(row.content, dict):
        return None
    return row.content


async def persist_session_question_cache(
    db: AsyncSession,
    learner_id: int,
    session_id: str,
    session_data: dict[str, Any],
) -> int:
    """把当前 session 内的试题缓存批量落库。"""
    count = 0
    tq_map = session_data.get("tiered_questions_map", {}) or {}
    if isinstance(tq_map, dict):
        for stage_key, tiered in tq_map.items():
            try:
                stage = int(stage_key)
            except (TypeError, ValueError):
                continue
            if not isinstance(tiered, dict):
                continue
            for level in ("node", "basic", "advanced"):
                qset = tiered.get(level)
                if qset and qset.get("questions"):
                    await save_question_set_to_db(db, learner_id, session_id, level, stage, qset)
                    count += 1

    final_set = session_data.get("comprehensive_questions")
    if isinstance(final_set, dict) and final_set.get("questions"):
        await save_question_set_to_db(db, learner_id, session_id, "comprehensive", None, final_set)
        count += 1
    return count


async def clear_persisted_practice_cache(db: AsyncSession, learner_id: int) -> None:
    """新一轮 Agent 协同生成开始时，删除旧试题和未完成答题进度。"""
    await db.execute(delete(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic.like(f"{QUESTION_TOPIC_PREFIX}%"),
    ))
    await db.execute(delete(Resource).where(
        Resource.learner_id == learner_id,
        Resource.resource_type == "test",
        Resource.topic.like(f"{STATE_TOPIC_PREFIX}%"),
    ))
    await db.flush()
