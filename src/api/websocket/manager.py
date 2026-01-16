"""
WebSocket Connection Manager for real-time courtroom communication
"""

from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """
    WebSocket连接管理器，处理多个客户端连接
    """

    def __init__(self):
        # session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket, role: Optional[str] = None):
        """
        建立WebSocket连接

        Args:
            session_id: 法庭会话ID
            websocket: WebSocket连接对象
            role: 用户角色（用于HITL）
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)
        print(f"WebSocket连接建立: session={session_id}, connections={len(self.active_connections[session_id])}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        """
        断开WebSocket连接

        Args:
            session_id: 法庭会话ID
            websocket: WebSocket连接对象
        """
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            if len(self.active_connections[session_id]) == 0:
                del self.active_connections[session_id]

        print(f"WebSocket连接断开: session={session_id}")

    async def broadcast_to_session(self, session_id: str, event: str, data: dict):
        """
        向会话的所有WebSocket连接广播消息

        Args:
            session_id: 法庭会话ID
            event: 事件类型
            data: 事件数据
        """
        if session_id not in self.active_connections:
            return

        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)

        disconnected = set()
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"发送消息失败: {str(e)}")
                disconnected.add(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(session_id, connection)

    async def send_to_connection(self, websocket: WebSocket, event: str, data: dict):
        """
        向单个WebSocket连接发送消息

        Args:
            websocket: WebSocket连接对象
            event: 事件类型
            data: 事件数据
        """
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        await websocket.send_text(message)

    def get_connection_count(self, session_id: str) -> int:
        """
        获取会话的连接数

        Args:
            session_id: 法庭会话ID

        Returns:
            连接数
        """
        return len(self.active_connections.get(session_id, set()))


# 全局连接管理器实例
manager = ConnectionManager()
