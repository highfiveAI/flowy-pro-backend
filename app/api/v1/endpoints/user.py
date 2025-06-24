# routers/user.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.security import verify_password
from app.core.config import settings
from app.schemas.signup_info import SocialUserCreate, UserCreate, LoginInfo, TokenPayload
from app.schemas.mypage import UserUpdateRequest, UserWithCompanyInfo
from app.schemas.find_id import EmailRequest, CodeRequest
from app.crud.crud_user import (
    create_user,
    authenticate_user,
    only_authenticate_email,
    get_projects_for_user,
    update_user_info,
    get_mypage_user,
    get_company_admin_emails,
    find_id_from_email,
    get_signup_status_or_raise_to_login_page,
    is_duplicate_login_id,
)
from app.crud.crud_company import get_signup_meta
from app.db.db_session import get_db_session
from app.services.signup_service.auth import create_access_token, verify_token, verify_access_token, check_access_token
from app.services.signup_service.google_auth import oauth
from app.services.notify_email_service import send_verification_code
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
import json


# 환경변수
BACKEND_URI = settings.BACKEND_URI
FRONTEND_URI = settings.FRONTEND_URI
SECRET_KEY = settings.SECRET_KEY 
COOKIE_SECURE = settings.COOKIE_SECURE 
COOKIE_SAMESITE = settings.COOKIE_SAMESITE 
ALGORITHM = "HS256"

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/jwtlogin")
# 소셜 회원가입
@router.post("/social_signup")
async def social_signup(request: Request, user_data: SocialUserCreate, db: AsyncSession = Depends(get_db_session)):
    token = request.cookies.get("signup_token")
    if not token:
        raise HTTPException(status_code=401, detail="토큰이 없습니다")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        name = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="이메일 정보가 없습니다")
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

    # 프론트에서 받은 추가 정보 + 소셜에서 가져온 정보 합치기
    new_user = UserCreate(
        email=email,
        name=name,
        login_id= user_data.login_id,
        password= user_data.password,
        phone= user_data.phone,
        company= user_data.company,
        department= user_data.department,
        team= user_data.team,
        position= user_data.position,
        job= user_data.job,
        sysrole= user_data.sysrole,
        login_type= user_data.login_type
    )

    return await create_user(db, new_user)
    
# 회원가입
@router.post("/signup")
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        # 1. DB 저장
        db_user = await create_user(db, user)
    except Exception as e:
        # 2. DB 저장 실패 시 에러 반환, 메일 발송 X
        return JSONResponse(status_code=400, content={"message": f"회원가입 실패: {str(e)}"})

    duplicate = await is_duplicate_login_id(db, db_user.user_login_id)
    if not duplicate:
        return JSONResponse(status_code=400, content={"message": "회원가입 검증 실패: DB에 사용자 정보가 없습니다."})
    
    # 3. DB 저장 성공 시 관리자에게 메일 발송
    try:
        from app.services.notify_email_service import send_signup_email_to_admin
        user_info = {
            "name": db_user.user_name,
            "email": db_user.user_email,
            "user_id": str(db_user.user_id)
        }
        admin_emails = await get_company_admin_emails(db, db_user.user_company_id, 'f3d23b8c-6e7b-4f5d-a72d-8a9622f94084')
        if admin_emails:
            await send_signup_email_to_admin(user_info, admin_emails)
    except Exception as e:
        # 메일 발송 실패는 회원가입 성공과 별개로 안내 (선택)
        return JSONResponse(status_code=200, content={"message": "회원가입 성공, 메일 발송 실패", "error": str(e)})
    
    return {"message": "회원가입 성공, 메일 발송 완료"}

# 로그인
@router.post("/login")
async def login(user: LoginInfo, response: Response, db: AsyncSession = Depends(get_db_session)):
    auth_user = await authenticate_user(db, user.login_id, user.password)

    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid login_id or password")

    # 로그 확인용 주석입니다. 후에 삭제 하셔도 됩니다.
    print("사용자 권한 : ", auth_user.user_sysrole_id)

    payload = TokenPayload(
        sub=str(auth_user.user_id),
        id=str(auth_user.user_id),
        name=auth_user.user_name,
        email=auth_user.user_email,
        login_id=auth_user.user_login_id,
        sysrole=str(auth_user.user_sysrole_id),
    )

    access_token = await create_access_token(
        data=payload.dict(),
        expires_delta=timedelta(minutes=30)
    )

    response = JSONResponse(content={
        "authenticated": True,
        "user": payload.dict()
    })

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,       # JavaScript에서 접근 불가
        secure=COOKIE_SECURE,        # 배포 시에는 반드시 True (HTTPS에서만 전송)
        samesite=COOKIE_SAMESITE,      # 또는 "strict", "none"
        max_age=3600,        # 쿠키 유지 시간 (초) – 1시간
        path="/",            # 쿠키가 적용될 경로
        
    )

    return response

# 로그아웃
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    return {"message": "Logged out successfully"}

# 로그인 → JWT 반환
@router.post("/jwtlogin")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession  = Depends(get_db_session)):

    auth_user = await authenticate_user(db, form_data.username, form_data.password )
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = await create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 인증 테스트
@router.get("/me")
async def read_me(token: str = Depends(oauth2_scheme)):
    username = await verify_token(token)
    return {"username": username}

