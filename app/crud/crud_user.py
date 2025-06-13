from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models import FlowyUser, SignupLog, ProjectUser, Project
from app.schemas.signup_info import UserCreate
from app.schemas.mypage import UserUpdateRequest
from app.core.security import verify_password
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        signup_completed_status="Pending"
    )
    db.add(log)

    await db.commit()
    await db.refresh(db_user)
    return db_user

async def authenticate_user(db: AsyncSession, login_id: str, password: str):
    stmt = select(FlowyUser).where(FlowyUser.user_login_id == login_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.user_password):
        return None
    return user


async def only_authenticate_email(db: AsyncSession, email: str):
    stmt = select(FlowyUser).options(joinedload(FlowyUser.company)).where(FlowyUser.user_email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user

async def get_projects_for_user(db: AsyncSession, user_id: UUID):
    stmt = (
        select(FlowyUser.user_name, Project.project_name, Project.project_id)
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

    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(user, key, value)

    await session.commit()
    await session.refresh(user)

    return {
        "user_id": str(user.user_id),
        "user_name": user.user_name,
        "user_team_name": user.user_team_name,
        "user_dept_name": user.user_dept_name,
        "user_phonenum": user.user_phonenum
    }

async def get_all_users(db: AsyncSession) -> list[FlowyUser]:
    result = await db.execute(select(FlowyUser))
    return result.scalars().all()