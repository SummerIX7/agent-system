from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.store import get_session, save_practice_state, get_practice_state, save_cached_questions, get_cached_questions, clear_cached_questions, save_tiered_questions_for_stage, get_tier_questions_for_stage
from app.core.domains import get_domain_from_input, get_default_domain
from app.models.database import get_db
from app.models.learner import Learner
from app.models.schemas import QuestionSet
from app.models.user import User
from app.agents.question_generator import QuestionGeneratorAgent

router = APIRouter(prefix="/api/questions", tags=["试题生成"])

question_agent = QuestionGeneratorAgent()


@router.get("/{session_id}", response_model=QuestionSet)
async def get_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    regenerate: bool = False,
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


@router.post("/practice/state/{session_id}")
async def save_state(session_id: str, state: PracticeStateRequest):
    """保存答题进度到 session"""
    save_practice_state(session_id, state.model_dump())
    return {"ok": True}


@router.get("/practice/state/{session_id}")
async def get_state(session_id: str):
    """恢复答题进度"""
    return get_practice_state(session_id)


@router.post("/practice/regenerate/{session_id}")
async def regenerate_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清除缓存并重新生成试题"""
    clear_cached_questions(session_id)
    save_practice_state(session_id, {})
    # 调用 get_questions 重新生成
    return await get_questions(session_id, db, current_user, regenerate=True)


# ═══════════════════════════════════════════
# 分阶试题 API（基础考核 + 提升考核）
# ═══════════════════════════════════════════

@router.post("/generate/{session_id}")
async def generate_tiered_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    stage: int = 1,
):
    """
    为指定学习节点一次性生成基础+提升两套试题并按 stage 缓存。

    默认 stage=1（Agent 协同阶段）。节点推进时由 advance API 内部调用。
    """
    session_data = get_session(session_id)
    learning_path = {}
    for res in session_data.get("resources", []):
        if res.get("type") == "learning_path":
            learning_path = res.get("content", {})
            break
    if not learning_path:
        learning_path = session_data.get("learning_path", {})

    path_stages = learning_path.get("path", [])
    stage_data = next((s for s in path_stages if s.get("stage") == stage), None)
    if not stage_data:
        # 降级：使用 session profile
        profile = session_data.get("profile", {})
        node_topic = profile.get("goals", [""])[0] if profile.get("goals") else "基础知识"
        node_difficulty = "beginner"
    else:
        node_topics = stage_data.get("topics", [])
        node_topic = node_topics[0] if node_topics else stage_data.get("title", "基础知识")
        node_difficulty = stage_data.get("difficulty", "beginner")

    profile = session_data.get("profile", {})
    from app.core.domains import get_domain_from_input
    domain = get_domain_from_input({
        "domain": profile.get("domain", ""),
        "goals": profile.get("goals", []),
    })
    topic = f"{domain.name} - {node_topic}"

    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()
    profile_dict = {
        "domain": domain.code,
        "education_background": learner.education_background if learner else "",
        "major": learner.major if learner else "",
        "goals": profile.get("goals", []),
        "knowledge_points": profile.get("knowledge_points", []),
        "blind_spots": profile.get("blind_spots", []),
    }

    difficulty_levels = ["beginner", "intermediate", "advanced", "expert"]
    basic_difficulty = node_difficulty
    try:
        advanced_idx = min(difficulty_levels.index(node_difficulty) + 1, len(difficulty_levels) - 1)
    except ValueError:
        advanced_idx = 1
    advanced_difficulty = difficulty_levels[advanced_idx]

    tiered = {}
    try:
        basic_result = await question_agent.generate_questions(topic=topic, difficulty=basic_difficulty, profile=profile_dict, count=6)
        tiered["basic"] = {"level": "basic", "label": "基础考核", "stage": stage, "topic": basic_result.get("topic", topic), "difficulty": basic_result.get("difficulty", basic_difficulty), "questions": basic_result.get("questions", [])}
    except Exception as e:
        print(f"[警告] 节点{stage}基础试题生成失败: {e}")
        tiered["basic"] = {"level": "basic", "stage": stage, "questions": [], "topic": topic, "difficulty": basic_difficulty}

    try:
        advanced_result = await question_agent.generate_questions(topic=topic, difficulty=advanced_difficulty, profile=profile_dict, count=6)
        tiered["advanced"] = {"level": "advanced", "label": "提升考核", "stage": stage, "topic": advanced_result.get("topic", topic), "difficulty": advanced_result.get("difficulty", advanced_difficulty), "questions": advanced_result.get("questions", [])}
    except Exception as e:
        print(f"[警告] 节点{stage}提升试题生成失败: {e}")
        tiered["advanced"] = {"level": "advanced", "stage": stage, "questions": [], "topic": topic, "difficulty": advanced_difficulty}

    # 按 stage 缓存
    save_tiered_questions_for_stage(session_id, stage, tiered)
    save_practice_state(session_id, {})

    bc, ac = len(tiered["basic"]["questions"]), len(tiered["advanced"]["questions"])
    print(f"[分阶试题] 节点{stage}: 基础{bc}题 + 提升{ac}题")

    return {
        "stage": stage,
        "node_topic": node_topic,
        "basic": {"level": "basic", "label": "基础考核", "difficulty": basic_difficulty, "question_count": bc},
        "advanced": {"level": "advanced", "label": "提升考核", "difficulty": advanced_difficulty, "question_count": ac},
    }


@router.get("/set/{session_id}/{level}")
async def get_tiered_question_set(
    session_id: str, level: str, stage: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定等级+节点的缓存试题。

    level: "basic" | "advanced"
    stage: 学习路径节点编号（默认 1）
    没有缓存时返回空列表。
    """
    from app.core.store import resolve_learner_context
    await resolve_learner_context(session_id, db)

    if level not in ("basic", "advanced"):
        return {"error": "level 必须为 basic 或 advanced", "questions": []}

    cached = get_tier_questions_for_stage(session_id, stage, level)
    if cached and cached.get("questions"):
        return cached

    return {"level": level, "label": f"{'基础' if level == 'basic' else '提升'}考核",
            "topic": "", "difficulty": "", "stage": stage, "questions": []}
