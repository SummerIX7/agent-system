from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, validate_session_ownership
from app.core.rate_limit import RateLimit
from app.core.store import (
    get_session,
    save_practice_state,
    get_practice_state,
    save_cached_questions,
    get_cached_questions,
    clear_cached_questions,
    save_tiered_questions_for_stage,
    get_tier_questions_for_stage,
    get_tiered_questions_for_stage,
    save_comprehensive_questions,
    get_comprehensive_questions,
    append_practice_result,
    get_practice_results,
)
from app.core.question_persistence import (
    save_question_set_to_db,
    load_question_set_from_db,
    save_practice_state_to_db,
    load_practice_state_from_db,
    clear_persisted_practice_cache,
)
from app.core.domains import get_domain_from_input, get_default_domain
from app.models.database import get_db
from app.models.learner import Learner
from app.models.agent_state import PracticeResult
from app.models.schemas import QuestionSet
from app.models.user import User
from app.agents.question_generator import QuestionGeneratorAgent

router = APIRouter(prefix="/api/questions", tags=["试题生成"])

question_agent = QuestionGeneratorAgent()


LEVEL_LABELS = {
    "node": "节点练习",
    "basic": "节点练习",
    "advanced": "节点练习",
    "comprehensive": "综合练习",
}

COMPREHENSIVE_FORMAT_VERSION = QuestionGeneratorAgent.COMPREHENSIVE_FORMAT_VERSION


def _normalize_level(level: str) -> str:
    """旧 URL 的 basic/advanced 统一落到新的节点练习。"""
    if level in {"basic", "advanced"}:
        return "node"
    return level


def _extract_learning_path(session_data: dict) -> dict:
    for res in session_data.get("resources", []):
        if res.get("type") == "learning_path":
            return res.get("content", {}) or {}
    return session_data.get("learning_path", {}) or {}


def _all_nodes_completed(learning_path: dict) -> bool:
    stages = learning_path.get("path", [])
    return bool(stages) and all(s.get("completed") or s.get("advanced_test_passed") for s in stages)


def _is_current_comprehensive(question_set: dict | None) -> bool:
    """旧版独立场景题自动失效，确保页面只读取单场景 5 题结构。"""
    if not isinstance(question_set, dict):
        return False
    questions = question_set.get("questions")
    scenario = question_set.get("scenario")
    return (
        question_set.get("format_version") == COMPREHENSIVE_FORMAT_VERSION
        and isinstance(scenario, dict)
        and bool(scenario.get("title"))
        and isinstance(questions, list)
        and len(questions) == 5
    )


def _stage_node_context(session_data: dict, stage: int) -> tuple[str, list[str], str]:
    learning_path = _extract_learning_path(session_data)
    path_stages = learning_path.get("path", [])
    stage_data = next((s for s in path_stages if s.get("stage") == stage), None)
    profile = session_data.get("profile", {})
    if not stage_data:
        fallback = profile.get("goals", [""])[0] if profile.get("goals") else "基础知识"
        return fallback, [], profile.get("recommended_difficulty", "beginner")

    node_title = stage_data.get("title", "基础知识")
    node_topics = [str(t) for t in stage_data.get("topics", []) if t]
    node_difficulty = stage_data.get("difficulty", "beginner")
    return node_title, node_topics, node_difficulty


def _collect_path_topics(learning_path: dict) -> list[str]:
    topics: list[str] = []
    for stage in learning_path.get("path", []):
        if stage.get("title"):
            topics.append(stage["title"])
        topics.extend(stage.get("topics", []) or [])
    return list(dict.fromkeys([t for t in topics if t]))


def _collect_avoid_questions(session_id: str, stage: int | None = None) -> list[str]:
    session = get_session(session_id)
    questions: list[str] = []

    tq_map = session.get("tiered_questions_map", {}) or {}
    if isinstance(tq_map, dict):
        stage_values = [tq_map.get(str(stage))] if stage else tq_map.values()
        for tiered in stage_values:
            if not isinstance(tiered, dict):
                continue
            for qset in tiered.values():
                for q in (qset or {}).get("questions", []) or []:
                    if q.get("question"):
                        questions.append(q["question"])

    final_set = get_comprehensive_questions(session_id)
    if final_set:
        for q in final_set.get("questions", []) or []:
            if q.get("question"):
                questions.append(q["question"])

    for item in get_practice_results(session_id):
        for q in item.get("questions", []) or []:
            if q.get("question"):
                questions.append(q["question"])

    return list(dict.fromkeys(questions))


