"""B 端管理后台路由 — 统一挂载"""
from fastapi import APIRouter, Depends

from app.core.auth import require_admin
from app.api.admin.dashboard import router as dashboard_router
from app.api.admin.users import router as users_router
from app.api.admin.approval import router as approval_router
from app.api.admin.knowledge import router as knowledge_router

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)], tags=["B端管理后台"])
router.include_router(dashboard_router)
router.include_router(users_router)
router.include_router(approval_router)
router.include_router(knowledge_router)
