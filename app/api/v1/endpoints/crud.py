from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.company_position import CompanyPositionCreate, CompanyPositionRead
from app.crud import crud_user
from app.api.deps import get_db_session
from typing import List

router = APIRouter()

@router.post("/", response_model=CompanyPositionRead)
def create_position(position_in: CompanyPositionCreate, db: Session = Depends(get_db_session)):
    return crud_user.create_company_position(db, position_in)

@router.get("/", response_model=List[CompanyPositionRead])
def read_positions(db: Session = Depends(get_db_session)):
    return crud_user.get_all_positions(db)