def _build_question_profile(profile: dict, learner: Learner | None, domain_code: str) -> dict:
    return {
        "domain": domain_code,
        "education_background": learner.education_background if learner else "",
        "major": learner.major if learner else "",
        "goals": profile.get("goals", []),
        "knowledge_points": profile.get("knowledge_points", []),
        "blind_spots": profile.get("blind_spots", []),
    }


def _session_learner_id(session_data: dict) -> int | None:
    try:
        learner_id = session_data.get("learner_id")
        if learner_id and learner_id != "unknown":
            return int(learner_id)
    except (TypeError, ValueError):
        return None
    return None


def _state_matches(state: dict, level: str | None, stage: int | None) -> bool:
    if not state:
        return False
    if level and state.get("level") != level:
        return False
    if stage is not None and state.get("stage") != stage:
        return False
    return True


async def _generate_stage_tiered_questions(
    session_id: str,
    stage: int,
    session_data: dict,
    db: AsyncSession,
    learner_id: int | None,
) -> dict:
    """按需生成某个节点练习，并同时写入 session 与 DB。"""
    profile = session_data.get("profile", {})
    node_title, node_topics, node_difficulty = _stage_node_context(session_data, stage)

    domain = get_domain_from_input({
        "domain": profile.get("domain", ""),
        "goals": profile.get("goals", []),
    })
    learner = None
    if learner_id:
        learner = (await db.execute(select(Learner).where(Learner.id == learner_id))).scalar_one_or_none()
    profile_dict = _build_question_profile(profile, learner, domain.code)

    topic_text = f"{node_title}（{'、'.join(node_topics)}）" if node_topics else node_title
    topic = f"{domain.name} - {topic_text}"

    tiered = {}
    try:
        node_result = await question_agent.generate_node_practice_questions(
            topic=topic,
            difficulty=node_difficulty,
            profile=profile_dict,
            count=9,
            avoid_questions=_collect_avoid_questions(session_id, stage),
            node_title=node_title,
            node_topics=node_topics,
        )
        tiered["node"] = {
            "level": "node", "label": "节点练习", "stage": stage,
            "topic": node_result.get("topic", topic),
            "difficulty": node_result.get("difficulty", node_difficulty),
            "questions": node_result.get("questions", []),
        }
    except Exception as e:
        print(f"[警告] 节点{stage}练习题按需生成失败: {e}")
        tiered["node"] = {"level": "node", "label": "节点练习", "stage": stage, "questions": [], "topic": topic, "difficulty": node_difficulty}

    save_tiered_questions_for_stage(session_id, stage, tiered)
    if learner_id:
        for save_level, qset in tiered.items():
            if qset and qset.get("questions"):
                await save_question_set_to_db(db, learner_id, session_id, save_level, stage, qset)
    return tiered


