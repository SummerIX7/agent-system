"""WebSocket \u63a8\u9001\u7aef\u70b9\u3002

\u65b0\u5b9e\u73b0\u7b56\u7565\uff082026-07 P1 \u4f18\u5316\uff09\uff1a
- \u4f18\u5148\u7528 Redis Pub/Sub \u8ba2\u9605 ``ws:pub:{session_id}``\uff0c\u6d88\u606f\u5b9e\u65f6\u9001\u8fbe\uff0c
  \u514d\u53bb\u65e7\u5b9e\u73b0\u7684 500ms \u8f6e\u8be2\u3002
- \u521d\u6b21\u8fde\u63a5\u65f6\u5148 pop \u4e00\u6b21 List\uff0c\u628a\u201c\u5efa\u8fde\u524d\u4ea7\u751f\u4f46\u672a\u6d88\u8d39\u201d\u7684\u6d88\u606f\u56de\u8865\u3002
- Redis \u4e0d\u53ef\u7528\u65f6\u81ea\u52a8\u964d\u7ea7\u4e3a\u8f6e\u8be2\u5185\u5b58\u961f\u5217\uff0c\u4fdd\u8bc1\u672c\u5730\u5f00\u53d1\u3001Redis \u6545\u969c\u65f6\u4ecd\u80fd\u5de5\u4f5c\u3002
- \u4fdd\u7559\u5bf9\u5ba2\u6237\u7aef receive_text \u7684\u5904\u7406\uff0c\u907f\u514d\u524d\u7aef\u884c\u4e3a\u53d8\u5316\u3002
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.store import (
    KEY_WS_PUB,
    add_agent_log,
    pop_ws_messages,
    push_ws_message,
    redis_is_available,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def _fanout_pubsub(
    session_id: str, websocket: WebSocket, stop_event: asyncio.Event
) -> None:
    """\u8ba2\u9605 Redis pub/sub \u5e76\u5c06\u6d88\u606f\u8f6c\u53d1\u5230 WebSocket \u3002

    Redis \u4e0d\u53ef\u7528\u6216\u8ba2\u9605\u5931\u8d25\u65f6\u56de\u9000\u5230\u201c\u5468\u671f pop \u5185\u5b58\u961f\u5217\u201d\u964d\u7ea7\u6a21\u5f0f\u3002
    """
    if not redis_is_available():
        await _fallback_poll(session_id, websocket, stop_event)
        return

    settings = get_settings()
    channel = f"{KEY_WS_PUB}:{session_id}"

    try:
        # \u5ef6\u8fdf\u5bfc\u5165\uff0c\u4fdd\u8bc1 redis \u4f9d\u8d56\u53ea\u5728\u9700\u8981\u65f6\u521d\u59cb\u5316
        import redis.asyncio as aioredis  # type: ignore
    except ImportError:
        logger.warning("redis.asyncio \u4e0d\u53ef\u7528\uff0c\u964d\u7ea7\u4e3a\u8f6e\u8be2")
        await _fallback_poll(session_id, websocket, stop_event)
        return

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=None,  # subscribe \u65f6\u4e0d\u80fd\u8bbe\u7f6e\uff0c\u4f1a\u65ad\u5f00
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis asyncio \u5efa\u8fde\u5931\u8d25\uff0c\u964d\u7ea7\u4e3a\u8f6e\u8be2: %s", e)
        await _fallback_poll(session_id, websocket, stop_event)
        return

    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)

        while not stop_event.is_set():
            # timeout=1.0 允许周期性回到主循环，便于检查 stop_event
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message is None:
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                payload = json.loads(data) if isinstance(data, str) else data
                await websocket.send_json(payload)
            except Exception as e:  # noqa: BLE001
                logger.warning("WS \u53d1\u9001\u5931\u8d25\uff08\u5931\u8054\u5ba2\u6237\u7aef\uff09: %s", e)
                break
    except Exception as e:  # noqa: BLE001
        logger.warning("Pub/Sub \u5faa\u73af\u5f02\u5e38\uff0c\u5df2\u9000\u51fa: %s", e)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            pass


async def _fallback_poll(
    session_id: str, websocket: WebSocket, stop_event: asyncio.Event
) -> None:
    """\u5185\u5b58\u961f\u5217 / Redis \u4e0d\u53ef\u7528\u65f6\u7684\u8f6e\u8be2\u964d\u7ea7\u5b9e\u73b0\uff08\u4fdd\u7559\u65e7\u884c\u4e3a\uff09\u3002"""
    while not stop_event.is_set():
        messages = pop_ws_messages(session_id)
        for msg in messages:
            try:
                await websocket.send_json(msg)
            except Exception:  # noqa: BLE001
                stop_event.set()
                return
        await asyncio.sleep(0.5)


async def _drain_backlog(session_id: str, websocket: WebSocket) -> None:
    """\u521d\u6b21\u8fde\u63a5\u65f6\u5c06 List \u4e2d\u5df2\u79ef\u538b\u7684\u6d88\u606f pop \u4e00\u6b21\u3002"""
    backlog = pop_ws_messages(session_id)
    for msg in backlog:
        try:
            await websocket.send_json(msg)
        except Exception:  # noqa: BLE001
            return


async def _consume_client_messages(
    websocket: WebSocket, stop_event: asyncio.Event
) -> None:
    """\u5904\u7406\u5ba2\u6237\u7aef\u53d1\u6765\u7684\u6587\u672c\u6d88\u606f\uff08\u4fdd\u7559\u539f\u56de\u58f0\u4e3a\uff09\u3002"""
    try:
        while not stop_event.is_set():
            data = await websocket.receive_text()
            await websocket.send_json({
                "agent": "\u7cfb\u7edf",
                "status": "running",
                "message": f"\u6536\u5230: {data}",
                "progress": 50,
            })
    except WebSocketDisconnect:
        stop_event.set()
    except Exception as e:  # noqa: BLE001
        logger.debug("client-consumer \u9000\u51fa: %s", e)
        stop_event.set()


@router.websocket("/ws/agent-status/{session_id}")
async def agent_status_ws(websocket: WebSocket, session_id: str):
    """Agent \u72b6\u6001\u5b9e\u65f6\u63a8\u9001\uff08Pub/Sub \u4f18\u5148 \u5185\u5b58\u961f\u5217\u964d\u7ea7\uff09\u3002"""
    await websocket.accept()

    # \u53d1\u9001\u8fde\u63a5\u786e\u8ba4
    await websocket.send_json({
        "agent": "\u7cfb\u7edf",
        "status": "connected",
        "message": f"\u4f1a\u8bdd {session_id} \u5df2\u8fde\u63a5",
        "progress": 0,
    })

    # \u56de\u8865\u5df2\u79ef\u538b\u6d88\u606f\uff08\u5efa\u8fde\u524d\u53d1\u5e03\u7684 pub/sub \u65e0\u6cd5\u56de\u653e\uff0c\u9760 List \u517c\u5bb9\uff09
    await _drain_backlog(session_id, websocket)

    stop_event = asyncio.Event()

    producer = asyncio.create_task(_fanout_pubsub(session_id, websocket, stop_event))
    consumer = asyncio.create_task(_consume_client_messages(websocket, stop_event))

    try:
        await asyncio.wait(
            {producer, consumer},
            return_when=asyncio.FIRST_COMPLETED,
        )
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        for task in (producer, consumer):
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass


def broadcast_agent_status(session_id: str, agent_name: str, status: str, message: str, progress: float = 0):
    """\u5e7f\u64ad Agent \u72b6\u6001\u5230 WebSocket\uff08\u4f9b workflow \u8282\u70b9\u8c03\u7528\uff09\u3002

    \u517c\u5bb9\u65e7\u8c03\u7528\u65b9\u5f0f\uff1a\u5185\u90e8\u4f9d\u7136\u8d70 push_ws_message\uff0c\u540e\u8005\u5df2\u53cc\u5199\uff08rpush + publish\uff09\u3002
    """
    push_ws_message(session_id, {
        "agent": agent_name,
        "status": status,
        "message": message,
        "progress": progress,
    })

    # 同时记录到 store
    add_agent_log(session_id, {
        "agent_name": agent_name,
        "status": status,
        "message": message,
        "progress": progress,
    })
