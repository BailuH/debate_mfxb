"""
Pydantic models for session management
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class CourtRole(str, Enum):
    """法庭角色枚举"""
    PLAINTIFF = "原告律师"
    DEFENDANT = "被告律师"
    JUDGE = "法官"


class CourtPhase(str, Enum):
    """法庭阶段枚举"""
    OPENING = "开庭阶段"
    CROSS_EXAMINATION = "交叉质证"
    CLOSING = "休庭小结"
    ENDED = "已结束"


class Evidence(BaseModel):
    """证据模型"""
    speaker: str = Field(..., description="提交证据的发言人角色")
    content: str = Field(..., description="证据内容描述")


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    case_info: str = Field(..., description="案件基本信息描述")
    case_evidence: Optional[List[Evidence]] = Field(default=[], description="案件证据列表")
    human_role: Optional[CourtRole] = Field(None, description="人类扮演的角色，null表示纯AI模式")


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    session_id: str = Field(..., description="会话唯一标识")
    status: str = Field(default="created", description="会话状态")
    current_phase: str = Field(..., description="当前法庭阶段")
    current_speaker: str = Field(..., description="当前发言人角色")


class MessageResponse(BaseModel):
    """消息响应模型"""
    sender: str = Field(..., description="消息发送者（带角色）")
    content: str = Field(..., description="消息内容")
    role: str = Field(..., description="消息角色（assistant/human）")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")


class SessionStatusResponse(BaseModel):
    """会话状态响应"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="会话状态")
    current_phase: str = Field(..., description="当前法庭阶段")
    current_speaker: str = Field(..., description="当前发言人")
    messages: List[MessageResponse] = Field(..., description="消息历史")
    rounds: int = Field(..., description="当前辩论轮次")
    requires_human_input: bool = Field(default=False, description="是否需要人类输入")
    pending_input_role: Optional[str] = Field(None, description="等待哪个角色的输入")


class EndSessionResponse(BaseModel):
    """结束会话响应"""
    status: str = Field(..., description="结束状态")
    final_phase: str = Field(..., description="最终阶段")
    total_rounds: int = Field(..., description="总辩论轮次")


class HumanInputRequest(BaseModel):
    """人类输入请求"""
    content: str = Field(..., description="人类输入的内容")
    role: CourtRole = Field(..., description="输入的角色")


class WebSocketMessage(BaseModel):
    """WebSocket消息基础模型"""
    event: str = Field(..., description="事件类型")
    data: dict = Field(..., description="事件数据")
