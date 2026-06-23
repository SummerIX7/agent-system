import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.store import pop_ws_messages, push_ws_message, add_agent_log

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/agent-status/{session_id}")
async def agent_status_ws(websocket: WebSocket, session_id: str):
    """Agent 状态实时推送"""
    await websocket.accept()

    # 发送连接确认
    await websocket.send_json({
        "agent": "系统",
        "status": "connected",
        "message": f"会话 {session_id} 已连接",
        "progress": 0,
    })

    try:
        while True:
            # 检查是否有待发消息
            messages = pop_ws_messages(session_id)
            for msg in messages:
                await websocket.send_json(msg)

            # 接收客户端消息（非阻塞，超时 1 秒）
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # 处理客户端消息
                await websocket.send_json({
                    "agent": "系统",
                    "status": "running",
                    "message": f"收到: {data}",
                    "progress": 50,
                })
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass


def broadcast_agent_status(session_id: str, agent_name: str, status: str, message: str, progress: float = 0):
    """广播 Agent 状态到 WebSocket（供 workflow 节点调用）"""
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
