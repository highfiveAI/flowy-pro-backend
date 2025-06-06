# routers/user.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.security import verify_password
from app.schemas.signup_info import UserCreate, LoginInfo
from app.crud.crud_user import create_user, authenticate_user
from app.api.deps import get_db_session
from app.services.auth import create_access_token, verify_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/jwtlogin")


@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db_session)):
    return create_user(db, user)

@router.post("/login")
def login(user: LoginInfo, db: Session = Depends(get_db_session)):
    auth_user = authenticate_user(db, user.email, user.password)
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": auth_user.user_name},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }

# 로그인 → JWT 반환
@router.post("/jwtlogin")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    auth_user = authenticate_user(db, form_data.username, form_data.password )
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 인증 테스트
@router.get("/me")
def read_me(token: str = Depends(oauth2_scheme)):
    username = verify_token(token)
    return {"username": username}
