"""LLM 响应缓存（prompt + topic 哈希 → response，默认 1h TTL）。"""

from __future__ import annotations

import hashlib
from typing import Optional

from app.core.store._client import KEY_LLM_CACHE, _get_redis, _is_redis_ok


def _hash_content(content: str) -> str:
    """对内容做哈希，生成缓存键"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def get_llm_cache(prompt: str, topic: str = "") -> Optional[str]:
    """获取缓存的 LLM 响应；用 prompt + topic 的哈希作为缓存键。"""
    r = _get_redis()

    if not _is_redis_ok(r):
        return None

    cache_key = _hash_content(prompt + topic)
    cached = r.get(f"{KEY_LLM_CACHE}:{cache_key}")
    return cached


def set_llm_cache(prompt: str, response: str, topic: str = "", ttl: int = 3600) -> None:
    """缓存 LLM 响应（默认 1 小时）。

    适合缓存：知识概念解释、标准问题回答。
    不适合缓存：个性化生成、苏格拉底追问。
    """
    r = _get_redis()

    if not _is_redis_ok(r):
        return

    cache_key = _hash_content(prompt + topic)
    r.setex(f"{KEY_LLM_CACHE}:{cache_key}", ttl, response)
