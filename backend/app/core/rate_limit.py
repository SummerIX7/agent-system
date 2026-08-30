"""
频率限制 FastAPI 依赖 —— 保护 LLM 消耗型接口不被恶意刷量

使用示例：
    from app.core.rate_limit import RateLimit

    _generate_ratelimit = RateLimit("generate", max_requests=5, window=60)

    @router.post("/generate")
    async def generate_resources(
        ...,
        _rl: None = Depends(_generate_ratelimit),
    ):
        ...

底层依赖 store.check_rate_limit（Redis Lua/内存降级），管理员默认豁免。
"""

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import get_current_user
from app.core.store import check_rate_limit


class RateLimit:
    """基于用户/IP 的滑窗限流依赖工厂"""

    def __init__(
        self,
        key: str,
        max_requests: int = 10,
        window: int = 60,
        scope: str = "user",
        admin_bypass: bool = True,
    ):
        """
        Args:
            key: 逻辑键（如 "generate"、"feedback"），用于区分不同接口配额
            max_requests: 窗口内最大请求次数
            window: 窗口大小（秒）
            scope: "user" 按用户 ID 限流；"ip" 按客户端 IP
            admin_bypass: 是否豁免管理员
        """
        self.key = key
        self.max_requests = max_requests
        self.window = window
        self.scope = scope
        self.admin_bypass = admin_bypass

    async def __call__(
        self,
        request: Request,
        current_user=Depends(get_current_user),
    ) -> None:
        # 管理员豁免（管理界面 / 压测场景）
        if self.admin_bypass and getattr(current_user, "role", None) == "admin":
            return

        if self.scope == "user":
            subject = f"user:{current_user.id}"
        else:
            client = request.client
            subject = f"ip:{client.host if client else 'unknown'}"

        rkey = f"{subject}:{self.key}"
        allowed = check_rate_limit(
            rkey,
            max_requests=self.max_requests,
            window_seconds=self.window,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请在 {self.window} 秒后重试",
                headers={"Retry-After": str(self.window)},
            )
