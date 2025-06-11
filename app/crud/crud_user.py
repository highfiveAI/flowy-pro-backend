from sqlalchemy.orm import Session
# from sqlalchemy import select
from app.models import FlowyUser, SignupLog, ProjectUser, Project
from app.schemas.signup_info import UserCreate
from app.core.security import verify_password
from passlib.context import CryptContext
# from sqlalchemy.ext.asyncio import AsyncSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password) if user.password else pwd_context.hash("social_dummy_password")

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
    db.flush()

    log = SignupLog(
        signup_request_user_id=db_user.user_id,
        signup_update_user_id=db_user.user_id,
        signup_completed_status="pending"
    )
    db.add(log)

    db.commit()
    db.refresh(db_user)
    return db_user

# async def authenticate_user(db: AsyncSession, email: str, password: str):
#     stmt = select(FlowyUser).where(FlowyUser.user_email == email)
#     result = await db.execute(stmt)
#     user = result.scalar_one_or_none()

#     if not user:
#         return None
#     if not verify_password(password, user.user_password):
#         return None
#     return user

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(FlowyUser).filter(FlowyUser.user_email == email).first()
    if not user:
        return None
    if not verify_password(password, user.user_password):
        return None
    return user

def only_authenticate_email(db: Session, email: str):
    email = db.query(FlowyUser).filter(FlowyUser.user_email == email).first()
    if not email:
        return None
    return email

def get_projects_for_user(db: Session, user_id: str):
    results = (
        db.query(FlowyUser.user_name, Project.project_name)
        .join(ProjectUser, ProjectUser.user_id == FlowyUser.user_id)
        .join(Project, Project.project_id == ProjectUser.project_id)
        .filter(FlowyUser.user_id == user_id)
        .all()
    )
    print(f"get_projects_for_user results: {results}")
    return results