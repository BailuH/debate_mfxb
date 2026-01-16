"""
Pydantic models for message handling
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WebSocketEvent(BaseModel):
    """WebSocket事件基础模型"""
    event: str = Field(..., description="事件类型")
    data: dict = Field(..., description="事件数据")


class DebateUpdateData(BaseModel):
    """辩论更新事件数据"""
    new_message: dict = Field(..., description="新消息")
    speaker_changed: bool = Field(..., description="发言人是否改变")
    new_speaker: Optional[str] = Field(None, description="新的发言人")
    phase_changed: bool = Field(..., description="阶段是否改变")
    current_phase: str = Field(..., description="当前阶段")
    round: int = Field(..., description="当前轮次")


class HumanInputRequiredData(BaseModel):
    """需要人类输入事件数据"""
    required_role: str = Field(..., description="需要哪个角色输入")
    prompt: str = Field(..., description="提示信息")
    timeout_seconds: Optional[int] = Field(None, description="超时时间（秒）")


class HumanInputData(BaseModel):
    """人类输入数据"""
    content: str = Field(..., description="输入内容")
    role: str = Field(..., description="角色")


class DebateEndedData(BaseModel):
    """辩论结束事件数据"""
    final_messages: list = Field(..., description="最终消息列表")
    total_rounds: int = Field(..., description="总轮次")
    final_phase: str = Field(..., description="最终阶段")