@router.get("/{session_id}", response_model=QuestionSet)
async def get_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    regenerate: bool = False,
    _validated: str = Depends(validate_session_ownership),
):
    """根据学习者画像动态生成试题（需登录）。默认优先返回缓存，传 regenerate=true 重新生成。"""
    # ── 0. 先查缓存（非主动重新生成时） ──
    if not regenerate:
        cached = get_cached_questions(session_id)
        if cached and cached.get("questions"):
            print(f"[试题] 命中缓存，共 {len(cached['questions'])} 题")
            return QuestionSet(
                topic=cached.get("topic", ""),
                difficulty=cached.get("difficulty", "beginner"),
                questions=cached.get("questions", []),
            )

    # ── 1. 从数据库获取 Learner 记录 ──
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    # 2. 从内存 store 获取 session 数据
    session_data = get_session(session_id)
    profile = session_data.get("profile", {})

    # 3. 推断领域配置（支持多领域，不再硬编码 CNC）
    goals = profile.get("goals", [])
    if not goals and learner and learner.goals:
        goals = learner.goals

    # 构建输入数据用于推断领域
    input_data = {
        "domain": profile.get("domain", ""),
        "goals": goals,
    }
    domain = get_domain_from_input(input_data)

    # 构建 topic（基于领域和目标）
    raw_goal = goals[0] if goals else ""
    topic = f"{domain.name} - {raw_goal}" if raw_goal else f"{domain.name}基础"

    difficulty = profile.get("recommended_difficulty", "beginner")
    if difficulty == "beginner" and learner:
        assessment = learner.self_assessment or {}
        if assessment:
            levels = list(assessment.values())
            if any("advanced" in str(v).lower() or "高级" in str(v) for v in levels):
                difficulty = "advanced"
            elif any("intermediate" in str(v).lower() or "中级" in str(v) for v in levels):
                difficulty = "intermediate"

    # 4. 构建 profile dict 供 Agent 使用
    profile_dict = {
        "domain": domain.code,
        "education_background": learner.education_background if learner else "",
        "major": learner.major if learner else "",
        "goals": goals,
        "knowledge_points": profile.get("knowledge_points", []),
        "blind_spots": profile.get("blind_spots", []),
    }

    # 5. 调用试题生成 Agent
    try:
        result_dict = await question_agent.generate_questions(
            topic=topic,
            difficulty=difficulty,
            profile=profile_dict,
            count=6,
            avoid_questions=_collect_avoid_questions(session_id),
        )
    except Exception as e:
        print(f"[警告] 试题生成失败: {e}")
        result_dict = {"topic": topic, "difficulty": difficulty, "domain": domain.code, "questions": []}

    # ── 6. 写入缓存 ──
    cache_data = {
        "topic": result_dict.get("topic", topic),
        "difficulty": result_dict.get("difficulty", difficulty),
        "questions": result_dict.get("questions", []),
    }
    save_cached_questions(session_id, cache_data)
    # 新试题生成后清除旧进度
    save_practice_state(session_id, {})
    print(f"[试题] 生成并缓存完成，共 {len(cache_data['questions'])} 题")

    return QuestionSet(
        topic=cache_data["topic"],
        difficulty=cache_data["difficulty"],
        questions=cache_data["questions"],
    )


# ── 答题进度持久化 ──

class PracticeStateRequest(BaseModel):
    current_index: int = 0
    questions: list = []
    level: str | None = None
    stage: int | None = None


@router.post("/practice/state/{session_id}")
async def save_state(
    session_id: str,
    state: PracticeStateRequest,
    db: AsyncSession = Depends(get_db),
    _validated: str = Depends(validate_session_ownership),
):
    """保存答题进度到 session，并按账号持久化到数据库。"""
    state_data = state.model_dump()
    if state_data.get("level"):
        state_data["level"] = _normalize_level(state_data["level"])
    save_practice_state(session_id, state_data)
    from app.core.store import resolve_learner_context
    session_data = await resolve_learner_context(session_id, db)
    learner_id = _session_learner_id(session_data)
    if learner_id:
        await save_practice_state_to_db(db, learner_id, session_id, state_data)
    return {"ok": True}


@router.get("/practice/state/{session_id}")
async def get_state(
    session_id: str,
    level: str | None = None,
    stage: int | None = None,
    db: AsyncSession = Depends(get_db),
    _validated: str = Depends(validate_session_ownership),
):
    """恢复答题进度。优先 session，缺失时从数据库按账号回填。"""
    if level:
        level = _normalize_level(level)
    state = get_practice_state(session_id)
    if _state_matches(state, level, stage):
        return state

    from app.core.store import resolve_learner_context
    session_data = await resolve_learner_context(session_id, db)
    learner_id = _session_learner_id(session_data)
    if learner_id:
        loaded = await load_practice_state_from_db(db, learner_id, level, stage)
        if loaded:
            save_practice_state(session_id, loaded)
            return loaded
    return state if state and not level else {}


@router.post("/practice/regenerate/{session_id}")
async def regenerate_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _validated: str = Depends(validate_session_ownership),
    _rl: None = Depends(RateLimit("questions:regenerate", max_requests=5, window=60)),
):
    """清除缓存并重新生成试题"""
    clear_cached_questions(session_id)
    save_practice_state(session_id, {})
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    learner = (await db.execute(stmt)).scalar_one_or_none()
    if learner:
        await clear_persisted_practice_cache(db, learner.id)
    # 调用 get_questions 重新生成
    return await get_questions(session_id, db, current_user, regenerate=True)


# ═══════════════════════════════════════════
# 节点练习 API（每节点 4 选择 + 3 判断 + 2 简答）
# ═══════════════════════════════════════════

