from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only, joinedload, contains_eager
from app.models import Project, ProjectUser, Meeting, MeetingUser, FlowyUser, SummaryLog, Feedback, TaskAssignLog
from app.schemas.project import ProjectCreate
from sqlalchemy.sql import label
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict
import uuid

feedbacktype_ids = [
    UUID("e508d0b2-1bfd-42a2-9687-1ae6cd36c648"),
    UUID("6cb5e437-bc6b-4a37-a3c4-473d9c0bebe2"),
    UUID("ab5a65c6-31a4-493b-93ff-c47e00925d17"),
    UUID("0a5a835d-53d0-43a6-b821-7c36f603a071"),
    UUID("73c0624b-e1af-4a2b-8e54-c1f8f7dab827"),
]

async def get_project_users_with_projects_by_user_id(
    db: AsyncSession, user_id: UUID
) -> list[dict]:
    """
    특정 user_id를 가진 사용자가 참여한 프로젝트들과 각 프로젝트의 참여자 수를 반환합니다.
    """
    # 사용자가 참여한 프로젝트들을 조회
    stmt = (
        select(ProjectUser)
        .where(ProjectUser.user_id == user_id)
        .options(selectinload(ProjectUser.project))
    )
    result = await db.execute(stmt)
    project_users = result.scalars().all()
    
    # 각 프로젝트별로 참여자 수를 계산
    project_data = []
    seen_projects = set()
    
    for project_user in project_users:
        project_id = project_user.project_id
        
        # 이미 처리한 프로젝트는 스킵
        if project_id in seen_projects:
            continue
        
        seen_projects.add(project_id)
        
        # 해당 프로젝트의 전체 참여자 수 조회
        count_stmt = select(func.count(ProjectUser.user_id)).where(
            ProjectUser.project_id == project_id
        )
        count_result = await db.execute(count_stmt)
        user_count = count_result.scalar()
        
        # 프로젝트 데이터에 참여자 수 추가
        project_data.append({
            "project_user_id": project_user.project_user_id,
            "user_id": project_user.user_id,
            "project_id": project_user.project_id,
            "role_id": project_user.role_id,
            "project": project_user.project,
            "user_count": user_count
        })
    
    return project_data

async def get_meetings_with_users_by_project_id(
    db: AsyncSession, project_id: UUID
) -> list[dict]:
    """
    프로젝트의 실제 진행된 회의와 분석 상태를 반환합니다.
    거부된 예정 회의는 제외합니다.
    """
    stmt = (
        select(Meeting)
        .where(
            Meeting.project_id == project_id,
            ~Meeting.meeting_title.like("[거부됨]%")  # 거부된 예정 회의 제외
        )
        .options(
            selectinload(Meeting.meeting_users).selectinload(MeetingUser.user),
            selectinload(Meeting.summary_logs),
            selectinload(Meeting.feedbacks)
        )
        .order_by(desc(Meeting.meeting_date))
    )
    result = await db.execute(stmt)
    meetings = result.scalars().all()
    
    # 각 회의에 분석 상태 추가
    meeting_data = []
    for meeting in meetings:
        # 분석 상태 판단
        has_audio_file = meeting.meeting_audio_path != "app/none"
        has_summary = len(meeting.summary_logs) > 0
        has_feedback = any(
            feedback.feedbacktype_id in feedbacktype_ids 
            for feedback in meeting.feedbacks
        )
        
        # 상태 결정 로직
        if not has_audio_file:
            analysis_status = "pending"  # 분석전 (예정 회의, 음성파일 미업로드)
        elif has_summary and has_feedback:
            analysis_status = "completed"  # 분석완료
        else:
            analysis_status = "analyzing"  # 분석중 (음성파일 있지만 분석 미완료)
        
        meeting_data.append({
            "meeting_id": meeting.meeting_id,
            "meeting_title": meeting.meeting_title,
            "meeting_agenda": meeting.meeting_agenda,
            "meeting_date": meeting.meeting_date,
            "project_id": meeting.project_id,
            "meeting_users": meeting.meeting_users,
            "analysis_status": analysis_status
        })
    
    return meeting_data

async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession
):
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)
    # 1. 프로젝트 생성
    new_project = Project(
        project_id=uuid.uuid4(),
        company_id=project_data.company_id,
        project_name=project_data.project_name,
        project_detail=project_data.project_detail,
        project_created_date=now,
        project_status=project_data.project_status,
    )
    db.add(new_project)
    await db.flush()  # project_id 필요하므로 flush로 먼저 반영

    # 2. 참여자 생성
    for user in project_data.project_users:
        project_user = ProjectUser(
            user_id=user.user_id,
            project_id=new_project.project_id,
            role_id=user.role_id,
        )
        db.add(project_user)

    await db.commit()
    return {"project_id": new_project.project_id}

