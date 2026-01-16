"""
Court Service - Core service layer that encapsulates LangGraph logic
"""

from typing import Dict, List, Optional, Set
import uuid
from datetime import datetime
import asyncio
from langchain_core.messages import ChatMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.workflow import app
from src.state import CourtState, evidence
from src.schemas.session import CourtRole


class CourtSession:
    """
    法庭会话类，封装单个辩论会话的所有信息和逻辑
    """

    def __init__(self, session_id: str, human_role: Optional[CourtRole] = None):
        self.session_id = session_id
        self.human_role = human_role
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.app = app
        self.config = {"configurable": {"thread_id": session_id}}
        self.state: Optional[CourtState] = None
        self.websocket_connections: Set = set()
        self.requires_human_input = False
        self.pending_input_role: Optional[str] = None
        self._lock = asyncio.Lock()

    async def initialize(self, case_info: str, case_evidence: List[dict]):
        """初始化法庭状态"""
        async with self._lock:
            initial_state: CourtState = {
                "case_info": case_info,
                "case_evidence": [
                    evidence(speaker=ev["speaker"], content=HumanMessage(content=ev["content"]))
                    for ev in case_evidence
                ],
                "phase": "准备阶段",
                "messages": [],
                "speaker": "",
                "human_role": self.human_role.value if self.human_role else None,
                "rounds": 0,
            }

            # 启动辩论
            self.state = await asyncio.to_thread(self.app.invoke, initial_state, self.config)
            self.last_activity = datetime.now()

    async def advance_debate(self):
        """推进辩论到下一步"""
        async with self._lock:
            if self.requires_human_input:
                raise ValueError("需要人类输入，无法自动推进")

            if not self.state:
                raise ValueError("会话未初始化")

            # 检查是否已经结束
            if self.state.get("phase") == "休庭小结":
                return self.state

            # 推进工作流
            try:
                # 如果当前发言人不是人类，自动推进
                current_speaker = self.state.get("speaker", "")
                if current_speaker != self.human_role:
                    # 需要推进
                    self.state = await asyncio.to_thread(self.app.invoke, None, self.config)
                    self.last_activity = datetime.now()

                    # 检查是否需要人类输入
                    if self.state.get("speaker") == self.human_role:
                        self.requires_human_input = True
                        self.pending_input_role = self.human_role

                return self.state
            except Exception as e:
                raise RuntimeError(f"推进辩论失败: {str(e)}")

    async def submit_human_input(self, content: str) -> CourtState:
        """提交人类输入并继续工作流"""
        async with self._lock:
            if not self.requires_human_input:
                raise ValueError("当前不需要人类输入")

            if not self.state:
                raise ValueError("会话未初始化")

            try:
                # 使用Command.resume继续执行
                self.state = await asyncio.to_thread(
                    self.app.invoke,
                    Command(resume=content),
                    self.config
                )

                self.requires_human_input = False
                self.pending_input_role = None
                self.last_activity = datetime.now()

                return self.state
            except Exception as e:
                raise RuntimeError(f"提交人类输入失败: {str(e)}")

    def get_formatted_messages(self) -> List[dict]:
        """获取格式化的消息历史"""
        if not self.state or not self.state.get("messages"):
            return []

        messages = []
        for msg in self.state["messages"]:
            if isinstance(msg, (ChatMessage, HumanMessage)):
                messages.append({
                    "sender": getattr(msg, "name", "未知"),
                    "content": msg.content,
                    "role": "assistant" if isinstance(msg, ChatMessage) else "human",
                    "timestamp": self.created_at.isoformat()
                })
        return messages

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "status": "ended" if self.state.get("phase") == "休庭小结" else "active",
            "current_phase": self.state.get("phase", "") if self.state else "准备阶段",
            "current_speaker": self.state.get("speaker", "") if self.state else "",
            "messages": self.get_formatted_messages(),
            "rounds": self.state.get("rounds", 0) if self.state else 0,
            "requires_human_input": self.requires_human_input,
            "pending_input_role": self.pending_input_role,
            "human_role": self.human_role.value if self.human_role else None,
        }


class CourtService:
    """
    法庭服务类，管理所有法庭会话
    """

    def __init__(self):
        self.sessions: Dict[str, CourtSession] = {}
        self._cleanup_task = None

    def _start_cleanup_task(self):
        """启动定时清理任务（懒加载，在第一个会话创建时调用）"""
        if not self._cleanup_task:
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            except RuntimeError:
                # 如果没有运行的事件循环，稍后再试
                pass

    async def _cleanup_expired_sessions(self):
        """清理3小时未活动的会话"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时检查一次
                now = datetime.now()
                expired_sessions = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if (now - session.last_activity).total_seconds() > 10800  # 3小时
                ]

                for session_id in expired_sessions:
                    await self.cleanup_session(session_id)
                    print(f"清理过期会话: {session_id}")

            except Exception as e:
                print(f"清理会话时出错: {str(e)}")

    async def create_session(
        self,
        case_info: str,
        case_evidence: List[dict],
        human_role: Optional[CourtRole] = None,
    ) -> str:
        """
        创建新的法庭会话

        Args:
            case_info: 案件基本信息
            case_evidence: 案件证据列表
            human_role: 人类扮演的角色，None表示纯AI模式

        Returns:
            session_id
        """
        # 启动清理任务（如果需要）
        self._start_cleanup_task()

        session_id = f"court_{uuid.uuid4().hex[:8]}"
        session = CourtSession(session_id, human_role)

        # 初始化状态
        await session.initialize(case_info, case_evidence)

        # 存储会话
        self.sessions[session_id] = session

        return session_id

    async def get_session(self, session_id: str) -> dict:
        """
        获取会话状态

        Args:
            session_id: 会话ID

        Returns:
            会话状态字典

        Raises:
            ValueError: 会话不存在
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        return self.sessions[session_id].to_dict()

    async def advance_debate(self, session_id: str) -> dict:
        """
        推进辩论

        Args:
            session_id: 会话ID

        Returns:
            更新后的会话状态

        Raises:
            ValueError: 会话不存在或需要人类输入
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        session = self.sessions[session_id]
        await session.advance_debate()

        return session.to_dict()

    async def submit_human_input(
        self, session_id: str, role: str, content: str
    ) -> dict:
        """
        提交人类输入

        Args:
            session_id: 会话ID
            role: 角色
            content: 输入内容

        Returns:
            更新后的会话状态

        Raises:
            ValueError: 会话不存在或不需要输入
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        session = self.sessions[session_id]
        await session.submit_human_input(content)

        return session.to_dict()

    async def cleanup_session(self, session_id: str):
        """
        清理会话

        Args:
            session_id: 会话ID
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]

            # 关闭所有WebSocket连接
            for websocket in session.websocket_connections:
                await websocket.close()

            # 从字典中移除
            del self.sessions[session_id]

    def get_session_object(self, session_id: str) -> Optional[CourtSession]:
        """
        获取会话对象（用于WebSocket）

        Args:
            session_id: 会话ID

        Returns:
            CourtSession对象或None
        """
        return self.sessions.get(session_id)


# 全局服务实例
court_service = CourtService()
