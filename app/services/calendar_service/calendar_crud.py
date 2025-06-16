from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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