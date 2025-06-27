from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, exists, String
from typing import List
from uuid import UUID
import datetime

from app.db.db_session import get_db_session
from app.services.signup_service.auth import check_access_token
from app.models.meeting import Meeting
from app.models.meeting_user import MeetingUser
from app.models.calendar import Calendar
from app.models.flowy_user import FlowyUser
from app.schemas.meeting import PendingMeetingResponse, AcceptMeetingRequest, RejectMeetingRequest
from app.schemas.signup_info import TokenPayload

router = APIRouter()

# PO 권한 체크 함수
async def check_po_permission(db: AsyncSession, user_id: UUID, meeting_id: UUID) -> bool:
    """사용자가 해당 회의의 PO(호스트)인지 확인"""
    HOST_ROLE_ID = "20ea65e2-d3b7-4adb-a8ce-9e67a2f21999"
    
    stmt = select(MeetingUser).where(
        and_(
            MeetingUser.user_id == user_id,
            MeetingUser.meeting_id == meeting_id,
            MeetingUser.role_id == HOST_ROLE_ID
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None

@router.get("/pending", response_model=List[PendingMeetingResponse])
async def get_pending_meetings(
    request: Request,
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: TokenPayload = Depends(check_access_token)
):
    """
    1️⃣ 확인 대기 중인 예정 회의 조회 API
    
    현재 meeting_id와 같은 프로젝트에서
    - meeting_audio_path = 'app/none' (Agent 생성)
    - 현재 사용자가 PO 권한
    - calendar 테이블에 agent_meeting_id가 없는 것 조회
    """
    try:
        user_id = UUID(current_user.id)
        
        # 현재 회의의 프로젝트 ID 조회
        current_meeting_stmt = select(Meeting.project_id).where(Meeting.meeting_id == meeting_id)
        current_meeting_result = await db.execute(current_meeting_stmt)
        current_meeting = current_meeting_result.scalar_one_or_none()
        
        if not current_meeting:
            raise HTTPException(status_code=404, detail="현재 회의를 찾을 수 없습니다.")
        
        project_id = current_meeting
        
        # PO 권한 체크
        is_po = await check_po_permission(db, user_id, meeting_id)
        if not is_po:
            raise HTTPException(status_code=403, detail="PO 권한이 필요합니다.")
        
        # 확인 대기 중인 예정 회의 조회
        # 1. Agent가 생성한 회의 (meeting_audio_path = 'app/none')
        # 2. 현재 사용자가 PO인 회의만
        # 3. 아직 캘린더에 처리되지 않은 것 (calendar.agent_meeting_id로 현재 회의 ID가 등록되지 않은 것)
        HOST_ROLE_ID = "20ea65e2-d3b7-4adb-a8ce-9e67a2f21999"
        
        stmt = select(Meeting).join(
            MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id
        ).where(
            and_(
                Meeting.meeting_audio_path == 'app/none',
                Meeting.project_id == project_id,  # 같은 프로젝트의 Agent 생성 회의
                MeetingUser.user_id == user_id,
                MeetingUser.role_id == HOST_ROLE_ID,
                ~exists().where(Calendar.agent_meeting_id == str(meeting_id))  # 현재 회의 ID로 처리되었는지 확인
            )
        )
        
        result = await db.execute(stmt)
        pending_meetings = result.scalars().all()
        
        response_list = []
        for meeting in pending_meetings:
            response_list.append(PendingMeetingResponse(
                meeting_id=meeting.meeting_id,
                meeting_title=meeting.meeting_title,
                meeting_date=meeting.meeting_date,
                meeting_agenda=meeting.meeting_agenda,
                project_id=meeting.project_id
            ))
        return response_list
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 UUID 형식: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/{meeting_id}/accept")
async def accept_meeting(
    request: Request,
    meeting_id: UUID,
    accept_request: AcceptMeetingRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: TokenPayload = Depends(check_access_token)
):
    """
    2️⃣ 예정 회의 캘린더 등록 API
    
    PO 권한 체크 후 calendar 테이블에 INSERT
    """
    try:
        user_id = UUID(current_user.id)
        agent_meeting_id = accept_request.agent_meeting_id
        
        # Agent 회의 정보 조회
        stmt = select(Meeting).where(Meeting.meeting_id == agent_meeting_id)
        result = await db.execute(stmt)
        agent_meeting = result.scalar_one_or_none()
        
        if not agent_meeting:
            raise HTTPException(status_code=404, detail="예정 회의를 찾을 수 없습니다.")
        
        # PO 권한 체크 (원본 회의 ID로 체크)
        is_po = await check_po_permission(db, user_id, meeting_id)
        if not is_po:
            raise HTTPException(status_code=403, detail="PO 권한이 필요합니다.")
        
        # 이미 처리된 회의인지 확인 (원본 회의 ID로 확인)
        existing_calendar_stmt = select(Calendar).where(
            Calendar.agent_meeting_id == str(meeting_id)
        )
        existing_result = await db.execute(existing_calendar_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이미 처리된 예정 회의입니다.")
        
        # Calendar 테이블에 INSERT
        # timezone 정보 제거 (데이터베이스가 TIMESTAMP WITHOUT TIME ZONE 사용)
        meeting_start = accept_request.meeting_date or agent_meeting.meeting_date
        if meeting_start.tzinfo is not None:
            meeting_start = meeting_start.replace(tzinfo=None)
            
        calendar_entry = Calendar(
            user_id=user_id,
            project_id=agent_meeting.project_id,
            title=accept_request.meeting_title or agent_meeting.meeting_title,
            start=meeting_start,
            end=None,  # 종료 시간은 선택적
            calendar_type="meeting",
            completed=False,
            created_at=datetime.datetime.now(),
            agent_meeting_id=str(meeting_id),  # 원본 회의 ID 저장
            # status="active"
        )
        
        db.add(calendar_entry)
        await db.commit()
        await db.refresh(calendar_entry)
        
        return {
            "success": True,
            "message": "예정 회의가 캘린더에 등록되었습니다.",
            "calendar_id": calendar_entry.calendar_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 UUID 형식: {str(e)}")
    except Exception as e:
        await db.rollback()
        print(f"[accept_meeting] 오류 발생: {str(e)}", flush=True)
        print(f"[accept_meeting] 오류 타입: {type(e)}", flush=True)
        import traceback
        print(f"[accept_meeting] 스택 트레이스: {traceback.format_exc()}", flush=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.post("/{meeting_id}/reject")
async def reject_meeting(
    request: Request,
    meeting_id: UUID,
    reject_request: RejectMeetingRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: TokenPayload = Depends(check_access_token)
):
    """
    3️⃣ 예정 회의 거부 처리 API
    
    PO 권한 체크 후 calendar 테이블에 거부 기록 INSERT
    """
    try:
        user_id = UUID(current_user.id)
        agent_meeting_id = reject_request.agent_meeting_id
        
        # Agent 회의 정보 조회
        stmt = select(Meeting).where(Meeting.meeting_id == agent_meeting_id)
        result = await db.execute(stmt)
        agent_meeting = result.scalar_one_or_none()
        
        if not agent_meeting:
            raise HTTPException(status_code=404, detail="예정 회의를 찾을 수 없습니다.")
        
        # PO 권한 체크 (원본 회의 ID로 체크)
        is_po = await check_po_permission(db, user_id, meeting_id)
        if not is_po:
            raise HTTPException(status_code=403, detail="PO 권한이 필요합니다.")
        
        # 이미 처리된 회의인지 확인 (원본 회의 ID로 확인)
        existing_calendar_stmt = select(Calendar).where(
            Calendar.agent_meeting_id == str(meeting_id)
        )
        existing_result = await db.execute(existing_calendar_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이미 처리된 예정 회의입니다.")
        
        # Calendar 테이블에 거부 기록 INSERT
        # timezone 정보 제거 (데이터베이스가 TIMESTAMP WITHOUT TIME ZONE 사용)
        meeting_start = agent_meeting.meeting_date
        if meeting_start.tzinfo is not None:
            meeting_start = meeting_start.replace(tzinfo=None)
            
        calendar_entry = Calendar(
            user_id=user_id,
            project_id=agent_meeting.project_id,
            title=f"[거부됨] {agent_meeting.meeting_title}",
            start=meeting_start,
            end=None,
            calendar_type="meeting",
            completed=False,
            created_at=datetime.datetime.now(),
            agent_meeting_id=str(meeting_id),  # 원본 회의 ID 저장
            status="rejected"
        )
        
        db.add(calendar_entry)
        await db.commit()
        await db.refresh(calendar_entry)
        
        return {
            "success": True,
            "message": "예정 회의가 거부되었습니다.",
            "calendar_id": calendar_entry.calendar_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 UUID 형식: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}") 