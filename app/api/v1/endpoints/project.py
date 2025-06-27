from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session
from app.crud.crud_user import get_all_users
from app.schemas.signup_info import TokenPayload
from app.schemas.project import ProjectCreate, ProjectNameUpdate, TaskAssignLogCreate, SummaryLogCreate, ProjectUpdateRequestBody, SummaryAndTaskRequest, MeetingCreateRequest
from app.services.signup_service.auth import check_access_token
from app.crud.crud_project import get_project_users_with_projects_by_user_id, get_meetings_with_users_by_project_id, create_project, get_meeting_detail_with_project_and_users, delete_project_by_id, update_project_name_by_id, insert_task_assign_log, insert_summary_log, update_project_with_users, insert_summary_and_task_logs
from uuid import UUID
import traceback
from fastapi.responses import JSONResponse
from app.services.calendar_service.calendar_crud import update_calendar_from_todos, insert_meeting_calendar
from app.crud.crud_meeting import insert_meeting, insert_meeting_user, get_role_id_by_user_and_project
from app.models.flowy_user import FlowyUser
from datetime import datetime

router = APIRouter()


@router.post("")
async def create_project_api(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        result = await create_project(project_data, db)
        return result
    except Exception as e:
    # 전체 traceback 문자열로 출력
        traceback_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        print("🔥 서버 에러:", traceback_str)  # 콘솔에 출력

        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": traceback_str}
        )


@router.get("/meta")
async def list_users(token_user = Depends(check_access_token), db: AsyncSession = Depends(get_db_session)):
    users = await get_all_users(token_user, db)
    return users

@router.get("/user_id/{user_id}")
async def read_user_projects(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    projects = await get_project_users_with_projects_by_user_id(db, user_id)
    return projects

@router.get("/meeting/{project_id}")
async def read_meetings_with_users(project_id: UUID, db: AsyncSession = Depends(get_db_session)):
    meetings = await get_meetings_with_users_by_project_id(db, project_id)
    return meetings

@router.get("/meeting/result/{meeting_id}")
async def meetings_with_result(meeting_id: UUID ,db: AsyncSession = Depends(get_db_session)):
    meetings = await get_meeting_detail_with_project_and_users(db, meeting_id)
    return meetings

@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db_session)):
    deleted = await delete_project_by_id(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}

@router.put("/{project_id}")
async def update_project_name(
    project_id: UUID,
    data: ProjectNameUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    updated = await update_project_name_by_id(db, project_id, data.project_name)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project name updated successfully"}

@router.post("/update_todos")
async def create_task_assign_log(
    log_data: TaskAssignLogCreate,
    db: AsyncSession = Depends(get_db_session)
):
    success = await insert_task_assign_log(
        db=db,
        meeting_id=log_data.meeting_id,
        updated_task_assign_contents=log_data.updated_task_assign_contents
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create task assign log")
    return {"message": "Task assign log created successfully"}

@router.post("/update_summary")
async def create_summary_log(
    log_data: SummaryLogCreate,
    db: AsyncSession = Depends(get_db_session)
):
    success = await insert_summary_log(
        db=db,
        meeting_id=log_data.meeting_id,
        updated_summary_contents=log_data.updated_summary_contents
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create task assign log")
    return {"message": "Task assign log created successfully"}

@router.post("/update_summary_task")
async def create_summary_and_task(
    data: SummaryAndTaskRequest,  # pydantic 모델
    db: AsyncSession = Depends(get_db_session)
):
    success = await insert_summary_and_task_logs(
        db,
        meeting_id=data.meeting_id,
        updated_summary_contents=data.updated_summary_contents,
        updated_task_assign_contents=data.updated_task_assign_contents
    )
    
    calendar_result = await update_calendar_from_todos(
        db=db,
        meeting_id=data.meeting_id,
        updated_task_assign_contents=data.updated_task_assign_contents
    )

    if not success:
        raise HTTPException(status_code=500, detail="저장 실패")
    return {"message": "저장 완료"}



@router.put("/update_project_with_users/{project_id}")
async def update_project(
    project_id: UUID,
    body: ProjectUpdateRequestBody,
    db: AsyncSession = Depends(get_db_session),
):
    success = await update_project_with_users(
        db=db,
        project_id=project_id,
        project_name=body.project_name,
        project_detail=body.project_detail,
        new_users=body.project_users,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated"}

@router.post("/meeting/create")
async def create_meeting_with_users(
    meeting_data: MeetingCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        meeting_date_obj = datetime.fromisoformat(meeting_data.meeting_date)

        # 👉 timezone-aware일 경우, tz를 제거하여 naive datetime으로 변환
        if meeting_date_obj.tzinfo is not None:
            meeting_date_obj = meeting_date_obj.replace(tzinfo=None)

        meeting = await insert_meeting(
            db=db,
            project_id=meeting_data.project_id,
            meeting_title=meeting_data.meeting_title,
            meeting_agenda=meeting_data.meeting_agenda,
            meeting_date=meeting_date_obj,
            meeting_audio_path=meeting_data.meeting_audio_path
        )
        for user in meeting_data.users:
            await insert_meeting_user(
                db=db,
                meeting_id=meeting.meeting_id,
                user_id=user.user_id,
                role_id=user.role_id
            )
            await insert_meeting_calendar(
                db=db,
                user_id=user.user_id,
                project_id=meeting_data.project_id,
                title=meeting_data.meeting_title,
                start=meeting_date_obj
            )
        return {"meeting_id": meeting.meeting_id}
    except Exception as e:
        traceback_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        print("🔥 서버 에러:", traceback_str)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": traceback_str}
        )
