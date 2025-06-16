from fastapi import APIRouter, status, Depends
from typing import List
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session

from app.services.admin_service.user_crud import UserCRUD
from app.services.admin_service.company_crud import CompanyCRUD
from app.services.admin_service.position_crud import PositionCRUD


# 사용자 관련 Pydantic 모델
class UserBase(BaseModel):
    user_name: str
    user_email: EmailStr
    user_login_id: str
    user_phonenum: str
    user_company_id: UUID
    user_dept_name: str | None = None
    user_team_name: str | None = None
    user_position_id: UUID
    user_jobname: str | None = None
    user_sysrole_id: UUID


class UserCreate(UserBase):
    user_password: str


class UserUpdate(UserBase):
    user_password: str | None = None


class UserResponse(UserBase):
    user_id: UUID
    signup_completed_status: str
    company_name: str
    position_name: str
    sysrole_name: str

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    status: str


# 회사 관련 Pydantic 모델
class CompanyBase(BaseModel):
    company_name: str
    company_scale: str | None = None
    service_startdate: datetime | None = None
    service_enddate: datetime | None = None
    service_status: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CompanyBase):
    pass


class CompanyStatusUpdate(BaseModel):
    service_status: bool
    service_enddate: datetime | None = None


class CompanyResponse(CompanyBase):
    company_id: UUID

    class Config:
        from_attributes = True


# 직급 관련 Pydantic 모델
class PositionBase(BaseModel):
    position_code: str
    position_name: str
    position_detail: str | None = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(PositionBase):
    pass


class PositionResponse(PositionBase):
    position_id: UUID
    position_company_id: UUID

    class Config:
        from_attributes = True

# 관리자 모델
class AdminUserResponse(BaseModel):
    user_id: UUID
    user_name: str
    user_email: EmailStr 
    user_login_id: str
    user_phonenum: str
    user_company_id: UUID
    user_dept_name: str | None = None
    user_team_name: str | None = None
    user_position_id: UUID
    user_jobname: str | None = None
    user_sysrole_id: UUID
    company_name: str | None = None


router = APIRouter()

# 사용자 관리 API
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """새로운 사용자를 생성합니다."""
    crud = UserCRUD()
    return await crud.create(user.model_dump())

@router.get("/users/admin_users", response_model=List[AdminUserResponse])
async def list_admin_users(db: AsyncSession = Depends(get_db_session)):
    """관리자 권한을 가진 사용자 목록을 조회합니다."""
    crud = UserCRUD()
    return await crud.get_admin_users(db)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID):
    """특정 사용자의 정보를 조회합니다."""
    crud = UserCRUD()
    return await crud.get_by_id(user_id)


@router.get("/users/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100):
    """사용자 목록을 조회합니다."""
    crud = UserCRUD()
    return await crud.get_all(skip=skip, limit=limit)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, user: UserUpdate):
    """사용자 정보를 수정합니다."""
    crud = UserCRUD()
    return await crud.update(user_id, user.model_dump(exclude_unset=True))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID):
    """사용자를 삭제합니다."""
    crud = UserCRUD()
    await crud.delete(user_id)
    return None


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(user_id: UUID, status_update: UserStatusUpdate):
    """사용자의 승인 상태를 변경합니다."""
    crud = UserCRUD()
    return await crud.update_user_status(user_id, status_update.status)




# 회사 관리 API
@router.post("/companies/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(company: CompanyCreate):
    """새로운 회사를 생성합니다."""
    crud = CompanyCRUD()
    return await crud.create(company.model_dump())


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: UUID):
    """특정 회사의 정보를 조회합니다."""
    crud = CompanyCRUD()
    return await crud.get_by_id(company_id)


@router.get("/companies/", response_model=List[CompanyResponse])
async def list_companies(skip: int = 0, limit: int = 100):
    """회사 목록을 조회합니다."""
    crud = CompanyCRUD()
    return await crud.get_all(skip=skip, limit=limit)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(company_id: UUID, company: CompanyUpdate):
    """회사 정보를 수정합니다."""
    crud = CompanyCRUD()
    return await crud.update(company_id, company.model_dump(exclude_unset=True))


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: UUID):
    """회사를 삭제합니다."""
    crud = CompanyCRUD()
    await crud.delete(company_id)
    return None


@router.put("/companies/{company_id}/status", response_model=CompanyResponse)
async def update_company_status(company_id: UUID, status_update: CompanyStatusUpdate):
    """회사의 서비스 상태를 변경합니다."""
    crud = CompanyCRUD()
    return await crud.update_service_status(
        company_id, 
        status_update.service_status,
        status_update.service_enddate
    )


# 직급 관리 API
@router.post("/positions/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(position: PositionCreate):
    """새로운 직급을 생성합니다."""
    crud = PositionCRUD()
    return await crud.create(position.model_dump())


@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(position_id: UUID):
    """특정 직급의 정보를 조회합니다."""
    crud = PositionCRUD()
    return await crud.get_by_id(position_id)


@router.get("/positions/", response_model=List[PositionResponse])
async def list_positions(skip: int = 0, limit: int = 100):
    """직급 목록을 조회합니다."""
    crud = PositionCRUD()
    return await crud.get_all(skip=skip, limit=limit)


@router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(position_id: UUID, position: PositionUpdate):
    """직급 정보를 수정합니다."""
    crud = PositionCRUD()
    return await crud.update(position_id, position.model_dump(exclude_unset=True))


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(position_id: UUID):
    """직급을 삭제합니다."""
    crud = PositionCRUD()
    await crud.delete(position_id)
    return None


@router.get("/companies/{company_id}/positions/", response_model=List[PositionResponse])
async def get_company_positions(company_id: UUID):
    """특정 회사의 직급 목록을 조회합니다."""
    crud = PositionCRUD()
    return await crud.get_by_company_id(company_id) 