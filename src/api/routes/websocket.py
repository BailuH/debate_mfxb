"""
WebSocket API Routes for real-time courtroom updates
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional

from ...services.court_service import court_service, CourtSession
from ...api.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    role: Optional[str] = Query(None, description="观察者的角色"),
):
    """
    WebSocket连接端点

    Args:
        websocket: WebSocket连接对象
        session_id: 法庭会话ID
        role: 用户角色（可选）
    """
    # 检查会话是否存在
    session = court_service.get_session_object(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    # 建立连接
    await manager.connect(session_id, websocket, role)

    # 将会话添加到WebSocket连接集合
    session.websocket_connections.add(websocket)

    try:
        # 发送欢迎消息
        await manager.send_to_connection(
            websocket,
            "connected",
            {"session_id": session_id, "message": "已连接到法庭", "role": role},
        )

        # 发送当前状态
        session_data = await court_service.get_session(session_id)
        await manager.send_to_connection(
            websocket, "status_update", session_data
        )

        # 持续接收消息
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")
            event_data = message.get("data", {})

            await handle_websocket_event(session_id, event, event_data, websocket)

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
        if session:
            session.websocket_connections.discard(websocket)
    except Exception as e:
        print(f"WebSocket错误: {str(e)}")
        manager.disconnect(session_id, websocket)
        if session:
            session.websocket_connections.discard(websocket)


async def handle_websocket_event(
    session_id: str, event: str, data: dict, websocket: WebSocket
):
    """
    处理WebSocket事件

    Args:
        session_id: 法庭会话ID
        event: 事件类型
        data: 事件数据
        websocket: WebSocket连接对象
    """
    session = court_service.get_session_object(session_id)
    if not session:
        await manager.send_to_connection(
            websocket, "error", {"message": "Session not found"}
        )
        return

    try:
        if event == "human_input":
            # 处理人类输入
            await handle_human_input(session_id, data, websocket)

        elif event == "next_step":
            # 请求下一步（AI模式）
            await handle_next_step(session_id, websocket)

        elif event == "ping":
            # 心跳响应
            await manager.send_to_connection(websocket, "pong", {})

        else:
            # 未知事件
            await manager.send_to_connection(
                websocket, "error", {"message": f"Unknown event: {event}"}
            )

    except Exception as e:
        await manager.send_to_connection(websocket, "error", {"message": str(e)})


async def handle_human_input(session_id: str, data: dict, websocket: WebSocket):
    """
    处理人类输入事件

    Args:
        session_id: 法庭会话ID
        data: 事件数据（包含content和role）
        websocket: WebSocket连接对象
    """
    content = data.get("content")
    role = data.get("role")

    if not content or not role:
        await manager.send_to_connection(
            websocket,
            "error",
            {"message": "Missing required fields: content and role"},
        )
        return

    try:
        # 提交人类输入
        await court_service.submit_human_input(session_id, role, content)

        # 获取更新后的状态
        session_data = await court_service.get_session(session_id)

        # 广播更新消息
        await manager.broadcast_to_session(
            session_id, "debate_update", {"new_message": session_data["messages"][-1] if session_data["messages"] else None}
        )

    except Exception as e:
        await manager.send_to_connection(
            websocket, "error", {"message": f"Failed to submit human input: {str(e)}"}
        )


async def handle_next_step(session_id: str, websocket: WebSocket):
    """
    处理下一步事件（AI模式）

    Args:
        session_id: 法庭会话ID
        websocket: WebSocket连接对象
    """
    try:
        # 推进辩论
        session_data = await court_service.advance_debate(session_id)

        # 检查是否需要人类输入
        if session_data["requires_human_input"]:
            await manager.broadcast_to_session(
                session_id,
                "human_input_required",
                {
                    "required_role": session_data["pending_input_role"],
                    "prompt": f"现在是{session_data['current_phase']}，请你发言",
                },
            )
        else:
            # 广播更新消息
            await manager.broadcast_to_session(
                session_id,
                "debate_update",
                {
                    "new_message": session_data["messages"][-1]
                    if session_data["messages"]
                    else None,
                    "speaker_changed": True,
                    "new_speaker": session_data["current_speaker"],
                    "phase_changed": False,
                    "current_phase": session_data["current_phase"],
                    "round": session_data["rounds"],
                },
            )

    except ValueError as e:
        await manager.send_to_connection(websocket, "error", {"message": str(e)})
    except Exception as e:
        await manager.send_to_connection(
            websocket, "error", {"message": f"Failed to advance debate: {str(e)}"}
        )


async def broadcast_debate_update(session_id: str, message_data: dict):
    """
    广播辩论更新消息

    Args:
        session_id: 法庭会话ID
        message_data: 消息数据
    """
    await manager.broadcast_to_session(session_id, "debate_update", message_data)


async def broadcast_human_input_required(session_id: str, role: str, prompt: str):
    """
    广播需要人类输入的消息

    Args:
        session_id: 法庭会话ID
        role: 需要输入的角色
        prompt: 提示信息
    """
    await manager.broadcast_to_session(
        session_id,
        "human_input_required",
        {
            "required_role": role,
            "prompt": prompt,
        },
    )


async def broadcast_debate_ended(session_id: str, session_data: dict):
    """
    广播辩论结束消息

    Args:
        session_id: 法庭会话ID
        session_data: 会话数据
    """
    await manager.broadcast_to_session(
        session_id,
        "debate_ended",
        {
            "final_messages": session_data["messages"],
            "total_rounds": session_data["rounds"],
            "final_phase": session_data["current_phase"],
        },
    )