@router.post("/generate/{session_id}")
async def generate_tiered_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    stage: int = 1,
    _validated: str = Depends(validate_session_ownership),
):
    """
    为指定学习节点生成一套节点练习并按 stage 缓存。

    默认 stage=1（Agent 协同阶段）。节点推进时由 advance API 内部调用。
    """
    session_data = get_session(session_id)
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    tiered = await _generate_stage_tiered_questions(
        session_id=session_id,
        stage=stage,
        session_data=session_data,
        db=db,
        learner_id=learner.id if learner else _session_learner_id(session_data),
    )
    save_practice_state(session_id, {})

    node_title, _, _ = _stage_node_context(session_data, stage)
    node_set = tiered.get("node", {})
    question_count = len(node_set.get("questions", []))
    print(f"[节点练习] 节点{stage}: {question_count}题")

    return {
        "stage": stage,
        "node_topic": node_title,
        "node": {
            "level": "node",
            "label": "节点练习",
            "difficulty": node_set.get("difficulty", ""),
            "question_count": question_count,
        },
    }


@router.get("/set/{session_id}/{level}")
async def get_tiered_question_set(
    session_id: str, level: str, stage: int = 1,
    db: AsyncSession = Depends(get_db),
    _validated: str = Depends(validate_session_ownership),
):
    """
    获取指定节点练习或综合练习的缓存试题。

    level: "node" | "comprehensive"；历史 basic/advanced 会自动兼容为 node。
    stage: 学习路径节点编号（默认 1）
    没有缓存时返回空列表。
    """
    from app.core.store import resolve_learner_context
    level = _normalize_level(level)
    session_data = await resolve_learner_context(session_id, db)
    persisted_learner_id = _session_learner_id(session_data)

    if level not in LEVEL_LABELS:
        return {"error": "level 必须为 node 或 comprehensive", "questions": []}

    if level == "comprehensive":
        learning_path = _extract_learning_path(session_data)

        cached = get_comprehensive_questions(session_id)
        if _is_current_comprehensive(cached):
            cached["label"] = LEVEL_LABELS[level]
            cached["stage"] = None
            return cached

        if persisted_learner_id:
            persisted = await load_question_set_from_db(db, persisted_learner_id, level, None)
            if _is_current_comprehensive(persisted):
                persisted["label"] = LEVEL_LABELS[level]
                persisted["stage"] = None
                save_comprehensive_questions(session_id, persisted)
                return persisted

        learner = None
        learner_id = session_data.get("learner_id")
        if learner_id and learner_id != "unknown":
            try:
                stmt = select(Learner).where(Learner.id == int(learner_id))
                result = await db.execute(stmt)
                learner = result.scalar_one_or_none()
            except (ValueError, TypeError):
                learner = None

        profile = session_data.get("profile", {})
        domain = get_domain_from_input({
            "domain": profile.get("domain", ""),
            "goals": profile.get("goals", []),
        })
        profile_dict = _build_question_profile(profile, learner, domain.code)
        topics = _collect_path_topics(learning_path)
        if not topics:
            topics = profile.get("knowledge_points", []) or profile.get("goals", []) or ["CNC 综合实践"]
        stage_difficulties = [s.get("difficulty") for s in learning_path.get("path", []) if s.get("difficulty")]
        difficulty = profile.get("recommended_difficulty") or (stage_difficulties[-1] if stage_difficulties else "intermediate")
        result = await question_agent.generate_comprehensive_questions(
            topics=topics,
            difficulty=difficulty,
            profile=profile_dict,
            count=5,
            avoid_questions=_collect_avoid_questions(session_id),
        )
        question_set = {
            "format_version": result.get("format_version", COMPREHENSIVE_FORMAT_VERSION),
            "level": "comprehensive",
            "label": LEVEL_LABELS[level],
            "topic": result.get("topic", "最终综合练习：真实业务场景"),
            "difficulty": result.get("difficulty", difficulty),
            "stage": None,
            "scenario": result.get("scenario", {}),
            "questions": result.get("questions", []),
        }
        save_comprehensive_questions(session_id, question_set)
        save_practice_state(session_id, {})
        if persisted_learner_id:
            await save_question_set_to_db(db, persisted_learner_id, session_id, level, None, question_set)
        return question_set

    cached = get_tier_questions_for_stage(session_id, stage, level)
    if cached and cached.get("questions"):
        cached["label"] = LEVEL_LABELS[level]
        return cached

    if persisted_learner_id:
        persisted = await load_question_set_from_db(db, persisted_learner_id, level, stage)
        if persisted and persisted.get("questions"):
            persisted["label"] = LEVEL_LABELS[level]
            persisted["stage"] = stage
            return persisted

        # 兼容历史数据：以前题目只存在内存中，服务重启会丢失。
        # 如果学习路径还在 DB 中，则按当前 stage 重新生成并立即落库，之后刷新不再丢。
        tiered = await _generate_stage_tiered_questions(
            session_id=session_id,
            stage=stage,
            session_data=session_data,
            db=db,
            learner_id=persisted_learner_id,
        )
        generated = tiered.get(level)
        if generated and generated.get("questions"):
            generated["label"] = LEVEL_LABELS[level]
            return generated

    return {"level": level, "label": LEVEL_LABELS[level],
            "topic": "", "difficulty": "", "stage": stage, "questions": []}


