from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, asc, desc
from app.models import FlowyUser, SignupLog, ProjectUser, Project, Role
from app.schemas.signup_info import UserCreate, TokenPayload
from app.schemas.mypage import UserUpdateRequest, UserWithCompanyInfo
from app.schemas.project import UserSchema, RoleSchema
from app.core.security import verify_password
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from uuid import UUID

FRONTEND_URI = settings.FRONTEND_URI
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
now = datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)


async def create_user(db: AsyncSession, user: UserCreate):
    hashed_password = (
        pwd_context.hash(user.password)
    )
    

    db_user = FlowyUser(
        user_name=user.name,
        user_email=user.email,
        user_login_id=user.login_id,
        user_password=hashed_password,
        user_phonenum=user.phone,
        user_company_id=user.company,
        user_dept_name=user.department,
        user_team_name=user.team,
        user_position_id=user.position,
        user_jobname=user.job,
        user_sysrole_id=user.sysrole,
        user_login_type=user.login_type
    )

    db.add(db_user)
    await db.flush()  # 비동기 flush

    log = SignupLog(
        signup_request_user_id=db_user.user_id,
        signup_update_user_id=db_user.user_id,
        signup_status_changed_date=now,
        signup_completed_status="Pending"
    )
    db.add(log)

    await db.commit()
    await db.refresh(db_user)
    return db_user

# 회원가입한 사용자의 회사의 회사관리자 정보 조회
async def get_company_admin_emails(db: AsyncSession, company_id: str, sysrole_id: str) -> list[str]:
    stmt = select(FlowyUser.user_email, FlowyUser.user_name, FlowyUser.user_id).where(
        FlowyUser.user_company_id == company_id,
        FlowyUser.user_sysrole_id == sysrole_id
    )
    result = await db.execute(stmt)
    emails = [row[0] for row in result.fetchall()]
    return emails


async def authenticate_user(db: AsyncSession, login_id: str, password: str):
    stmt = select(FlowyUser).where(FlowyUser.user_login_id == login_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.user_password):
        return None

    # 여기서 상태 체크 추가
    await get_signup_status_or_raise(db, user.user_id)

    return user

async def get_signup_status_or_raise(db: AsyncSession, user_id: UUID) -> str:
    stmt = (
        select(SignupLog)
        .where(SignupLog.signup_request_user_id == user_id)
        .order_by(asc(SignupLog.signup_status_changed_date))
        .limit(1)
    )
    result = await db.execute(stmt)
    signup_log = result.scalars().first()

    if not signup_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회원가입 로그를 찾을 수 없습니다."
        )

    status_value = signup_log.signup_completed_status.lower()

    if status_value in ["pending", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"회원가입 상태가 '{signup_log.signup_completed_status}'입니다."
        )

    return signup_log.signup_completed_status

async def get_signup_status_or_raise_to_login_page(db: AsyncSession, user_id: UUID) -> str:
    stmt = (
        select(SignupLog)
        .where(SignupLog.signup_request_user_id == user_id)
        .order_by(desc(SignupLog.signup_status_changed_date))  # 최신순
        .limit(1)
    )
    result = await db.execute(stmt)
    signup_log = result.scalars().first()

    if not signup_log:
        raise HTTPException(
            status_code=302,
            headers={"Location": f"{FRONTEND_URI}/login?error=not_found"}
        )

    status_value = (signup_log.signup_completed_status or "").lower()

    if status_value in ["pending", "rejected"]:
        raise HTTPException(
            status_code=302,
            headers={"Location": f"{FRONTEND_URI}/login?error=not_allowed"}
        )

    return status_value

