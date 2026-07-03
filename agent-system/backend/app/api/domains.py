"""
领域配置 API
返回可用领域列表，供前端动态加载
"""

from fastapi import APIRouter

from app.core.domains import get_all_domains

router = APIRouter(prefix="/api", tags=["领域配置"])


@router.get("/domains")
async def list_domains():
    """获取所有可用领域配置（完整字段，兼容旧路由）"""
    domains = get_all_domains()
    return [
        {
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "order": d.order,
            "core_topics": d.core_topics,
            "difficulty_levels": d.difficulty_levels,
            "self_assessment_skills": d.self_assessment_skills,
            "prerequisite_knowledge": d.prerequisite_knowledge,
        }
        for d in domains
    ]
