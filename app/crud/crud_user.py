from sqlalchemy.orm import Session
from app.models import CompanyPosition, FlowyUser
from app.schemas.company_position import CompanyPositionCreate
from app.schemas.signup_info import UserCreate
from app.core.security import verify_password
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_company_position(db: Session, position_in: CompanyPositionCreate) -> CompanyPosition:
    db_position = CompanyPosition(
        position_code=position_in.position_code,
        position_name=position_in.position_name,
        position_detail=position_in.position_detail,
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

def get_all_positions(db: Session):
    return db.query(CompanyPosition).all()

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = FlowyUser(
        user_name = user.name,
        user_email = user.email,
        user_login_id = user.login_id,
        user_password = hashed_password,
        user_phonenum = user.phone,
        user_company_id = user.company,
        user_dept_name = user.department,
        user_team_name = user.team,
        user_position_id = user.position,
        user_jobname = user.job,
        user_sysrole_id = user.sysrole
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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