async def only_authenticate_email(db: AsyncSession, email: str):
    stmt = select(FlowyUser).options(joinedload(FlowyUser.company)).where(FlowyUser.user_email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    return user

async def get_mypage_user(db: AsyncSession, email: str):
    stmt = (
        select(FlowyUser)
        .options(joinedload(FlowyUser.company))
        .where(FlowyUser.user_email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    return UserWithCompanyInfo(
        user_id=user.user_id,
        user_name=user.user_name,
        user_email=user.user_email,
        user_login_id=user.user_login_id,
        user_phonenum=user.user_phonenum,
        user_team_name=user.user_team_name,
        user_dept_name=user.user_dept_name,
        company_id=user.company.company_id if user.company else None,
        company_name=user.company.company_name if user.company else None,
    )

async def get_projects_for_user(db: AsyncSession, user_id: UUID):
    stmt = (
        select(FlowyUser.user_name, Project.project_name, Project.project_id, Project.project_created_date, Project.project_end_date, ProjectUser.user_id, Project.project_detail)
        .join(ProjectUser, ProjectUser.user_id == FlowyUser.user_id)
        .join(Project, Project.project_id == ProjectUser.project_id)
        .where(FlowyUser.user_id == user_id)
    )
    result = await db.execute(stmt)
    projects = result.all()

    print(f"get_projects_for_user results: {projects}")
    return projects

async def update_user_info(user_id: str, user_update: UserUpdateRequest, session: AsyncSession):
    result = await session.execute(
        select(FlowyUser).where(FlowyUser.user_id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)
  
    # update_data를 사용해서 DB에 저장
    for key, value in update_data.items():
        # print(f"[DEBUG] setattr: {key} = {value}")
        setattr(user, key, value)

    await session.commit()
    await session.refresh(user)

    return {
        "user_id": str(user.user_id),
        "user_name": user.user_name,
        "user_phonenum": user.user_phonenum
    }

# 회사 id, 유저, 역할
async def get_all_users(token_user: TokenPayload, db: AsyncSession) -> list[UserSchema]:

    result = await db.execute(
        select(FlowyUser)
        .options(joinedload(FlowyUser.company))
        .where(FlowyUser.user_id == token_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise Exception("해당 사용자가 존재하지 않습니다.")

    company_id = user.user_company_id

    # 2. 해당 회사의 모든 유저 조회
    result_users = await db.execute(
        select(FlowyUser.user_id, FlowyUser.user_name)
        .where(FlowyUser.user_company_id == company_id)
    )
    users_rows = result_users.all()

    result_roles = await db.execute(select(Role.role_id, Role.role_name))
    roles_rows = result_roles.all()

    users = [UserSchema(user_id=row[0], user_name=row[1]) for row in users_rows]
    roles = [RoleSchema(role_id=row[0], role_name=row[1]) for row in roles_rows]

    return {
        "company_id": company_id,
        "users": users,
        "roles": roles,
    }

async def find_id_from_email(db: AsyncSession, email: str):
    stmt = select(FlowyUser.user_login_id).where(FlowyUser.user_email == email)
    result = await db.execute(stmt)
    user_login_id = result.scalar_one_or_none()

    return user_login_id


async def is_duplicate_login_id(db: AsyncSession, login_id: str) -> bool:
    stmt = select(FlowyUser).where(FlowyUser.user_login_id == login_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user is not None

async def get_user_by_login_id_and_email(
    db: AsyncSession,
    user_login_id: str,
    email: str
) -> FlowyUser | None:
    stmt = select(FlowyUser).where(
        FlowyUser.user_login_id == user_login_id,
        FlowyUser.user_email == email
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# 유저 비밀번호 변경하는 함수
async def update_user_password(db: AsyncSession, user_login_id: str, new_password: str) -> bool:
    # 비밀번호 해시 생성
    hashed_password = pwd_context.hash(new_password)

    # 업데이트 쿼리 작성
    stmt = (
        update(FlowyUser)
        .where(FlowyUser.user_login_id == user_login_id)
        .values(user_password=hashed_password)
        .execution_options(synchronize_session="fetch")
    )

    try:
        await db.execute(stmt)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        # 로그 남기기 등 필요
        return False

# 유저 id를 통해 정보를 찾는 함수
async def get_user_by_id(db: AsyncSession, user_id: str):
    stmt = (
        select(FlowyUser)
        .where(FlowyUser.user_id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user