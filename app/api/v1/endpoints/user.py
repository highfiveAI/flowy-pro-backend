# routers/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.signup_info import UserCreate, LoginInfo
from app.crud.crud_user import create_user, authenticate_user
from app.api.deps import get_db_session

router = APIRouter()

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db_session)):
    return create_user(db, user)

@router.post("/login")
def login(user: LoginInfo, db: Session = Depends(get_db_session)):
    auth_user = authenticate_user(db, user.email, user.password)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful", "user_id": auth_user.user_id}