"""
学习路径节点管理 API
支持学习路径查看、当前节点获取、节点推进等功能
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.auth import get_current_user
from app.core.store import get_session, update_session
from app.core.domains import get_domain_from_input, build_domain_prompt
from app.models.database import get_db
from app.models.learner import Learner
from app.models.resource import Resource
from app.models.user import User
from app.api.knowledge_graph import build_kg_progress_for_learner, mark_learning_event_by_learner_id
from app.agents.diagnosis import DiagnosisAgent
from app.utils.db_helpers import retry_on_deadlock
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


class MarkBasicPassedRequest(BaseModel):
    """标记基础考核通过请求"""
    basic_score: float = PASS_THRESHOLD * 100  # 基础考核正确率，默认 70%


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
    # 先确保 session store 有用户上下文
    from app.core.store import resolve_learner_context
    if db is not None:
        await resolve_learner_context(session_id, db)

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

    # DB 降级：直接从 DB 恢复，不依赖 session store 中有 learner_id
    if db is not None and not learning_path.get("path") and session_id.startswith("user-"):
        try:
            user_id = int(session_id.split("-", 1)[1])
            stmt = select(Learner).where(Learner.user_id == user_id)
            r = await db.execute(stmt)
            learner = r.scalar_one_or_none()
            if learner and learner.learning_path and learner.learning_path.get("path"):
                learning_path = learner.learning_path
                current_stage = int(learning_path.get("current_stage", 1))
                _persist_learning_path(session_id, learning_path)
                update_session(session_id, {"current_stage": current_stage, "learner_id": str(learner.id)})
        except (ValueError, IndexError):
            pass

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
    current_node = next((s for s in path_stages if s.get("stage") == current_stage), {})
    current_knowledge_items = [
        item for item in [current_node.get("title", ""), *current_node.get("topics", [])] if item
    ]

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
    })

    if can_advance:
        # 只有提升考核通过后才标记节点完成
        learning_path = _update_node_state(learning_path, current_stage, {"completed": True})
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
            try:
                await mark_learning_event_by_learner_id(
                    db,
                    learner_id,
                    current_knowledge_items,
                    100,
                    "advanced_test",
                )
            except Exception as e:
                print(f"[警告] 知识图谱掌握度更新失败: {e}")

        if new_stage > total_stages:
            result["message"] = "所有节点已完成，学习流程结束"
            result["new_stage"] = None
            result["all_completed"] = True
        else:
            result["message"] = f"已推进到第 {new_stage} 节点"
            result["new_stage"] = new_stage
            result["all_completed"] = False

        _clear_node_cache(session_id)

        # 节点推进成功后初始化知识图谱进度（如果尚未设置）
        try:
            from app.api.knowledge_graph import build_kg_progress_for_learner
            if learner_id and learner_id != "unknown":
                try:
                    lid = int(learner_id)
                    lr_stmt = select(Learner).where(Learner.id == lid)
                    lr_result = await db.execute(lr_stmt)
                    kg_learner = lr_result.scalar_one_or_none()
                    if kg_learner and kg_learner.kg_progress is None:
                        kg_learner.kg_progress = build_kg_progress_for_learner("")
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            print(f"[警告] 知识图谱进度初始化失败: {e}")
    else:
        learning_path = _update_node_state(learning_path, current_stage, {"need_review": True})
        _persist_learning_path(session_id, learning_path)
        result["message"] = "提升考核未通过，建议巩固学习后重新尝试"
        result["new_stage"] = current_stage
        result["all_completed"] = False

    return result


@router.post("/{session_id}/mark-basic-passed")
async def mark_basic_passed(
    session_id: str,
    req: MarkBasicPassedRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    标记当前节点基础考核已通过。
    基础考核通过后、进入提升考核前调用，用于持久化基础考核状态。
    """
    learning_path, current_stage = await _get_learning_path_from_any_source(session_id, db)
    current_node = next((s for s in learning_path.get("path", []) if s.get("stage") == current_stage), {})
    current_knowledge_items = [
        item for item in [current_node.get("title", ""), *current_node.get("topics", [])] if item
    ]

    # 更新当前节点状态
    learning_path = _update_node_state(learning_path, current_stage, {
        "basic_score": req.basic_score,
        "basic_test_passed": True,
    })

    _persist_learning_path(session_id, learning_path)

    # 持久化到数据库
    session_data = get_session(session_id)
    learner_id = session_data.get("learner_id", "")
    if learner_id and learner_id != "unknown":
        await _persist_learning_path_to_db(db, learner_id, learning_path)
        try:
            await mark_learning_event_by_learner_id(
                db,
                learner_id,
                current_knowledge_items,
                max(req.basic_score, 70),
                "basic_test",
            )
        except Exception as e:
            print(f"[警告] 知识图谱基础掌握度更新失败: {e}")

    return {
        "ok": True,
        "stage": current_stage,
        "basic_test_passed": True,
    }


