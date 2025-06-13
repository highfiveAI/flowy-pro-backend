from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Project, ProjectUser, Meeting
from uuid import UUID

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