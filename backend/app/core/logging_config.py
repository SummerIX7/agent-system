"""
统一日志配置模块。

设计目标：
1. 单一入口 `setup_logging()` 通过 `logging.dictConfig` 配置全局 logger，避免各模块散乱使用 `print`。
2. 通过 `contextvars.ContextVar` 保存 `request_id` / `session_id`，在异步任务间天然隔离；
   `RequestContextFilter` 会把它们注入每条 log record，格式化时可用 `%(request_id)s` 引用。
3. Sentry 采用条件接入：仅当 `SENTRY_DSN` 环境变量存在且 `sentry-sdk` 已安装时初始化，
   不给已有部署带来强依赖。
4. 提供 `bind_request_context()` 供 middleware 在请求进入时设置上下文，
   离开时通过返回的 token 复位。
"""

from __future__ import annotations

import logging
import logging.config
import os
import sys
from contextvars import ContextVar, Token
from typing import Optional

# ── 请求级 ContextVar ──
# 默认值 "-" 便于日志格式化时占位对齐
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_session_id_var: ContextVar[str] = ContextVar("session_id", default="-")


def get_request_id() -> str:
    """获取当前协程/任务上下文里的 request_id。"""
    return _request_id_var.get()


def get_session_id() -> str:
    """获取当前协程/任务上下文里的 session_id。"""
    return _session_id_var.get()


def bind_request_context(request_id: str, session_id: str = "-") -> tuple[Token, Token]:
    """把 request_id / session_id 绑定到当前上下文，返回 token 供复位使用。"""
    return (
        _request_id_var.set(request_id),
        _session_id_var.set(session_id),
    )


def reset_request_context(tokens: tuple[Token, Token]) -> None:
    """复位 bind_request_context 返回的 token。"""
    try:
        _request_id_var.reset(tokens[0])
    except Exception:
        pass
    try:
        _session_id_var.reset(tokens[1])
    except Exception:
        pass


class RequestContextFilter(logging.Filter):
    """把 ContextVar 中的 request_id / session_id 注入到 LogRecord。

    - 缺失时用 `-` 兜底，避免 formatter 引用 `%(request_id)s` 抛 KeyError。
    - 由 dictConfig 挂到根 handler 上，业务代码无需手动打点。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_var.get()
        if not hasattr(record, "session_id"):
            record.session_id = _session_id_var.get()
        return True


def _build_dict_config(level: str) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": "app.core.logging_config.RequestContextFilter",
            },
        },
        "formatters": {
            "default": {
                # 带 request_id 的结构化前缀，便于 grep / Loki 提取
                "format": (
                    "%(asctime)s %(levelname)-7s [%(name)s]"
                    " [rid=%(request_id)s sid=%(session_id)s] %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
                "filters": ["request_context"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            # 抑制第三方过于详细的日志（httpx/uvicorn access 会淹没业务日志）
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
            "urllib3": {"level": "WARNING", "propagate": True},
            "chromadb": {"level": "WARNING", "propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
        },
    }


_configured = False


def setup_logging(level: Optional[str] = None) -> None:
    """初始化日志系统。多次调用幂等，仅第一次生效。"""
    global _configured
    if _configured:
        return

    resolved_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.config.dictConfig(_build_dict_config(resolved_level))

    # 条件接入 Sentry：仅当 DSN 存在且 SDK 可用
    _init_sentry_if_available()

    _configured = True

    # 默认给启动流程一条可见的确认日志
    logging.getLogger(__name__).info(
        "logging initialized (level=%s, sentry=%s)",
        resolved_level,
        "on" if _sentry_enabled else "off",
    )


_sentry_enabled = False


def _init_sentry_if_available() -> None:
    """如果环境变量 SENTRY_DSN 存在且 sentry-sdk 已安装，则初始化 Sentry。

    - 未安装 sentry-sdk 时静默跳过，不影响主流程
    - 生产环境推荐 `pip install sentry-sdk[fastapi]`
    """
    global _sentry_enabled

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk  # type: ignore
        from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore
        from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore
    except ImportError:
        print(
            "[logging] 检测到 SENTRY_DSN 但 sentry-sdk 未安装，跳过 Sentry 初始化。"
            "如需启用错误监控，请执行: pip install 'sentry-sdk[fastapi]'",
            file=sys.stderr,
        )
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("ENV", "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        _sentry_enabled = True
    except Exception as e:  # noqa: BLE001
        print(f"[logging] Sentry 初始化失败: {e}", file=sys.stderr)