class PracticeResultRequest(BaseModel):
    level: str
    stage: int | None = None
    score: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    question_count: int = 0
    questions: list = []


@router.post("/practice/result/{session_id}")
async def save_practice_result(
    session_id: str,
    result: PracticeResultRequest,
    db: AsyncSession = Depends(get_db),
    _validated: str = Depends(validate_session_ownership),
):
    """保存一轮练习结果。练习结果只用于报告和知识图谱掌握度，不推进学习节点。"""
    from app.core.store import resolve_learner_context
    session_data = await resolve_learner_context(session_id, db)

    payload = result.model_dump()
    payload["level"] = _normalize_level(result.level)
    payload["label"] = LEVEL_LABELS.get(payload["level"], payload["level"])
    # 双写：Redis（作缓存）+ DB（持久化，"接着学"的可靠存储）
    all_results = append_practice_result(session_id, payload)

    # 写入 DB
    learner_id = session_data.get("learner_id")
    if learner_id and learner_id != "unknown":
        try:
            db.add(PracticeResult(
                learner_id=int(learner_id),
                session_id=session_id,
                level=payload.get("level"),
                stage=payload.get("stage"),
                score=payload.get("score", 0),
                correct_count=payload.get("correct_count", 0),
                wrong_count=payload.get("wrong_count", 0),
                question_count=payload.get("question_count", 0),
                questions=payload.get("questions"),
                label=payload.get("label"),
            ))
            await db.flush()
        except Exception as e:
            print(f"[警告] 练习结果写入DB失败: {e}")

    try:
        from app.api.knowledge_graph import mark_learning_event_by_learner_id

        learner_id = session_data.get("learner_id")
        learning_path = _extract_learning_path(session_data)
        knowledge_items: list[str] = []
        result_level = payload["level"]
        if result_level == "comprehensive":
            knowledge_items = _collect_path_topics(learning_path)
        elif result.stage:
            stage_data = next((s for s in learning_path.get("path", []) if s.get("stage") == result.stage), {})
            knowledge_items = [stage_data.get("title", ""), *stage_data.get("topics", [])]
        if learner_id and learner_id != "unknown" and knowledge_items:
            await mark_learning_event_by_learner_id(
                db,
                learner_id,
                [item for item in knowledge_items if item],
                result.score,
                f"{result_level}_practice",
            )
    except Exception as e:
        print(f"[警告] 练习结果更新知识图谱失败: {e}")

    return {"ok": True, "total": len(all_results)}


@router.get("/practice/results/{session_id}")
async def list_practice_results(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _validated: str = Depends(validate_session_ownership),
):
    """获取练习结果列表，供分析报告展示。DB 优先，Redis 降级。"""
    # DB 优先（持久化可信源）
    stmt = (
        select(PracticeResult)
        .where(PracticeResult.session_id == session_id)
        .order_by(PracticeResult.created_at)
    )
    result = await db.execute(stmt)
    db_results = result.scalars().all()
    if db_results:
        return {"results": [
            {
                "level": r.level,
                "stage": r.stage,
                "score": r.score,
                "correct_count": r.correct_count,
                "wrong_count": r.wrong_count,
                "question_count": r.question_count,
                "questions": r.questions or [],
                "label": r.label,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in db_results
        ]}

    # 降级 Redis
    return {"results": get_practice_results(session_id)}
