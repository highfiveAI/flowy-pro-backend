from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session
from app.crud.crud_user import get_all_users
from app.crud.crud_project import get_project_users_with_projects_by_user_id, get_meetings_with_users_by_project_id
from uuid import UUID
router = APIRouter()

@router.post("")
async def create_projet_api():
    return;

@router.get("/meta")
async def list_users(db: AsyncSession = Depends(get_db_session)):
    users = await get_all_users(db)
    return users

@router.get("/user_id/{user_id}")
async def read_user_projects(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    projects = await get_project_users_with_projects_by_user_id(db, user_id)
    return projects

@router.get("/meeting/{project_id}")
async def read_meetings_with_users(project_id: UUID, db: AsyncSession = Depends(get_db_session)):
    meetings = await get_meetings_with_users_by_project_id(db, project_id)
    return meetings
