from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4, UUID
from datetime import datetime
from app.models.meeting import Meeting  # 실제 모델 경로에 맞게 수정
from app.models.project_user import ProjectUser
from app.models.flowy_user import FlowyUser
from app.models.meeting_user import MeetingUser
from app.models.project import Project
from typing import List, Dict, Optional

#회의 참석자 저장 함수
async def insert_meeting_user(db: AsyncSession, meeting_id: str, user_id: str, role_id: str):
    meeting_participant = MeetingUser(
        meeting_id=meeting_id,
        user_id=user_id,
        role_id=role_id
    )
    db.add(meeting_participant)
    await db.commit()
    await db.refresh(meeting_participant)
    return meeting_participant


# meeting 저장 함수
async def insert_meeting(
    db: AsyncSession,
    project_id: str,
    meeting_title: str,
    meeting_agenda: str,
    meeting_date: datetime,
    meeting_audio_path: str = None
):
    meeting = Meeting(
        meeting_id=str(uuid4()),
        project_id=project_id,
        meeting_title=meeting_title,
        meeting_agenda=meeting_agenda,
        meeting_date=meeting_date,
        meeting_audio_path=meeting_audio_path
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting 


# summary_log 저장 함수
async def insert_summary_log(db: AsyncSession, summary_contents: dict, meeting_id: str):
    # print(f"insert_summary_log called! summary_contents={summary_contents}", flush=True)
    # print(f"summary_contents type: {type(summary_contents)}", flush=True)
    # print(f"summary_contents keys: {summary_contents.keys() if isinstance(summary_contents, dict) else 'not a dict'}", flush=True)
    from app.models import SummaryLog
    
    # agent_output 직접 추출
    summary_agent_output = summary_contents.get("agent_output", "")
    # print(f"extracted summary_agent_output={summary_agent_output}", flush=True)
    
    summary_log = SummaryLog(
        summary_log_id=str(uuid4()),
        updated_summary_contents=summary_agent_output,
        updated_summary_date=datetime.now(),
        meeting_id=meeting_id
    )
    db.add(summary_log)
    await db.commit()
    await db.refresh(summary_log)
    return summary_log

# 역할분담 로그 저장 함수
async def insert_task_assign_log(db: AsyncSession, assigned_roles: dict, meeting_id: str):
    # print(f"insert_task_assign_log called! assigned_roles={assigned_roles}", flush=True)
    # print(f"assigned_roles type: {type(assigned_roles)}", flush=True)
    # print(f"assigned_roles keys: {assigned_roles.keys() if isinstance(assigned_roles, dict) else 'not a dict'}", flush=True)
    from app.models import TaskAssignLog
    
    # assigned_roles.assigned_roles.assigned_todos 추출
    assigned_roles_data = assigned_roles.get("assigned_roles", {})
    # print(f"assigned_roles_data: {assigned_roles_data}", flush=True)
    assigned_todos = assigned_roles_data.get("assigned_todos", [])
    # print(f"extracted assigned_todos={assigned_todos}", flush=True)
    
    task_assign_log = TaskAssignLog(
        task_assign_log_id=str(uuid4()),
        updated_task_assign_contents={"assigned_todos": assigned_todos},
        updated_task_assign_date=datetime.now(),
        meeting_id=meeting_id
    )
    db.add(task_assign_log)
    await db.commit()
    await db.refresh(task_assign_log)
    return task_assign_log

# feedbacktype_id 매핑 함수
async def get_feedback_type_map(db: AsyncSession):
    from app.models import FeedbackType
    result = await db.execute(select(FeedbackType))
    rows = result.scalars().all()
    return {row.feedbacktype_name: row.feedbacktype_id for row in rows}

# 피드백 저장 함수
async def insert_feedback_log(db: AsyncSession, feedback_detail: dict, feedbacktype_id: str, meeting_id: str):
    print(f"insert_feedback_log called! feedback_detail={feedback_detail}", flush=True)
    print(f"feedback_detail type: {type(feedback_detail)}", flush=True)
    print(f"feedback_detail keys: {feedback_detail.keys() if isinstance(feedback_detail, dict) else 'not a dict'}", flush=True)
    from app.models import Feedback
    feedback = Feedback(
        feedback_id=str(uuid4()),
        feedbacktype_id=feedbacktype_id,
        feedback_detail=feedback_detail,
        feedback_created_date=datetime.now(),
        meeting_id=meeting_id
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback 

# 프로젝트 사용자 목록 불러오기
async def get_conference_list(db: AsyncSession, project_id: str) -> List[Dict]:
    stmt = select(
        FlowyUser.user_id,
        FlowyUser.user_name,
        FlowyUser.user_email,
        FlowyUser.user_phonenum,
        FlowyUser.user_position_id,
        FlowyUser.user_jobname,
        ProjectUser.role_id
    ).join(
        ProjectUser,
        FlowyUser.user_id == ProjectUser.user_id
    ).where(
        ProjectUser.project_id == project_id
    )
    
    result = await db.execute(stmt)
    users = result.all()
    
    return [
        {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_email": user.user_email,
            "user_phonenum": user.user_phonenum,
            "user_position_id": user.user_position_id,
            "user_jobname": user.user_jobname,
            "role_id": user.role_id
        }
        for user in users
    ]

# 프롬프트 로그 저장용 에이전트 유형 매핑 함수 및 insert 함수
async def get_agent_type_map():
    return {
        '요약': 'summary',
        '검색': 'search',
        '문서': 'docs',  # 필요시 추가
    }

# 프롬프트 로그 저장 함수
async def insert_prompt_log(db: AsyncSession, meeting_id: str, agent_type: str, prompt_output: str, prompt_input_date: datetime, prompt_output_date: datetime):
    from app.models import PromptLog
    
    # meeting_id를 UUID로 변환
    meeting_uuid = UUID(meeting_id) if isinstance(meeting_id, str) else meeting_id
    
    prompt_log = PromptLog(
        # prompt_id는 자동 생성되므로 제거
        prompt_meeting_id=meeting_uuid,
        agent_type=agent_type,
        prompt_output=prompt_output,
        prompt_input_date=prompt_input_date,
        prompt_output_date=prompt_output_date
    )
    db.add(prompt_log)
    await db.commit()
    await db.refresh(prompt_log)
    return prompt_log

# 프롬프트 로그 조회 함수
async def get_prompt_logs_by_meeting(db: AsyncSession, meeting_id: str, agent_type: Optional[str] = None):
    """
    회의 ID로 프롬프트 로그 조회
    
    Args:
        db: 데이터베이스 세션
        meeting_id: 회의 ID
        agent_type: 에이전트 타입 (선택적, 'search', 'summary', 'docs')
    
    Returns:
        프롬프트 로그 리스트
    """
    from app.models import PromptLog
    
    # meeting_id를 UUID로 변환
    meeting_uuid = UUID(meeting_id) if isinstance(meeting_id, str) else meeting_id
    
    stmt = select(PromptLog).where(PromptLog.prompt_meeting_id == meeting_uuid)
    
    if agent_type:
        stmt = stmt.where(PromptLog.agent_type == agent_type)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [
        {
            "prompt_id": str(log.prompt_id),
            "agent_type": log.agent_type,
            "prompt_output": log.prompt_output,
            "prompt_input_date": log.prompt_input_date,
            "prompt_output_date": log.prompt_output_date
        }
        for log in logs
    ]

# 모든 프롬프트 로그 조회 함수
async def get_all_prompt_logs(db: AsyncSession, agent_type: Optional[str] = None):
    """
    모든 프롬프트 로그 조회
    
    Args:
        db: 데이터베이스 세션
        agent_type: 에이전트 타입 (선택적)
    
    Returns:
        프롬프트 로그 리스트
    """
    from app.models import PromptLog
    
    stmt = select(PromptLog)
    
    if agent_type:
        stmt = stmt.where(PromptLog.agent_type == agent_type)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [
        {
            "prompt_id": str(log.prompt_id),
            "meeting_id": str(log.prompt_meeting_id),
            "agent_type": log.agent_type,
            "prompt_output": log.prompt_output,
            "prompt_input_date": log.prompt_input_date,
            "prompt_output_date": log.prompt_output_date
        }
        for log in logs
    ]

# 프로젝트 회의 목록 조회
async def get_project_meetings(db: AsyncSession, project_id: str):
    stmt = (
        select(
            Meeting.meeting_id,
            Meeting.meeting_title,
            Meeting.meeting_date,
            Meeting.meeting_agenda,
            Project.project_name
        )
        .join(Project, Meeting.project_id == Project.project_id)
        .where(Project.project_id == project_id)
    )
    result = await db.execute(stmt)
    meetings = result.all()
    return meetings

async def get_role_id_by_user_and_project(db: AsyncSession, user_id: str, project_id: str) -> str:
    stmt = select(ProjectUser.role_id).where(
        ProjectUser.user_id == user_id,
        ProjectUser.project_id == project_id
    )
    result = await db.execute(stmt)
    role_id = result.scalar_one_or_none()
    return str(role_id) if role_id else None

async def update_meeting(
    db: AsyncSession,
    meeting_id: str,
    meeting_title: str,
    meeting_agenda: str,
    meeting_date: datetime,
    meeting_audio_path: str = None
):
    result = await db.execute(
        select(Meeting).where(Meeting.meeting_id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        return None
    meeting.meeting_title = meeting_title
    meeting.meeting_agenda = meeting_agenda
    meeting.meeting_date = meeting_date
    meeting.meeting_audio_path = meeting_audio_path
    await db.commit()
    await db.refresh(meeting)
    return meeting

async def update_meeting_user(
    db: AsyncSession,
    meeting_user_id: str,
    role_id: str
):
    result = await db.execute(
        select(MeetingUser).where(MeetingUser.meeting_user_id == meeting_user_id)
    )
    meeting_user = result.scalar_one_or_none()
    if not meeting_user:
        return None
    meeting_user.role_id = role_id
    await db.commit()
    await db.refresh(meeting_user)
    return meeting_user