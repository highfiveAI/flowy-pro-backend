# routers/user.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.security import verify_password
from app.schemas.signup_info import UserCreate, LoginInfo
from app.crud.crud_user import create_user, authenticate_user, only_authenticate_email
from app.api.deps import get_db_session
from app.services.auth import create_access_token, verify_token
from app.services.google_auth import oauth

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


@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = "http://localhost:8000/api/v1/users/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db_session)):
    # 1) 구글에서 온 authorization code를 받아서 access token 요청
    token = await oauth.google.authorize_access_token(request)
    print(token)
    print("token type:", type(token))
    id_token = token.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No id_token in token")
    if not token:
        raise HTTPException(status_code=400, detail="Failed to get access token from Google")

    user_info = token.get('userinfo')

    # 3) user_info 를 바탕으로 회원가입 또는 로그인 처리 (DB 저장 등)
    # 예: user_info['email'], user_info['name'] 등
    email = user_info.get("email")
    name = user_info.get("name")

    request.session['email'] = email
    print(request.session.get('email'))
    print(name)

    auth_user = only_authenticate_email(db, email)

    if not auth_user:
        return RedirectResponse(url="/login-fail")

    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=30)
    )

    # 4) 처리 후 원하는 곳으로 리다이렉트하거나 토큰 반환 등 응답 처리
    # 여기서는 예시로 성공 페이지나 프론트엔드 주소로 리다이렉트
    return RedirectResponse(url="/login-success")  # 또는 프론트엔드 URL