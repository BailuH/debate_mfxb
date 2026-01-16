"""
Session Management API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ...schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionStatusResponse,
    EndSessionResponse,
    HumanInputRequest,
)
from ...services.court_service import court_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    创建新的法庭会话

    Args:
        request: 创建会话请求

    Returns:
        会话信息

    Raises:
        HTTPException: 创建失败时抛出500错误
    """
    try:
        evidence_list = []
        if request.case_evidence:
            evidence_list = [{"speaker": ev.speaker, "content": ev.content} for ev in request.case_evidence]

        session_id = await court_service.create_session(
            case_info=request.case_info,
            case_evidence=evidence_list,
            human_role=request.human_role,
        )

        session_data = await court_service.get_session(session_id)

        return CreateSessionResponse(
            session_id=session_id,
            current_phase=session_data["current_phase"],
            current_speaker=session_data["current_speaker"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(session_id: str):
    """
    获取会话状态和消息历史

    Args:
        session_id: 会话ID

    Returns:
        会话状态信息

    Raises:
        HTTPException: 会话不存在时抛出404错误
    """
    try:
        session_data = await court_service.get_session(session_id)
        return SessionStatusResponse(**session_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@router.delete("/{session_id}", response_model=EndSessionResponse)
async def end_session(session_id: str):
    """
    结束并清理会话

    Args:
        session_id: 会话ID

    Returns:
        结束信息

    Raises:
        HTTPException: 会话不存在时抛出404错误
    """
    try:
        session_data = await court_service.get_session(session_id)
        await court_service.cleanup_session(session_id)

        return EndSessionResponse(
            status="ended",
            final_phase=session_data["current_phase"],
            total_rounds=session_data["rounds"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"结束会话失败: {str(e)}")

