from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only, joinedload, contains_eager
from app.models import Project, ProjectUser, Meeting, MeetingUser, FlowyUser, SummaryLog, Feedback
from app.schemas.project import ProjectCreate
from sqlalchemy.sql import label
from uuid import UUID
from datetime import datetime
import uuid

async def get_project_users_with_projects_by_user_id(
    db: AsyncSession, user_id: UUID
) -> list[ProjectUser]:
    """
    특정 user_id를 가진 ProjectUser들을 조회하고, 각각의 관련된 Project도 함께 가져옵니다.
    """
    stmt = (
        select(ProjectUser)
        .where(ProjectUser.user_id == user_id)
        .options(selectinload(ProjectUser.project))  # Project를 eager load
    )
    result = await db.execute(stmt)
    project_users = result.scalars().all()  # 여기 추가
    return project_users  # 리스트가 반환됨

async def get_meetings_with_users_by_project_id(
    db: AsyncSession, project_id: UUID
) -> list[Meeting]:
    stmt = (
        select(Meeting)
        .where(Meeting.project_id == project_id)
        .options(
            selectinload(Meeting.meeting_users).selectinload(MeetingUser.user)  # 유저 정보까지
            # selectinload(Meeting.meeting_users).selectinload(MeetingUser.role)   # 역할 정보도 포함하고 싶다면
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession
):
    now = datetime.utcnow()
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
            .where(Feedback.meeting_id == meeting_id)
            .order_by(desc(Feedback.feedback_created_date))
            .limit(1)
        )
        feedback_result = await db.execute(feedback_stmt)
        feedback = feedback_result.scalars().first()

        # meeting 객체에 직접 넣어줍니다. (필드가 없으면 수동으로 속성 추가)
        if summary_log:
            setattr(meeting, "summary_log", summary_log)
        if feedback:
            setattr(meeting, "feedback", feedback)

    return meeting


# 프로젝트 삭제 함수
async def delete_project_by_id(db: AsyncSession, project_id: UUID) -> bool:
    # 먼저 해당 프로젝트가 존재하는지 확인
    stmt = select(Project).where(Project.project_id == project_id)
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        return False  # 존재하지 않음

    await db.delete(project)
    await db.commit()
    return True  # 삭제 성공

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
