from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.models.calendar import Calendar
from typing import List, Optional
from uuid import UUID
from datetime import datetime

async def get_calendars_by_user_and_project(user_id: UUID, project_id: UUID, db: AsyncSession) -> List[Calendar]:
    result = await db.execute(
        select(Calendar).where(
            (Calendar.user_id == user_id) & (Calendar.project_id == project_id)
        )
    )
    return result.scalars().all()

async def update_calendar(
    calendar_id: UUID,
    completed: bool,
    db: AsyncSession
) -> Optional[Calendar]:
    result = await db.execute(
        select(Calendar).where(Calendar.calendar_id == calendar_id)
    )
    calendar = result.scalar_one_or_none()
    if not calendar:
        return None
    calendar.completed = completed
    calendar.updated_at = datetime.now()
    await db.commit()
    await db.refresh(calendar)
    return calendar

async def insert_meeting_calendar(
    db: AsyncSession,
    user_id: UUID,
    project_id: UUID,
    title: str,
    start: datetime,
    calendar_type: str = "meeting",
    completed: bool = False,
    created_at: datetime = None,
    updated_at: datetime = None
):
    now = datetime.utcnow()
    calendar = Calendar(
        user_id=user_id,
        project_id=project_id,
        title=title,
        start=start,
        end=None,
        calendar_type=calendar_type,
        completed=completed,
        created_at=created_at or now,
        updated_at=updated_at or now
    )
    db.add(calendar)
    await db.commit()
    await db.refresh(calendar)
    return calendar 