@router.post("/{session_id}/complete-current")
async def complete_current_node(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    学习资源页完成当前节点。
    练习页不再推进节点，节点解锁统一由该接口触发。
    """
    learning_path, current_stage = await _get_learning_path_from_any_source(session_id, db)
    path_stages = learning_path.get("path", [])
    total_stages = len(path_stages)
    if not path_stages:
        return {"ok": False, "message": "暂无学习路径", "new_stage": None, "all_completed": False}

    already_all_completed = all(s.get("completed") or s.get("advanced_test_passed") for s in path_stages)
    if already_all_completed:
        return {"ok": True, "message": "所有节点已完成", "new_stage": None, "all_completed": True}

    current_node = next((s for s in path_stages if s.get("stage") == current_stage), None)
    if not current_node:
        return {"ok": False, "message": "未找到当前节点", "new_stage": None, "all_completed": False}

    current_knowledge_items = [
        item for item in [current_node.get("title", ""), *current_node.get("topics", [])] if item
    ]
    learning_path = _update_node_state(learning_path, current_stage, {
        "completed": True,
        "completed_by": "resource",
        "completed_at": datetime.now().isoformat(),
    })

    new_stage = current_stage + 1
    all_completed = new_stage > total_stages
    learning_path["current_stage"] = new_stage
    _persist_learning_path(session_id, learning_path)
    update_session(session_id, {"current_stage": new_stage})

    session_data = get_session(session_id)
    learner_id = session_data.get("learner_id", "")
    if learner_id and learner_id != "unknown":
        await _persist_learning_path_to_db(db, learner_id, learning_path)
        try:
            await mark_learning_event_by_learner_id(
                db,
                learner_id,
                current_knowledge_items,
                85,
                "resource_complete",
            )
        except Exception as e:
            print(f"[警告] 资源学习完成更新知识图谱失败: {e}")

    try:
        from app.core.store import save_practice_state
        save_practice_state(session_id, {})
    except Exception:
        pass

    return {
        "ok": True,
        "stage": current_stage,
        "new_stage": None if all_completed else new_stage,
        "all_completed": all_completed,
        "message": "所有节点已完成，综合练习已解锁" if all_completed else f"已解锁第 {new_stage} 节点",
    }


@retry_on_deadlock()
async def _persist_learning_path_to_db(db: AsyncSession, learner_id: str | int, learning_path: dict):
    """将 learning_path 持久化到 learners 表（含死锁重试）"""
    try:
        lid = int(learner_id)
    except (ValueError, TypeError):
        return
    stmt = select(Learner).where(Learner.id == lid)
    r = await db.execute(stmt)
    learner = r.scalar_one_or_none()
    if learner:
        learner.learning_path = learning_path
        await db.flush()


@retry_on_deadlock()
async def _persist_learner_path_and_cache(
    db: AsyncSession, learner_id: str, learning_path: dict, report_cache=None
):
    """合并写入 learner 的 learning_path 和 report_cache（单次 flush，防死锁）。

    用于 generate_node_content 端点：将原来两次 UPDATE learners
    （_persist_learning_path_to_db + report_cache flush）合并为一次，
    消除同一事务内多次 flush 同一行的死锁风险。
    """
    stmt = select(Learner).where(Learner.id == learner_id)
    r = await db.execute(stmt)
    learner = r.scalar_one_or_none()
    if learner:
        learner.learning_path = learning_path
        if report_cache is not None:
            learner.report_cache = report_cache
        await db.flush()


class GenerateNodeRequest(BaseModel):
    session_id: str
    stage: int = 1


@router.post("/{session_id}/generate-node-content")
async def generate_node_content(
    session_id: str,
    req: GenerateNodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    为指定节点按需生成资源+试题。
    兼容旧数据或人工补救场景；正常流程已在 Agent 协同阶段一次性生成 5 个节点资源。
    生成完自动调用 LLM，结果持久化到 DB + session store。
    """
    from app.graph.workflow import generate_resources_for_stage, _generate_and_cache_questions
    from app.metrics.report_builder import build_report_cache

    session_data = get_session(session_id)
    learning_path, _ = await _get_learning_path_from_any_source(session_id, db)
    profile = session_data.get("profile", {})
    learner_id = session_data.get("learner_id", "")

    # 生成资源
    _broadcast(session_id, "知识生成 Agent", "running", f"正在生成节点 {req.stage} 资源...", 90)
    new_resources = await generate_resources_for_stage(session_id, req.stage, profile, learning_path)

    if learner_id and learner_id != "unknown":
        for res in new_resources:
            db.add(Resource(
                learner_id=learner_id, session_id=session_id,
                resource_type=res["type"], content=res["content"],
                topic=res.get("topic", ""), difficulty=res.get("difficulty", "beginner"),
                stage=req.stage,
            ))
        await db.flush()

    # 生成试题
    stage_data = next((s for s in learning_path.get("path", []) if s.get("stage") == req.stage), {})
    topic = stage_data.get("topics", [""])[0] if stage_data.get("topics") else ""
    difficulty = stage_data.get("difficulty", "beginner")
    await _generate_and_cache_questions(session_id, req.stage, topic, difficulty, profile, learning_path)

    # 标记 has_resources
    learning_path = _update_node_state(learning_path, req.stage, {"has_resources": True})
    _persist_learning_path(session_id, learning_path)

    # 重新计算报告快照（先计算 cache，再合并写入 DB）
    cache = None
    try:
        stmt_res = select(Resource).where(Resource.session_id == session_id, Resource.stage == req.stage)
        res_result = await db.execute(stmt_res)
        stage_resources = res_result.scalars().all()
        cache = await build_report_cache(
            all_content=[str(r.content) for r in stage_resources if r.content],
            all_difficulties=[r.difficulty for r in stage_resources if r.difficulty],
            topic=topic, profile=profile, learning_path=learning_path,
        )
    except Exception as e:
        print(f"[警告] 报告快照更新失败: {e}")

    # 合并写入 DB：learning_path + report_cache 一次 UPDATE，避免多次 flush 同一行引发死锁
    if learner_id and learner_id != "unknown":
        await _persist_learner_path_and_cache(db, learner_id, learning_path, cache)

    _broadcast(session_id, "知识生成 Agent", "completed",
               f"节点{req.stage}资源+试题生成完成", 95)

    resource_count = len(new_resources)
    print(f"[按需生成] 节点{req.stage}: {resource_count}种资源")
    return {"ok": True, "stage": req.stage, "resource_count": resource_count}


@retry_on_deadlock()
async def _flush_learner_profile(db: AsyncSession, learner: Learner, next_stage: int):
    """死锁重试：仅执行 db.flush()，learner 属性已在 _update_learner_profile 中更新"""
    await db.flush()


async def _update_learner_profile(
    db: AsyncSession,
    learner_id: str | int,
    profile: dict,
    test_feedback: list,
    completed_stage: int,
    next_stage: int,
):
    """根据答题反馈更新学习者画像和学情诊断"""
    # 1. 从数据库获取 Learner 记录
    try:
        lid = int(learner_id)
    except (ValueError, TypeError):
        print(f"[警告] 无效的 learner_id: {learner_id}")
        return
    stmt = select(Learner).where(Learner.id == lid)
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

    # 5. 持久化到数据库（对象属性已在内存中更新，flush 带死锁重试）
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

    await _flush_learner_profile(db, learner, next_stage)
    print(f"[学情更新] learner_id={learner_id} 画像已更新，推进到第 {next_stage} 节点")


def _clear_node_cache(session_id: str) -> None:
    """清除考核相关缓存，为下一节点准备"""
    from app.core.store import clear_cached_questions, clear_test_results, save_practice_state
    clear_cached_questions(session_id)
    clear_test_results(session_id)
    save_practice_state(session_id, {})
    update_session(session_id, {"tiered_questions": None, "test_results": {}})