# 회의 분석 결과
async def get_meeting_detail_with_project_and_users(
    db: AsyncSession, meeting_id: UUID
) -> Meeting | None:
    stmt = (
        select(Meeting)
        .where(Meeting.meeting_id == meeting_id)
        .options(
            load_only(
                Meeting.meeting_id,
                Meeting.meeting_title,
                Meeting.meeting_agenda,
                Meeting.meeting_date,
                Meeting.project_id
            ),
            selectinload(Meeting.project).load_only(
                Project.project_id,
                Project.project_name
            ),
            selectinload(Meeting.meeting_users)
                .selectinload(MeetingUser.user)
                .load_only(FlowyUser.user_id, FlowyUser.user_name),
        )
    )

    result = await db.execute(stmt)
    meeting = result.scalars().first()

    # ✅ 최신 summary_log 1개 따로 쿼리
    if meeting:
        # meeting.project_id로 ProjectUser 목록 조회
        project_users_stmt = select(ProjectUser).where(ProjectUser.project_id == meeting.project_id).options(selectinload(ProjectUser.user))
        project_users_result = await db.execute(project_users_stmt)
        project_users = project_users_result.scalars().all()
        setattr(meeting, "project_users", project_users)

        summary_stmt = (
            select(SummaryLog)
            .where(SummaryLog.meeting_id == meeting_id)
            .order_by(desc(SummaryLog.updated_summary_date))
            .limit(1)
        )
        summary_result = await db.execute(summary_stmt)
        summary_log = summary_result.scalars().first()

        feedback_stmt = (
            select(Feedback)
            .where(
                Feedback.meeting_id == meeting_id,
                Feedback.feedbacktype_id.in_(feedbacktype_ids)
            )
            .order_by(desc(Feedback.feedback_created_date))
        )
        feedback_result = await db.execute(feedback_stmt)
        feedback = feedback_result.scalars().all()

        task_assign_role_stmt = (
            select(TaskAssignLog)
            .where(TaskAssignLog.meeting_id == meeting_id)
            .order_by(desc(TaskAssignLog.updated_task_assign_date))
            .limit(1)
        )
        task_assign_role_result = await db.execute(task_assign_role_stmt)
        task_assign_role = task_assign_role_result.scalars().first()

        # meeting 객체에 직접 넣어줍니다. (필드가 없으면 수동으로 속성 추가)
        if summary_log:
            setattr(meeting, "summary_log", summary_log)
        if feedback:
            setattr(meeting, "feedback", feedback)
        if task_assign_role:
            setattr(meeting, "task_assign_role", task_assign_role)

    return meeting

# # 프로젝트 삭제 함수
# async def delete_project_by_id(db: AsyncSession, project_id: UUID) -> bool:
#     # 먼저 해당 프로젝트가 존재하는지 확인
#     stmt = select(Project).where(Project.project_id == project_id)
#     result = await db.execute(stmt)
#     project = result.scalars().first()

#     if not project:
#         return False  # 존재하지 않음

#     await db.delete(project)
#     await db.commit()
#     return True  # 삭제 성공

async def update_project_name_by_id(
    db: AsyncSession,
    project_id: UUID,
    project_name: str
) -> bool:
    # 해당 project_id로 프로젝트 검색
    stmt = select(Project).where(Project.project_id == project_id)
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        return False  # 프로젝트가 존재하지 않음

    # 프로젝트 이름 수정
    project.project_name = project_name
    await db.commit()
    return True  # 수정 성공

# 역할 분배 업데이트 
async def insert_task_assign_log(
    db: AsyncSession,
    meeting_id: UUID,
    updated_task_assign_contents: dict,
) -> bool:
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)

    new_log = TaskAssignLog(
        meeting_id=meeting_id,
        updated_task_assign_contents=updated_task_assign_contents,
        updated_task_assign_date=datetime.now()
    )
    
    db.add(new_log)
    try:
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        # 필요시 로그 출력 or 예외 처리
        return False

# 요약 로그 업데이트
async def insert_summary_log(
    db: AsyncSession,
    meeting_id: UUID,
    updated_summary_contents: dict,
) -> bool:
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)

    new_log = SummaryLog(
        meeting_id=meeting_id,
        updated_summary_contents=updated_summary_contents,
        updated_summary_date=now
    )
    
    db.add(new_log)
    try:
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        # 필요시 로그 출력 or 예외 처리
        return False

async def insert_summary_and_task_logs(
    db: AsyncSession,
    meeting_id: UUID,
    updated_summary_contents: dict,
    updated_task_assign_contents: dict
) -> bool:
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)

    summary_log = SummaryLog(
        meeting_id=meeting_id,
        updated_summary_contents=updated_summary_contents,
        updated_summary_date=now
    )

    task_log = TaskAssignLog(
        meeting_id=meeting_id,
        updated_task_assign_contents=updated_task_assign_contents,
        updated_task_assign_date=now
    )

    try:
        async with db.begin():  # 트랜잭션 시작
            db.add_all([summary_log, task_log])
        return True
    except Exception as e:
        await db.rollback()
        return False

async def update_project_with_users(
    db: AsyncSession,
    project_id: UUID,
    project_name: str,
    project_detail: str,
    new_users: List[Dict[str, UUID]],  # [{user_id, role_id}]
) -> bool:
    result = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result.scalars().first()
    if not project:
        return False

    project.project_name = project_name
    project.project_detail = project_detail

    result = await db.execute(
        select(ProjectUser).where(ProjectUser.project_id == project_id)
    )
    existing_users = result.scalars().all()

    existing_map = {str(u.user_id): u for u in existing_users}
    new_map = {str(u.user_id): u.role_id for u in new_users}

    # 삭제할 사용자
    for user_id_str in list(existing_map.keys()):
        if user_id_str not in new_map:
            await db.delete(existing_map[user_id_str])
    

    # 추가 또는 수정할 사용자
    for user_id_str, new_role_id in new_map.items():
        if user_id_str not in existing_map:
            new_project_user = ProjectUser(
                project_id=project_id,
                user_id=UUID(user_id_str),
                role_id=new_role_id,
            )
            db.add(new_project_user)
        else:
            existing_user = existing_map[user_id_str]
            if existing_user.role_id != new_role_id:
                existing_user.role_id = new_role_id

    await db.commit()
    return True
