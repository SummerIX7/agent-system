"""
学习路径节点管理 API
支持学习路径查看、当前节点获取、节点推进等功能
"""
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.store import get_session, update_session
from app.core.domains import get_domain_from_input, build_domain_prompt
from app.models.database import get_db
from app.models.learner import Learner
from app.models.resource import Resource
from app.models.user import User
from app.agents.diagnosis import DiagnosisAgent
try:
    from app.graph.workflow import _broadcast
except ImportError:
    def _broadcast(session_id: str, agent: str, status: str, message: str, progress: float = 0):
        pass

router = APIRouter(prefix="/api/learning-path", tags=["学习路径管理"])

diagnosis_agent = DiagnosisAgent()

# 考核通过阈值
PASS_THRESHOLD = 0.7  # 70%


class AdvanceRequest(BaseModel):
    """节点推进请求"""
    basic_score: float = 0.0       # 基础考核正确率
    advanced_score: float = 0.0    # 提升考核正确率
    test_feedback: list = []       # 答题反馈记录


class NodeInfo(BaseModel):
    """学习路径节点信息"""
    stage: int
    title: str
    topics: list = []
    estimated_hours: float = 0
    difficulty: str = "beginner"
    prerequisites: list = []
    resources_type: list = []
    completed: bool = False
    basic_test_passed: bool = False
    advanced_test_passed: bool = False
    has_resources: bool = False


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    nodes: list = []
    total_estimated_hours: float = 0
    current_stage: int = 1
    recommended_order: str = ""
    all_completed: bool = False


def _build_node_info(stage_data: dict) -> NodeInfo:
    """
    从 learning_path 的节点数据构建 NodeInfo。
    节点状态字段（completed/basic_test_passed等）已内嵌在 learning_path JSON 中。
    """
    return NodeInfo(
        stage=stage_data.get("stage", 0),
        title=stage_data.get("title", ""),
        topics=stage_data.get("topics", []),
        estimated_hours=stage_data.get("estimated_hours", 0),
        difficulty=stage_data.get("difficulty", "beginner"),
        prerequisites=stage_data.get("prerequisites", []),
        resources_type=stage_data.get("resources_type", []),
        completed=stage_data.get("completed", False),
        basic_test_passed=stage_data.get("basic_test_passed", False),
        advanced_test_passed=stage_data.get("advanced_test_passed", False),
        has_resources=stage_data.get("has_resources", False),
    )


def _update_node_state(learning_path: dict, stage: int, updates: dict) -> dict:
    """更新 learning_path 中指定节点的状态字段，返回修改后的 learning_path"""
    for s in learning_path.get("path", []):
        if s.get("stage") == stage:
            s.update(updates)
            break
    return learning_path


def _persist_learning_path(session_id: str, learning_path: dict) -> None:
    """持久化 learning_path 到 session store"""
    # 更新 store 中已有的 learning_path 资源
    session = get_session(session_id)
    resources = session.get("resources", [])
    found = False
    for i, res in enumerate(resources):
        if res.get("type") == "learning_path":
            resources[i] = {**res, "content": learning_path}
            found = True
            break
    if not found:
        resources.append({"type": "learning_path", "content": learning_path, "topic": "", "difficulty": "beginner"})
    update_session(session_id, {"resources": resources})


# ═══════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════

async def _get_learning_path_from_any_source(session_id: str, db: AsyncSession = None) -> tuple[dict, int]:
    """
    从 session store 获取学习路径，无数据时从 DB 降级读取。
    返回 (learning_path_dict, current_stage_int)。
    """
    session_data = get_session(session_id)

    # 从 resources 中提取学习路径
    learning_path = {}
    for res in session_data.get("resources", []):
        if res.get("type") == "learning_path":
            learning_path = res.get("content", {})
            break
    if not learning_path:
        learning_path = session_data.get("learning_path", {})

    current_stage = int(session_data.get("current_stage", learning_path.get("current_stage", 1)))

    # 如果 session store 没有路径数据，从 DB 降级读取
    if not learning_path.get("path") and db is not None:
        learner_id = session_data.get("learner_id", "")
        if learner_id and learner_id != "unknown":
            stmt = select(Learner).where(Learner.id == learner_id)
            r = await db.execute(stmt)
            learner = r.scalar_one_or_none()
            if learner and learner.learning_path:
                learning_path = learner.learning_path
                current_stage = int(learning_path.get("current_stage", 1))
                # 回写到 session store
                _persist_learning_path(session_id, learning_path)
                update_session(session_id, {"current_stage": current_stage})

    return learning_path, current_stage


