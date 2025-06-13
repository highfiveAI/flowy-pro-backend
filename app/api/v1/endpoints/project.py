from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session
from app.crud.crud_user import get_all_users
router = APIRouter()

@router.post("")
async def create_projet_api():
    return;

@router.get("/meta")
async def list_users(db: AsyncSession = Depends(get_db_session)):
    users = await get_all_users(db)
    return users