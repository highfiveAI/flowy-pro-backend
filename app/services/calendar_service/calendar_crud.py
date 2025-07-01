import json
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Calendar
from app.models.flowy_user import FlowyUser
from app.models.meeting import Meeting
from app.models.meeting_user import MeetingUser
from app.models.task_assign_log import TaskAssignLog


async def get_calendars_by_user_and_project(user_id: UUID, project_id: UUID, db: AsyncSession) -> List[Calendar]:
    result = await db.execute(
        select(Calendar).where(
            (Calendar.user_id == user_id) & (Calendar.project_id == project_id)
        )
    )
    return result.scalars().all()


async def get_calendars_by_user_and_project_filtered(user_id: UUID, project_id: UUID, db: AsyncSession) -> List[Calendar]:
    """
    사용자와 프로젝트별 캘린더 조회 (거부된 예정 회의 제외)
    """
    result = await db.execute(
        select(Calendar).where(
            (Calendar.user_id == user_id) & 
            (Calendar.project_id == project_id) &
            (Calendar.status != 'rejected')  # 거부된 예정 회의는 캘린더에 표시하지 않음
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
    updated_at: datetime = None,
    status: str = "active"
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
        updated_at=updated_at or now,
        status=status
    )
    db.add(calendar)
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def insert_calendar_from_task(db: AsyncSession, task_assign_log: TaskAssignLog) -> List[Calendar]:
    """
    task_assign_log에 기록된 할 일 목록을 기반으로 캘린더에 새 일정을 추가합니다.
    """
    meeting_id = task_assign_log.meeting_id
    
    if not task_assign_log.updated_task_assign_contents:
        return []

    try:
        if isinstance(task_assign_log.updated_task_assign_contents, str):
            assigned_data = json.loads(task_assign_log.updated_task_assign_contents)
        else:
            assigned_data = task_assign_log.updated_task_assign_contents
        
        assigned_todos = assigned_data.get("assigned_todos", [])
    except (json.JSONDecodeError, AttributeError):
        return []

    meeting_result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        return []
    project_id = meeting.project_id

    participant_ids_result = await db.execute(select(MeetingUser.user_id).where(MeetingUser.meeting_id == meeting_id))
    participant_user_ids = participant_ids_result.scalars().all()

    if not participant_user_ids:
        return []

    users_result = await db.execute(select(FlowyUser).where(FlowyUser.user_id.in_(participant_user_ids)))
    participants = users_result.scalars().all()
    assignee_to_user_id = {user.user_name: user.user_id for user in participants}

    new_calendar_entries = []
    
    for todo in assigned_todos:
        assignee_name = todo.get("assignee")

        if assignee_name in ["미지정", "미할당"]:
            continue

        user_id = assignee_to_user_id.get(assignee_name)
        if not user_id:
            continue

        title = todo.get("action")
        if not title:
            continue

        schedule_str = todo.get("schedule")
        start_date = None
        end_date = None
        
        # '언급 없음'이 아닌 경우 날짜를 파싱합니다.
        if schedule_str and schedule_str != "언급 없음":
            # 날짜 형식 "YYYY.MM.DD(요일)" 에서 날짜 부분만 추출합니다.
            date_match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", schedule_str)
            if date_match:
                year, month, day = map(int, date_match.groups())
                start_date = datetime(year, month, day)
                end_date = datetime(year, month, day)
        else:
            start_date = datetime.now()
        
        new_entry = Calendar(
            user_id=user_id,
            project_id=project_id,
            title=title,
            start=start_date,
            end=end_date,
            calendar_type="todo",
            created_at=datetime.utcnow(),
            completed=False
        )
        db.add(new_entry)
        new_calendar_entries.append(new_entry)

    try:
        await db.commit()
        for entry in new_calendar_entries:
            await db.refresh(entry)
    except Exception as e:
        await db.rollback()
        print(f"Calendar 일정 추가 중 오류 발생: {e}")
        return []

    return new_calendar_entries


async def update_calendar_from_todos(db: AsyncSession, meeting_id: UUID, updated_task_assign_contents: dict) -> List[Calendar]:
    """
    할 일 목록을 받아서 캘린더를 동기화(업데이트)합니다.
    - 동일한 일정(같은 user_id, project_id, title, start, end, calendar_type='todo')이 있으면 insert하지 않음
    - task가 다른 사람에게 옮겨진 경우 기존 일정을 삭제하고 새 담당자에게 등록
    """
    if isinstance(updated_task_assign_contents, str):
        assigned_data = json.loads(updated_task_assign_contents)
    else:
        assigned_data = updated_task_assign_contents
    assigned_todos = assigned_data.get("assigned_todos", [])

    meeting_result = await db.execute(select(Meeting).where(Meeting.meeting_id == meeting_id))
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        return []
    project_id = meeting.project_id

    participant_ids_result = await db.execute(select(MeetingUser.user_id).where(MeetingUser.meeting_id == meeting_id))
    participant_user_ids = participant_ids_result.scalars().all()
    users_result = await db.execute(select(FlowyUser).where(FlowyUser.user_id.in_(participant_user_ids)))
    participants = users_result.scalars().all()
    assignee_to_user_id = {user.user_name: user.user_id for user in participants}

    existing_calendars_result = await db.execute(
        select(Calendar).where(
            Calendar.project_id == project_id,
            Calendar.calendar_type == "todo"
        )
    )
    existing_calendars = existing_calendars_result.scalars().all()

    new_calendar_entries = []
    for todo in assigned_todos:
        assignee_name = todo.get("assignee")
        if assignee_name in ["미지정", "미할당"]:
            continue
        user_id = assignee_to_user_id.get(assignee_name)
        if not user_id:
            continue
        title = todo.get("action")
        if not title:
            continue
        schedule_str = todo.get("schedule")
        start_date = None
        end_date = None
        if schedule_str and schedule_str != "언급 없음":
            date_match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", schedule_str)
            if date_match:
                year, month, day = map(int, date_match.groups())
                start_date = datetime(year, month, day)
                end_date = datetime(year, month, day)
        else:
            start_date = datetime.now()

        found = None
        for cal in existing_calendars:
            if (
                cal.title == title and
                cal.start == start_date and
                cal.end == end_date and
                cal.project_id == project_id and
                cal.calendar_type == "todo"
            ):
                if cal.user_id == user_id:
                    found = cal
                    break
                else:   
                    await db.delete(cal)
                    await db.commit()
        if found:
            continue
        new_entry = Calendar(
            user_id=user_id,
            project_id=project_id,
            title=title,
            start=start_date,
            end=end_date,
            calendar_type="todo",
            created_at=datetime.utcnow(),
            completed=False
        )
        db.add(new_entry)
        new_calendar_entries.append(new_entry)
    try:
        await db.commit()
        for entry in new_calendar_entries:
            await db.refresh(entry)
    except Exception as e:
        await db.rollback()
        print(f"[update_calendar_from_todos] 일정 동기화 중 오류: {e}")
        return []
    return new_calendar_entries