@router.get("/{session_id}", response_model=LearningPathResponse)
async def get_learning_path(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取完整学习路径及各节点状态"""
    learning_path, current_stage = await _get_learning_path_from_any_source(session_id, db)
    path_stages = learning_path.get("path", [])

    nodes = [_build_node_info(s).model_dump() for s in path_stages]

    all_completed = all(
        s.get("advanced_test_passed") or s.get("completed")
        for s in path_stages
    ) if path_stages else False

    return LearningPathResponse(
        nodes=nodes,
        total_estimated_hours=learning_path.get("total_estimated_hours", 0),
        current_stage=current_stage,
        recommended_order=learning_path.get("recommended_order", ""),
        all_completed=all_completed,
    )


@router.get("/{session_id}/current-node")
async def get_current_node(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取当前应学习的节点信息"""
    learning_path, current_stage = await _get_learning_path_from_any_source(session_id, db)
    path_stages = learning_path.get("path", [])

    current_stage_data = next((s for s in path_stages if s.get("stage") == current_stage), None)
    if not current_stage_data:
        return {"current_node": None, "message": "无可用节点"}

    return {
        "current_node": _build_node_info(current_stage_data).model_dump(),
        "total_nodes": len(path_stages),
        "all_completed": all(
            s.get("advanced_test_passed") or s.get("completed") for s in path_stages
        ) if path_stages else False,
    }


@router.post("/{session_id}/advance")
async def advance_node(
    session_id: str,
    req: AdvanceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    节点推进：评估考核结果，决定是否推进到下一节点

    规则：
    - 提升考核正确率 ≥ 70% → 推进到下一节点 + 更新学习者画像
    - 提升考核正确率 < 70% → 标记当前节点"需巩固"，不推进
    """
    session_data = get_session(session_id)

    # 获取当前学习路径
    learning_path = {}
    for res in session_data.get("resources", []):
        if res.get("type") == "learning_path":
            learning_path = res.get("content", {})
            break
    if not learning_path:
        learning_path = session_data.get("learning_path", {})

    current_stage = session_data.get("current_stage", learning_path.get("current_stage", 1))
    path_stages = learning_path.get("path", [])
    total_stages = len(path_stages)

    # 判断是否可推进
    can_advance = req.advanced_score >= PASS_THRESHOLD
    result = {
        "advanced_passed": can_advance,
        "current_stage": current_stage,
        "total_stages": total_stages,
        "message": "",
    }

    # 更新当前节点状态（直接修改 learning_path 内嵌字段）
    learning_path = _update_node_state(learning_path, current_stage, {
        "basic_score": req.basic_score,
        "basic_test_passed": req.basic_score >= PASS_THRESHOLD,
        "advanced_score": req.advanced_score,
        "advanced_test_passed": can_advance,
        "completed": True,
    })

    if can_advance:
        new_stage = current_stage + 1
        learning_path["current_stage"] = new_stage

        # 持久化到 session store
        _persist_learning_path(session_id, learning_path)
        update_session(session_id, {"current_stage": new_stage})

        # 持久化到数据库
        learner_id = session_data.get("learner_id", "")
        if learner_id and learner_id != "unknown":
            await _persist_learning_path_to_db(db, learner_id, learning_path)
            try:
                await _update_learner_profile(
                    db, learner_id, session_data.get("profile", {}),
                    req.test_feedback, current_stage, new_stage,
                )
            except Exception as e:
                print(f"[警告] 更新学习者画像失败: {e}")

        # ── 为新节点生成资源 + 试题 ──
        if new_stage <= total_stages:
            profile = session_data.get("profile", {})
            from app.graph.workflow import generate_resources_for_stage, _generate_and_cache_questions
            _broadcast(session_id, "知识生成 Agent", "running", f"正在为节点 {new_stage} 生成资源...", 90)
            try:
                new_resources = await generate_resources_for_stage(
                    session_id, new_stage, profile, learning_path,
                )
                # 持久化资源到 DB
                if learner_id and learner_id != "unknown":
                    for res in new_resources:
                        db_resource = Resource(
                            learner_id=learner_id,
                            session_id=session_id,
                            resource_type=res["type"],
                            content=res["content"],
                            topic=res.get("topic", ""),
                            difficulty=res.get("difficulty", "beginner"),
                            stage=new_stage,
                        )
                        db.add(db_resource)
                    await db.flush()

                # 更新 node_states: 标记新节点 has_resources
                learning_path = _update_node_state(learning_path, new_stage, {"has_resources": True})
                _persist_learning_path(session_id, learning_path)
                if learner_id and learner_id != "unknown":
                    await _persist_learning_path_to_db(db, learner_id, learning_path)

                # 生成新节点的试题
                topic = res.get("topic", "") if new_resources else ""
                difficulty = next((s.get("difficulty", "beginner") for s in path_stages if s.get("stage") == new_stage), "beginner")
                domain_topic = f"{session_data.get('profile', {}).get('goals', [''])[0]}" if session_data.get('profile', {}).get('goals') else topic
                await _generate_and_cache_questions(session_id, new_stage, domain_topic or topic, difficulty, profile, learning_path)

                print(f"[节点推进] 节点{new_stage} 资源+试题生成完成")
            except Exception as e:
                print(f"[警告] 节点{new_stage} 资源生成失败: {e}")

        if new_stage > total_stages:
            result["message"] = "所有节点已完成，学习流程结束"
            result["new_stage"] = None
            result["all_completed"] = True
        else:
            result["message"] = f"已推进到第 {new_stage} 节点"
            result["new_stage"] = new_stage
            result["all_completed"] = False

        _clear_node_cache(session_id)
    else:
        learning_path = _update_node_state(learning_path, current_stage, {"need_review": True})
        _persist_learning_path(session_id, learning_path)
        result["message"] = "提升考核未通过，建议巩固学习后重新尝试"
        result["new_stage"] = current_stage
        result["all_completed"] = False

    return result


async def _persist_learning_path_to_db(db: AsyncSession, learner_id: str, learning_path: dict):
    """将 learning_path 持久化到 learners 表"""
    stmt = select(Learner).where(Learner.id == learner_id)
    r = await db.execute(stmt)
    learner = r.scalar_one_or_none()
    if learner:
        learner.learning_path = learning_path
        await db.flush()


async def _update_learner_profile(
    db: AsyncSession,
    learner_id: str,
    profile: dict,
    test_feedback: list,
    completed_stage: int,
    next_stage: int,
):
    """根据答题反馈更新学习者画像和学情诊断"""
    # 1. 从数据库获取 Learner 记录
    stmt = select(Learner).where(Learner.id == learner_id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if not learner:
        print(f"[警告] 未找到 learner_id={learner_id} 的记录")
        return

    # 2. 收集答题反馈中的正确/错误知识点
    correct_topics = []
    wrong_topics = []
    for fb in test_feedback:
        topic = fb.get("topic", "")
        if fb.get("is_correct") or fb.get("finalCorrect"):
            correct_topics.append(topic)
        else:
            wrong_topics.append(topic)

    # 3. 更新 knowledge_points 评分
    kps = list(profile.get("knowledge_points", []))
    for kp in kps:
        name = kp.get("name", "")
        if name in correct_topics:
            kp["score"] = min(100, kp.get("score", 0) + 15)
        elif name in wrong_topics:
            kp["score"] = max(0, kp.get("score", 0) - 5)

    # 4. 重新调用学情诊断更新画像
    try:
        input_data = {
            "education_background": learner.education_background or profile.get("education_background", ""),
            "major": learner.major or profile.get("major", ""),
            "work_experience_years": learner.work_experience_years or 0,
            "self_assessment": learner.self_assessment or {},
            "learning_style": profile.get("learning_style", "practice"),
            "goals": learner.goals or profile.get("goals", []),
        }
        diagnosis_result = await diagnosis_agent.run(input_data)
        new_profile = diagnosis_result.get("profile", {})
        new_difficulty = diagnosis_result.get("difficulty", "beginner")
    except Exception as e:
        print(f"[警告] 学情诊断调用失败，使用本地更新: {e}")
        new_profile = profile
        new_difficulty = profile.get("recommended_difficulty", "beginner")

    # 5. 持久化到数据库
    learner.knowledge_points = new_profile.get("knowledge_points", kps)
    learner.blind_spots = new_profile.get("blind_spots", [])
    learner.overall_level = new_profile.get("overall_level", learner.overall_level)
    learner.recommended_difficulty = new_difficulty

    # 更新学习路径的 current_stage
    if learner.learning_path:
        lp = learner.learning_path
        if isinstance(lp, dict):
            lp["current_stage"] = next_stage
            learner.learning_path = lp

    await db.flush()
    print(f"[学情更新] learner_id={learner_id} 画像已更新，推进到第 {next_stage} 节点")


def _clear_node_cache(session_id: str) -> None:
    """清除考核相关缓存，为下一节点准备"""
    from app.core.store import clear_cached_questions, clear_test_results, save_practice_state
    clear_cached_questions(session_id)
    clear_test_results(session_id)
    save_practice_state(session_id, {})
    update_session(session_id, {"tiered_questions": None, "test_results": {}})
