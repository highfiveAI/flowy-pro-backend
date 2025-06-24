from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models import FlowyUser, SignupLog, ProjectUser, Project, Role
from app.schemas.signup_info import UserCreate, TokenPayload
from app.schemas.mypage import UserUpdateRequest, UserWithCompanyInfo
from app.schemas.project import UserSchema, RoleSchema
from app.core.security import verify_password
from app.services.signup_service.auth import create_access_token, verify_token, verify_access_token
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

    # 토큰에서 권한 정보 추출하는 의존성 함수
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=402, detail="인증 실패")
    try:
        user: TokenPayload = await verify_access_token(token)
    except ValueError:
        raise HTTPException(status_code=404, detail="인증 실패")
    return user  # user.sysrole 등으로 권한 확인 가능


# 시스템 관리자 검증
def require_super_admin(user: TokenPayload = Depends(get_current_user)):
    if getattr(user, "sysrole", None) != "c4cb5e53-617e-463f-8ddb-67252f9a9742":
        raise HTTPException(status_code=403, detail="시스템 관리자만 접근 가능")
    return user

# 회사 관리자 검증
def require_company_admin(user: TokenPayload = Depends(get_current_user)):
    if getattr(user, "sysrole", None) != "f3d23b8c-6e7b-4f5d-a72d-8a9622f94084":
        raise HTTPException(status_code=403, detail="회사 관리자만 접근 가능")
    return user

# 둘 중 하나 인지 검증
def require_any_admin(user: TokenPayload = Depends(get_current_user)):
    if getattr(user, "sysrole", None) not in [
        "c4cb5e53-617e-463f-8ddb-67252f9a9742",
        "f3d23b8c-6e7b-4f5d-a72d-8a9622f94084"
    ]:
        raise HTTPException(status_code=403, detail="관리자만 접근 가능")
    return user
