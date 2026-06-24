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

    resources = []
    for res in result.get("final_resources", []):
        resource_data = ResourceOutput(
            type=res.get("type", ""),
            content=res.get("content", ""),
            topic=res.get("topic", request.topic),
            difficulty=res.get("difficulty", "beginner"),
        )
        resources.append(resource_data)

        # 1. 写入 MySQL
        # content 可能是字符串（讲义等）或 dict（试题、学习路径），需要统一处理
        raw_content = res.get("content", "")
        if isinstance(raw_content, (dict, list)):
            import json
            content_str = json.dumps(raw_content, ensure_ascii=False)
        else:
            content_str = str(raw_content)

        db_resource = Resource(
            learner_id=learner_id or "unknown",
            session_id=request.session_id,
            resource_type=res.get("type", "lecture"),
            content=content_str,
            topic=res.get("topic", request.topic),
            difficulty=res.get("difficulty", "beginner"),
            sources=res.get("sources", None),
            review_score=res.get("review_score", None),
            review_passed="passed",
        )
        db.add(db_resource)

        # 2. 同时存入内存 store（兼容旧逻辑）
        add_resource(request.session_id, resource_data.model_dump())

    await db.flush()
    return resources


@router.get("/resources/{session_id}", response_model=list[ResourceOutput])
async def get_resources(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定会话的生成资源（优先从数据库读取）"""
    # 先从 MySQL 查询
    stmt = select(Resource).where(Resource.session_id == session_id)
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

    # 降级：从内存 store 读取
    session = get_session(session_id)
    return [
        ResourceOutput(
            type=r.get("type", ""),
            content=r.get("content", ""),
            topic=r.get("topic", ""),
            difficulty=r.get("difficulty", "beginner"),
        )
        for r in session.get("resources", [])
    ]