# 유저 체크
@router.get("/auth/check")
async def auth_check(request: Request):
    user = await check_access_token(request)
    user_dict = json.loads(user.json())
    return JSONResponse(content={"authenticated": True, "user": user_dict})

#  구글 로그인
@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = BACKEND_URI + "/api/v1/users/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

# 구글 로그인 콜백
@router.get("/auth/google/callback")
async def google_callback(request: Request, response: Response, db: AsyncSession = Depends(get_db_session)):
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

    auth_user = await only_authenticate_email(db, email)
    
    if not auth_user:
        signup_token = await create_access_token(
        data={"sub": name,
            "email": email},
        expires_delta=timedelta(minutes=30)
        )

        redirect_response = RedirectResponse(url= FRONTEND_URI + "/social_sign_up")
        redirect_response.set_cookie(
            key="signup_token",
            value=signup_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=3600,
            path="/", 
        )
        return redirect_response

    await get_signup_status_or_raise_to_login_page(db, auth_user.user_id)

    payload = TokenPayload(
        sub=str(auth_user.user_id),
        id=str(auth_user.user_id),
        name=auth_user.user_name,
        email=auth_user.user_email,
        login_id=auth_user.user_login_id,
        sysrole=str(auth_user.user_sysrole_id)

    )

    access_token = await create_access_token(
        data=payload.dict(),
        expires_delta=timedelta(minutes=30)
    )

    redirect_response = RedirectResponse(url= FRONTEND_URI)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=3600,
        path="/", 
    )

    # 4) 처리 후 원하는 곳으로 리다이렉트하거나 토큰 반환 등 응답 처리
    # 여기서는 예시로 성공 페이지나 프론트엔드 주소로 리다이렉트
    return redirect_response  # 또는 프론트엔드 URL 

# 프로젝트 유저들 get
@router.get("/projects/{user_id}")
async def read_projects_for_user(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    projects = await get_projects_for_user(db, user_id)
    projects_list = [
        {"userName": p[0], "projectName": p[1], "projectId": str(p[2]), "projectCreatedDate": p[3], "projectEndDate": p[4], "projectDetail": p[6]} for p in projects
    ]
    return {"projects": projects_list}

# 회원가입시 회사, 직급 등 메타데이터 get
@router.get("/signup/meta")
async def read_company_names(db: AsyncSession = Depends(get_db_session)):
    data = await get_signup_meta(db)

    return data

# 마이페이지 유저의 정보 get
@router.get("/one")
async def read_one_user(
    request: Request,
    token_user = Depends(check_access_token),
    db: AsyncSession = Depends(get_db_session),
    response_model=UserWithCompanyInfo):

    user_dict = json.loads(token_user.json())
    print(user_dict)
    user_info = await get_mypage_user(db, token_user.email)
    if user_info is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_info

# 마이페이지 유저 정보 업데이트 라우터
@router.put("/update")
async def update_user(
    # request: Request,
    user_update: UserUpdateRequest,
    token_user = Depends(check_access_token),
    session: AsyncSession = Depends(get_db_session)
):

    user_data = await update_user_info(token_user.id, user_update, session)
    return {
        "message": "User updated successfully",
        "user": user_data
    }

# 마이페이지 유저 식별 라우터
@router.post("/mypage/check")
async def mypage_check(
    request: Request,
    userInfo: LoginInfo,
    token_user = Depends(check_access_token),
    db: AsyncSession = Depends(get_db_session)
 ):
    auth_user = await authenticate_user(db, userInfo.login_id, userInfo.password)
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid login_id or password")

    return True

@router.post("/find_id/send_code")
async def send_code_api(request: Request, payload: EmailRequest):
    try:
        # 1. 이메일 형식은 Pydantic(EmailStr)에서 기본 검사됨
        email = payload.email

        # 2. 인증 코드 생성 및 전송 시도
        code = await send_verification_code(email)
        if not code:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="인증 코드 생성에 실패했습니다."
            )

        # 3. 세션에 인증 코드 저장
        try:
            request.session['verify_code'] = code
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="세션 저장 중 오류가 발생했습니다."
            )

        return {"message": "인증 코드가 전송되었습니다."}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 코드 전송 중 알 수 없는 오류가 발생했습니다."
        )

@router.post("/verify_code")
async def verify_code(request: Request, payload: CodeRequest):
    saved_code = request.session.get("verify_code")
    is_verified = payload.input_code == saved_code
    return {"verified": is_verified}

@router.post("/find_id")
async def find_id_api(payload: EmailRequest, db: AsyncSession = Depends(get_db_session)):
    user_login_id = await find_id_from_email(db, payload.email)

    if not user_login_id:
        raise HTTPException(status_code=404, detail="해당 이메일로 등록된 아이디가 없습니다.")

    return {"user_login_id": user_login_id}

@router.get("/sign_up/check_id")
async def check_duplicate_id(login_id: str, db: AsyncSession = Depends(get_db_session)):
    is_duplicate = await is_duplicate_login_id(db, login_id)
    return {"is_duplicate": is_duplicate}