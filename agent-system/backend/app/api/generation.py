from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import GenerateRequest, ResourceOutput
from app.models.resource import Resource
from app.graph.workflow import run_workflow
from app.core.store import add_resource, get_session

router = APIRouter(prefix="/api", tags=["资源生成"])


@router.post("/generate", response_model=list[ResourceOutput])
async def generate_resources(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """触发资源生成（讲义/指南/试题）— 运行完整 Agent 工作流"""

    # 获取学习者画像：优先用请求传入的，其次从 store 查找
    profile = request.profile or {}
    if not profile:
        session = get_session(request.session_id)
        profile = session.get("profile", {})

    # 构造 learner_input（传给工作流的诊断 Agent）
    learner_input = {
        "education_background": profile.get("education_background", "未知"),
        "major": profile.get("major", "未知"),
        "work_experience_years": profile.get("work_experience_years", 0),
        "self_assessment": profile.get("self_assessment", {}),
        "learning_style": profile.get("learning_style", "practice"),
        "goals": profile.get("goals", []),
    }

    # 查找 learner_id（从 store 或 session）
    learner_id = profile.get("id", "")
    if not learner_id:
        session = get_session(request.session_id)
        learner_id = session.get("learner_id", "")

    try:
        result = await run_workflow(
            learner_input=learner_input,
            topic=request.topic,
            session_id=request.session_id,
            profile=profile,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资源生成失败: {e}")

    # ── 持久化 Agent 日志 ──
    from app.core.store import flush_agent_logs_to_db
    log_count = await flush_agent_logs_to_db(request.session_id, db)
    if log_count:
        print(f"[Agent日志] 已持久化 {log_count} 条到数据库")

    # 允许写入数据库的资源类型（与 Enum 定义一致）
    DB_RESOURCE_TYPES = {"lecture", "guide", "project", "test"}

    resources = []
    review_results = result.get("review_results", {})

    for res in result.get("final_resources", []):
        res_type = res.get("type", "")
        res_stage = res.get("stage", 1)  # 工作流输出的资源默认属于节点 1

        resource_data = ResourceOutput(
            type=res_type,
            content=res.get("content", ""),
            topic=res.get("topic", request.topic),
            difficulty=res.get("difficulty", "beginner"),
        )
        resources.append(resource_data)

        # 只有标准资源类型才写入数据库
        if res_type in DB_RESOURCE_TYPES:
            review = review_results.get(res_type, {})
            db_resource = Resource(
                learner_id=learner_id or "unknown",
                session_id=request.session_id,
                resource_type=res_type,
                content=res.get("content", ""),
                topic=res.get("topic", request.topic),
                difficulty=res.get("difficulty", "beginner"),
                stage=res_stage,
                sources=res.get("sources", None),
                review_score=review.get("score", None),
                review_passed="passed" if review.get("passed", True) else "failed",
            )
            db.add(db_resource)

        # 所有资源都存入内存 store（包括 learning_path）
        add_resource(request.session_id, {**resource_data.model_dump(), "stage": res_stage})

    # 将学习路径持久化到 Learner 表（含 node_states 初始化）
    learning_path_data = result.get("learning_path", {})
    if learning_path_data and learner_id:
        from app.models.learner import Learner as LearnerModel
        stmt_lp = select(LearnerModel).where(LearnerModel.id == learner_id)
        result_lp = await db.execute(stmt_lp)
        learner_record = result_lp.scalar_one_or_none()
        if learner_record:
            # 初始化每个节点的 node_states 到 learning_path 中
            for stage in learning_path_data.get("path", []):
                if "completed" not in stage:
                    stage["completed"] = False
                if "basic_test_passed" not in stage:
                    stage["basic_test_passed"] = False
                if "advanced_test_passed" not in stage:
                    stage["advanced_test_passed"] = False
                if "has_resources" not in stage:
                    stage["has_resources"] = (stage.get("stage", 0) == 1)  # 只有节点 1 初始有资源
            learner_record.learning_path = learning_path_data

            # 计算并持久化报告指标快照
            try:
                from app.metrics.report_builder import build_report_cache
                all_content = []
                all_difficulties = []
                for res in resources:
                    content = res.content if hasattr(res, 'content') else str(res)
                    if content:
                        all_content.append(str(content))
                    if res.difficulty:
                        all_difficulties.append(res.difficulty)

                profile_for_report = profile or {}
                if learner_record:
                    profile_for_report = {
                        **profile_for_report,
                        "knowledge_points": learner_record.knowledge_points or [],
                        "blind_spots": learner_record.blind_spots or [],
                        "overall_level": learner_record.overall_level or "beginner",
                        "recommended_difficulty": learner_record.recommended_difficulty or "beginner",
                    }

                report_cache = await build_report_cache(
                    all_content=all_content,
                    all_difficulties=all_difficulties,
                    topic=request.topic,
                    profile=profile_for_report,
                    learning_path=learning_path_data or {},
                )
                learner_record.report_cache = report_cache
                print(f"[报告快照] 已计算并持久化")
            except Exception as e:
                print(f"[警告] 报告快照计算失败: {e}")

    await db.flush()
    return resources


@router.get("/resources/{session_id}", response_model=list[ResourceOutput])
async def get_resources(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    stage: int = None,
):
    """获取指定会话的生成资源。传 stage 参数可按学习节点过滤。"""
    # 先从 MySQL 查询
    stmt = select(Resource).where(Resource.session_id == session_id)
    if stage is not None:
        stmt = stmt.where(Resource.stage == stage)
    result = await db.execute(stmt)
    db_resources = result.scalars().all()

    if db_resources:
        return [
            ResourceOutput(
                type=r.resource_type,
                content=r.content,
                topic=r.topic,
                difficulty=r.difficulty or "beginner",
            )
            for r in db_resources
        ]

    # 降级：从内存 store 读取（支持 stage 过滤）
    session = get_session(session_id)
    store_resources = session.get("resources", [])
    if stage is not None:
        store_resources = [r for r in store_resources if r.get("stage") == stage]
    return [
        ResourceOutput(
            type=r.get("type", ""),
            content=r.get("content", ""),
            topic=r.get("topic", ""),
            difficulty=r.get("difficulty", "beginner"),
        )
        for r in store_resources if r.get("type") != "learning_path"
    ]


@router.get("/trace/{session_id}")
async def get_trace(session_id: str):
    """返回完整工作流追踪数据——每个节点的输入输出和 LLM 调用明细"""
    from app.core.store import get_trace_entries
    session = get_session(session_id)
    entries = get_trace_entries(session_id)
    agent_logs = session.get("agent_logs", [])

    resources = session.get("resources", [])
    outcome = "unknown"
    if any(r.get("type") == "learning_path" for r in resources):
        for r in resources:
            if r.get("type") == "lecture" and "未通过质量审核" in str(r.get("content", "")):
                outcome = "degraded"
                break
        else:
            outcome = "completed"

    return {
        "session_id": session_id,
        "topic": session.get("topic", ""),
        "profile": {
            "difficulty": session.get("profile", {}).get("recommended_difficulty", ""),
            "goals": session.get("profile", {}).get("goals", []),
        },
        "nodes": entries,
        "agent_logs": agent_logs,
        "outcome": {"result": outcome, "resources_count": len(resources)},
    }
