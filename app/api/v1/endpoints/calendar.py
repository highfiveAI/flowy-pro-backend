from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session
from app.services.calendar_service.calendar_crud import get_calendars_by_user_and_project, update_calendar
from app.schemas.calendar import CalendarResponse
from typing import List
from uuid import UUID
from datetime import datetime

router = APIRouter()

@router.get("/{user_id}/{project_id}", response_model=List[CalendarResponse])
async def read_calendars_by_user_and_project(user_id: UUID, project_id: UUID, db: AsyncSession = Depends(get_db_session)):
    calendars = await get_calendars_by_user_and_project(user_id, project_id, db)
    return calendars

@router.put("/{calendar_id}", response_model=CalendarResponse)
async def edit_calendar(
    calendar_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db_session)
):
    calendar = await update_calendar(
        calendar_id=calendar_id,
        completed=body["completed"],
        db=db
    )
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar 