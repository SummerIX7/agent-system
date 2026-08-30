"""
\u5206\u5c42\u5065\u5eb7\u68c0\u67e5\u4e0e\u6307\u6807\u91c7\u96c6\u7aef\u70b9\u3002

\u8bbe\u8ba1\u76ee\u6807\uff08\u5bf9\u9f50 K8s / \u4f20\u7edf LB\u30017.2 \u8282\uff09\uff1a
- ``/livez`` : \u8fdb\u7a0b\u5b58\u6d3b\u63a2\u9488\u3002\u53ea\u8981 FastAPI \u80fd\u56de\u5e94\u5c31\u8fd4\u56de 200\uff0c\u4e0d\u505a\u4efb\u4f55\u4f9d\u8d56\u68c0\u6d4b\u3002
- ``/readyz`` : \u5c31\u7eea\u63a2\u9488\u3002\u4f9d\u5b58\u4e0d\u5065\u5eb7\u65f6\u8fd4\u56de 503\uff0c\u8ba9 LB \u4e0d\u5f80\u672c\u8282\u70b9\u8f6c\u53d1\u3002\n  \u68c0\u6d4b\u9879\uff1a
    * MySQL \u53ef\u8fbe\uff08select 1\uff09
    * Redis \u53ef\u8fbe\uff08_is_redis_ok\uff09
    * \u5fc5\u8981\u7684\u5bc6\u94a5\u5df2\u914d\u7f6e\uff08MOCK \u6a21\u5f0f\u65f6\u8df3\u8fc7\uff09
- ``/metrics`` : Prometheus \u6587\u672c\u683c\u5f0f\u7684\u8f7b\u91cf\u6307\u6807\u3002\u5f53\u524d\u5305\u542b\uff1a
    * process_uptime_seconds
    * http_requests_total{status=...}
    * llm_calls_total\uff08\u9884\u7559\u63a5\u53e3\uff0c\u7531 BaseAgent \u8c03\u7528\uff09
  \u8fdb\u9636\u9700\u6c42\u53ef\u63a5\u5165 prometheus_client\uff0c\u8fd9\u91cc\u5148\u4ee5\u81ea\u7ef4\u62a4\u8ba1\u6570\u5668\u5b9e\u73b0\uff0c\u907f\u514d\u65b0\u589e\u4f9d\u8d56\u3002

\u6240\u6709\u7aef\u70b9\u90fd\u4e0d\u9700\u9274\u6743\u3002\n"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.store import _get_redis, _is_redis_ok
from app.models.database import async_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["\u5065\u5eb7\u68c0\u67e5"])

# ── \u8fdb\u7a0b\u542f\u52a8\u65f6\u95f4 \u2500\u2500
_process_start = time.time()

# ── \u7b80\u5355\u8ba1\u6570\u5668\uff1aHTTP \u72b6\u6001\u7801\u7ef4\u5ea6 \u2500\u2500
# \u4e3a\u4e86\u907f\u514d\u65b0\u589e prometheus_client \u4f9d\u8d56\uff0c\u8fd9\u91cc\u624b\u5199\u4e00\u4e2a\u6781\u7b80\u7248\uff1b
# \u5982\u540e\u7eed\u63a5\u5165\u6b63\u89c4\u76d1\u63a7\uff0c\u53ef\u76f4\u63a5\u66ff\u6362\u4e3a Counter/Histogram\u3002
_http_status_counter: dict[int, int] = {}
_llm_calls_counter: int = 0
_llm_cache_hit_counter: int = 0


def record_http_status(code: int) -> None:
    """\u4f9b middleware \u8c03\u7528\u3002"""
    _http_status_counter[code] = _http_status_counter.get(code, 0) + 1


def record_llm_call(cache_hit: bool = False) -> None:
    """\u4f9b BaseAgent.call_llm \u5728\u672a\u6765\u63a5\u5165\u65f6\u8c03\u7528\u3002"""
    global _llm_calls_counter, _llm_cache_hit_counter
    _llm_calls_counter += 1
    if cache_hit:
        _llm_cache_hit_counter += 1


# ═══════════════════════════════════════════
# /livez \u2014 \u5c3d\u91cf\u4fdd\u6301\u8f7b\u91cf\uff0c\u4e0d\u78b0\u4e1a\u52a1\u4f9d\u8d56
# ═══════════════════════════════════════════

@router.get("/livez")
async def livez() -> dict[str, str]:
    """\u5b58\u6d3b\u63a2\u9488\uff1a\u53ea\u8981\u8fdb\u7a0b\u80fd\u8ddf\u8981\u5c31\u7b97\u6d3b\u3002"""
    return {"status": "ok"}


# ═══════════════════════════════════════════
# /readyz \u2014 \u4e25\u683c\u4f9d\u8d56\u68c0\u67e5\uff0c\u4efb\u4e00\u5931\u8d25 -> 503
# ═══════════════════════════════════════════

async def _check_mysql() -> dict[str, Any]:
    try:
        async with async_session() as sess:
            await sess.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:  # noqa: BLE001
        return {"status": "unhealthy", "error": type(e).__name__}


def _check_redis() -> dict[str, Any]:
    r = _get_redis()
    if not _is_redis_ok(r):
        # Redis \u4e0d\u53ef\u7528\u65f6\u9879\u76ee\u4f1a\u964d\u7ea7\u4e3a\u5185\u5b58\u5b58\u50a8 -> \u8fd9\u91cc\u6807\u8bb0\u4e3a degraded \u4f46\u4ecd\u53ef\u7528
        return {"status": "degraded", "backend": "memory"}
    return {"status": "healthy", "backend": "redis"}


def _check_llm_config(settings) -> dict[str, Any]:
    # MOCK \u6a21\u5f0f\u4e0b\u4e0d\u9700\u771f\u5b9e API Key
    if getattr(settings, "MOCK_MODE", False):
        return {"status": "healthy", "mode": "mock"}
    missing = []
    if not settings.LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not settings.EMBEDDING_API_KEY and getattr(settings, "ENABLE_KNOWLEDGE_BASE", False):
        missing.append("EMBEDDING_API_KEY")
    if missing:
        return {"status": "unhealthy", "missing": missing}
    return {"status": "healthy"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, Any]:
    """\u5c31\u7eea\u63a2\u9488\uff1a\u4efb\u4e00\u5173\u952e\u4f9d\u8d56 unhealthy \u65f6\u8fd4\u56de 503\u3002"""
    settings = get_settings()

    checks = {
        "mysql": await _check_mysql(),
        "redis": _check_redis(),
        "llm_config": _check_llm_config(settings),
    }

    # degraded \u4e0d\u963b\u65ad\u5c31\u7eea\uff08\u5185\u5b58\u964d\u7ea7\u4ecd\u53ef\u5bf9\u5916\u63d0\u4f9b\u670d\u52a1\uff09
    unhealthy = [name for name, r in checks.items() if r.get("status") == "unhealthy"]

    if unhealthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "checks": checks, "failed": unhealthy}

    return {"status": "ok", "checks": checks}


# ═══════════════════════════════════════════
# /metrics \u2014 Prometheus \u6587\u672c\u683c\u5f0f
# ═══════════════════════════════════════════

@router.get("/metrics")
async def metrics(request: Request) -> Response:
    """Prometheus \u62c9\u53d6\u683c\u5f0f\u3002

    \u4ec5\u5305\u542b\u57fa\u672c\u6307\u6807\uff0c\u540e\u7eed\u5982\u63a5\u5165\u6b63\u89c4 prometheus_client \u53ef\u5347\u7ea7\u4e3a Histogram\u3002
    """
    lines: list[str] = []

    uptime = time.time() - _process_start
    lines.append("# HELP process_uptime_seconds Uptime of the FastAPI process")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append(f"process_uptime_seconds {uptime:.3f}")

    lines.append("# HELP http_requests_total HTTP requests observed by status code")
    lines.append("# TYPE http_requests_total counter")
    for code, count in sorted(_http_status_counter.items()):
        lines.append(f'http_requests_total{{code="{code}"}} {count}')

    lines.append("# HELP llm_calls_total LLM calls counted by BaseAgent")
    lines.append("# TYPE llm_calls_total counter")
    lines.append(f"llm_calls_total {_llm_calls_counter}")

    lines.append("# HELP llm_cache_hits_total LLM cache hits observed")
    lines.append("# TYPE llm_cache_hits_total counter")
    lines.append(f"llm_cache_hits_total {_llm_cache_hit_counter}")

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
