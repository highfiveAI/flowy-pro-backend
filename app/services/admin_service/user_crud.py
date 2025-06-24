from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import logging
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.core.config import settings
from app.models.flowy_user import FlowyUser
from app.models.signup_log import SignupLog
from app.models.company import Company
from app.models.company_position import CompanyPosition
from app.models.sysrole import Sysrole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 로거 설정
logger = logging.getLogger(__name__)

# .env 파일에서 DB 설정 로드
load_dotenv()

# DB 연결 설정 (비동기)
DB_URL = settings.CONNECTION_STRING.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(
    DB_URL,
    echo=True
)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class UserCRUD:
    def __init__(self):
        self.db: AsyncSession = AsyncSessionLocal()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def create(self, user_data: dict) -> dict:
        """새로운 사용자를 생성합니다."""
        try:
            # 이메일 중복 검사
            existing_user = await self._get_user_by_email(user_data["user_email"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 이메일입니다."
                )

            # 로그인 ID 중복 검사
            existing_user = await self._get_user_by_login_id(user_data["user_login_id"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 로그인 ID입니다."
                )

            # 비밀번호 해싱
            if "user_password" in user_data:
                user_data["user_password"] = pwd_context.hash(user_data["user_password"])
            
            # 로그인 타입 설정
            user_data["user_login_type"] = "general"

            # 사용자 생성
            user = FlowyUser(**user_data)
            self.db.add(user)
            await self.db.flush()  # user_id를 얻기 위해 flush

            # 회원가입 이력 생성
            signup_log = SignupLog(
                signup_log_id=uuid4(),
                signup_request_user_id=user.user_id,
                signup_update_user_id=UUID("7f2d2784-b12b-4b8d-a9fc-3857e52f9e96"),
                signup_status_changed_date=datetime.now(),
                signup_completed_status="Approved" # Approved, Pending, Rejected
            )
            self.db.add(signup_log)
            
            await self.db.commit()
            await self.db.refresh(user)

            # 관련 정보 조회
            company_query = select(Company).filter(Company.company_id == user.user_company_id)
            position_query = select(CompanyPosition).filter(CompanyPosition.position_id == user.user_position_id)
            sysrole_query = select(Sysrole).filter(Sysrole.sysrole_id == user.user_sysrole_id)

            company_result = await self.db.execute(company_query)
            position_result = await self.db.execute(position_query)
            sysrole_result = await self.db.execute(sysrole_query)

            company = company_result.scalar_one_or_none()
            position = position_result.scalar_one_or_none()
            sysrole = sysrole_result.scalar_one_or_none()

            # 응답 데이터 구성
            return {
                "user_id": user.user_id,
                "user_login_id": user.user_login_id,
                "user_email": user.user_email,
                "user_name": user.user_name,
                "user_phonenum": user.user_phonenum,
                "user_company_id": user.user_company_id,
                "user_dept_name": user.user_dept_name,
                "user_team_name": user.user_team_name,
                "user_position_id": user.user_position_id,
                "user_jobname": user.user_jobname,
                "user_sysrole_id": user.user_sysrole_id,
                "signup_completed_status": signup_log.signup_completed_status,
                "company_name": company.company_name if company else None,
                "position_name": position.position_name if position else None,
                "sysrole_name": sysrole.sysrole_name if sysrole else None
            }
            
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """모든 사용자를 회원가입 상태와 함께 조회합니다."""
        try:
            print(f"사용자 목록 조회 시작 - skip: {skip}, limit: {limit}")
            
            # FlowyUser와 관련 테이블들을 조인하여 조회
            query = (
                select(
                    FlowyUser,
                    SignupLog.signup_completed_status,
                    Company.company_name,
                    CompanyPosition.position_name,
                    Sysrole.sysrole_name
                )
                .outerjoin(SignupLog, FlowyUser.user_id == SignupLog.signup_request_user_id)
                .outerjoin(Company, FlowyUser.user_company_id == Company.company_id)
                .outerjoin(CompanyPosition, FlowyUser.user_position_id == CompanyPosition.position_id)
                .outerjoin(Sysrole, FlowyUser.user_sysrole_id == Sysrole.sysrole_id)
                .offset(skip)
                .limit(limit)
            )
            
            print(f"실행될 쿼리: {str(query)}")
            result = await self.db.execute(query)
            results = result.all()
            print(f"조회된 사용자 수: {len(results)}")
            
            # 결과를 딕셔너리 리스트로 변환
            users_with_status = []
            for user, signup_completed_status, company_name, position_name, sysrole_name in results:
                try:
                    # # print(f"\n사용자 정보 변환 시작 ----------------")
                    # print(f"user_id: {user.user_id}")
                    # print(f"signup_completed_status 타입: {type(signup_completed_status)}")
                    # print(f"signup_completed_status 값: {signup_completed_status}")
                    
                    status = "Pending" if signup_completed_status is None else signup_completed_status
                    # print(f"최종 status 값: {status}")
                    
                    user_dict = {
                        "user_id": str(user.user_id),
                        "user_login_id": user.user_login_id,
                        "user_email": user.user_email,
                        "user_name": user.user_name,
                        "user_phonenum": user.user_phonenum,
                        "user_position_id": user.user_position_id,
                        "user_dept_name": user.user_dept_name,
                        "user_team_name": user.user_team_name,
                        "user_jobname": user.user_jobname,
                        "user_company_id": user.user_company_id,
                        "user_sysrole_id": user.user_sysrole_id,
                        "signup_completed_status": status,
                        "company_name": company_name,
                        "position_name": position_name,
                        "sysrole_name": sysrole_name
                    }
                    
                    # print(f"변환된 user_dict: {user_dict}")
                    # print("사용자 정보 변환 완료 ----------------\n")
                    
                    users_with_status.append(user_dict)
                except Exception as e:
                    print(f"사용자 데이터 변환 중 오류 발생: {str(e)}, user_id: {user.user_id}")
                    continue
            
            # print(f"전체 변환된 데이터: {users_with_status}")
            return users_with_status
            
        except Exception as e:
            print(f"사용자 목록 조회 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"사용자 목록 조회 중 오류 발생: {str(e)}"
            )

    async def get_by_id(self, user_id: UUID) -> dict:
        """ID로 사용자를 회원가입 상태와 함께 조회합니다."""
        try:
            print(f"사용자 조회 시작 - user_id: {user_id}")
            
            query = (
                select(
                    FlowyUser,
                    SignupLog.signup_completed_status,
                    Company.company_name,
                    CompanyPosition.position_name,
                    Sysrole.sysrole_name
                )
                .outerjoin(SignupLog, FlowyUser.user_id == SignupLog.signup_request_user_id)
                .outerjoin(Company, FlowyUser.user_company_id == Company.company_id)
                .outerjoin(CompanyPosition, FlowyUser.user_position_id == CompanyPosition.position_id)
                .outerjoin(Sysrole, FlowyUser.user_sysrole_id == Sysrole.sysrole_id)
                .filter(FlowyUser.user_id == user_id)
            )
            
            result = await self.db.execute(query)
            user_result = result.first()
            
            if not user_result:
                print(f"사용자를 찾을 수 없음 - user_id: {user_id}")
                raise HTTPException(
                    status_code=404,
                    detail="사용자를 찾을 수 없습니다."
                )
            
            user, signup_completed_status, company_name, position_name, sysrole_name = user_result
            
            # 결과를 딕셔너리로 변환
            user_dict = {
                "user_id": str(user.user_id),
                "user_login_id": user.user_login_id,
                "user_email": user.user_email,
                "user_name": user.user_name,
                "user_phonenum": user.user_phonenum,
                "user_position_id": user.user_position_id,
                "user_dept_name": user.user_dept_name,
                "user_team_name": user.user_team_name,
                "user_jobname": user.user_jobname,
                "user_company_id": user.user_company_id,
                "user_sysrole_id": user.user_sysrole_id,
                "signup_completed_status": "Pending" if signup_completed_status is None else signup_completed_status,
                "company_name": company_name,
                "position_name": position_name,
                "sysrole_name": sysrole_name
            }
            
            print(f"사용자 조회 완료 - user_id: {user_id}")
            return user_dict
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"사용자 조회 중 오류 발생: {str(e)}, user_id: {user_id}")
            raise HTTPException(
                status_code=500,
                detail=f"사용자 조회 중 오류 발생: {str(e)}"
            )

    async def update(self, user_id: UUID, user_data: dict) -> dict:
        """사용자 정보를 수정합니다."""
        try:
            # 사용자 객체 직접 조회
            query = select(FlowyUser).filter(FlowyUser.user_id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="사용자를 찾을 수 없습니다."
                )

            # 이메일 중복 검사
            if "user_email" in user_data:
                existing_user = await self._get_user_by_email(user_data["user_email"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 이메일입니다."
                    )

            # 로그인 ID 중복 검사
            if "user_login_id" in user_data:
                existing_user = await self._get_user_by_login_id(user_data["user_login_id"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 사용 중인 로그인 ID입니다."
                    )

            # 비밀번호 해싱
            if "user_password" in user_data:
                user_data["user_password"] = pwd_context.hash(user_data["user_password"])

            for key, value in user_data.items():
                setattr(user, key, value)

            await self.db.commit()
            await self.db.refresh(user)

            # 관련 정보 조회
            company_query = select(Company).filter(Company.company_id == user.user_company_id)
            position_query = select(CompanyPosition).filter(CompanyPosition.position_id == user.user_position_id)
            sysrole_query = select(Sysrole).filter(Sysrole.sysrole_id == user.user_sysrole_id)
            signup_log_query = select(SignupLog).filter(SignupLog.signup_request_user_id == user_id)

            company_result = await self.db.execute(company_query)
            position_result = await self.db.execute(position_query)
            sysrole_result = await self.db.execute(sysrole_query)
            signup_log_result = await self.db.execute(signup_log_query)

            company = company_result.scalar_one_or_none()
            position = position_result.scalar_one_or_none()
            sysrole = sysrole_result.scalar_one_or_none()
            signup_log = signup_log_result.scalar_one_or_none()

            # 응답 데이터 구성
            return {
                "user_id": user.user_id,
                "user_login_id": user.user_login_id,
                "user_email": user.user_email,
                "user_name": user.user_name,
                "user_phonenum": user.user_phonenum,
                "user_company_id": user.user_company_id,
                "user_dept_name": user.user_dept_name,
                "user_team_name": user.user_team_name,
                "user_position_id": user.user_position_id,
                "user_jobname": user.user_jobname,
                "user_sysrole_id": user.user_sysrole_id,
                "signup_completed_status": signup_log.signup_completed_status if signup_log else "Pending",
                "company_name": company.company_name if company else None,
                "position_name": position.position_name if position else None,
                "sysrole_name": sysrole.sysrole_name if sysrole else None
            }
            
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, user_id: UUID) -> None:
        """사용자를 삭제합니다."""
        try:
            user = await self.get_by_id(user_id)
            await self.db.delete(user)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def _get_user_by_email(self, email: str) -> Optional[FlowyUser]:
        """이메일로 사용자를 조회합니다."""
        query = select(FlowyUser).filter(FlowyUser.user_email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_by_login_id(self, login_id: str) -> Optional[FlowyUser]:
        """로그인 ID로 사용자를 조회합니다."""
        query = select(FlowyUser).filter(FlowyUser.user_login_id == login_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_user_status(self, user_id: UUID, status: str) -> dict:
        """사용자의 승인 상태를 변경합니다."""
        try:
            print(f"사용자 상태 변경 시작 - user_id: {user_id}, status: {status}")
            
            # 사용자 존재 여부 확인
            query = select(FlowyUser).filter(FlowyUser.user_id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="사용자를 찾을 수 없습니다."
                )
            
            # 기존 signup_log가 있는지 확인
            signup_log_query = select(SignupLog).filter(SignupLog.signup_request_user_id == user_id)
            signup_log_result = await self.db.execute(signup_log_query)
            signup_log = signup_log_result.scalar_one_or_none()
            
            if signup_log:
                # 기존 로그 업데이트
                signup_log.signup_completed_status = status
                signup_log.signup_status_changed_date = datetime.now()
            else:
                # 새로운 로그 생성
                signup_log = SignupLog(
                    signup_log_id=uuid4(),
                    signup_request_user_id=user_id,
                    signup_update_user_id=UUID("7f2d2784-b12b-4b8d-a9fc-3857e52f9e96"),  # 관리자 ID
                    signup_status_changed_date=datetime.now(),
                    signup_completed_status=status
                )
                self.db.add(signup_log)
            
            await self.db.commit()
            
            # 업데이트된 사용자 정보 반환
            return await self.get_by_id(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            print(f"사용자 상태 변경 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"사용자 상태 변경 중 오류 발생: {str(e)}"
            )

    async def get_admin_users(self, db: AsyncSession) -> list[dict]:
        admin_sysrole_id = UUID("f3d23b8c-6e7b-4f5d-a72d-8a9622f94084")
        query = (
            select(FlowyUser, Company.company_name)
            .outerjoin(Company, FlowyUser.user_company_id == Company.company_id)
            .where(FlowyUser.user_sysrole_id == admin_sysrole_id)
        )
        result = await db.execute(query)
        results = result.all()
        admin_users = []
        for user, company_name in results:
            admin_users.append({
                "user_id": user.user_id,
                "user_name": user.user_name,
                "user_email": user.user_email,
                "user_login_id": user.user_login_id,
                "user_phonenum": user.user_phonenum,
                "user_company_id": user.user_company_id,
                "user_dept_name": user.user_dept_name,
                "user_team_name": user.user_team_name,
                "user_position_id": user.user_position_id,
                "user_jobname": user.user_jobname,
                "user_sysrole_id": user.user_sysrole_id,
                "company_name": company_name,
            })
        return admin_users

    async def get_users_by_company(self, company_id: UUID) -> list[dict]:
        """회사별 사용자 목록 조회"""
        query = (
            select(FlowyUser)
            .where(FlowyUser.user_company_id == company_id)
        )
        result = await self.db.execute(query)
        users = result.scalars().all()
        return [
            {
                "user_id": user.user_id,
                "user_login_id": user.user_login_id,
                "user_email": user.user_email,
                "user_name": user.user_name,
                "user_phonenum": user.user_phonenum,
                "user_company_id": user.user_company_id,
                "user_dept_name": user.user_dept_name,
                "user_team_name": user.user_team_name,
                "user_position_id": user.user_position_id,
                "user_jobname": user.user_jobname,
                "user_sysrole_id": user.user_sysrole_id
            }
            for user in users
        ]

    async def get_admin_sysrole_id(self) -> UUID:
        """관리자 권한 sysrole_id 동적 조회 (없으면 fallback)"""
        query = select(Sysrole).where(Sysrole.sysrole_name.in_(["admin", "회사 관리자"]))
        result = await self.db.execute(query)
        sysrole = result.scalar_one_or_none()
        if sysrole:
            return sysrole.sysrole_id
        # fallback: 기존 하드코딩 값
        return UUID("f3d23b8c-6e7b-4f5d-a72d-8a9622f94084")

    async def get_user_sysrole_id(self) -> UUID:
        """일반 사용자 권한 sysrole_id 동적 조회 (없으면 fallback)"""
        query = select(Sysrole).where(Sysrole.sysrole_name.in_(["user", "일반 사용자"]))
        result = await self.db.execute(query)
        sysrole = result.scalar_one_or_none()
        if sysrole:
            return sysrole.sysrole_id
        return UUID("c4cb5e53-617e-463f-8ddb-67252f9a9742")

    async def set_admin_user(self, user_id: UUID, company_id: UUID = None, force: bool = False) -> bool:
        """사용자를 관리자 권한으로 지정 (force=True면 기존 관리자 일반 사용자로 변경)"""
        query = select(FlowyUser).filter(FlowyUser.user_id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        admin_sysrole_id = await self.get_admin_sysrole_id()
        user_sysrole_id = await self.get_user_sysrole_id()
        # 회사 ID가 없으면 대상 사용자로부터 추출
        if not company_id:
            company_id = user.user_company_id
        if force:
            # 해당 회사의 기존 관리자 모두 일반 사용자로 변경
            admin_query = select(FlowyUser).where(
                (FlowyUser.user_company_id == company_id) & (FlowyUser.user_sysrole_id == admin_sysrole_id)
            )
            admin_result = await self.db.execute(admin_query)
            admins = admin_result.scalars().all()
            for admin in admins:
                if admin.user_id != user.user_id:
                    admin.user_sysrole_id = user_sysrole_id
        user.user_sysrole_id = admin_sysrole_id

        # signup_log의 signup_completed_status를 Approved로 변경
        signup_log_query = select(SignupLog).filter(SignupLog.signup_request_user_id == user_id)
        signup_log_result = await self.db.execute(signup_log_query)
        signup_log = signup_log_result.scalar_one_or_none()
        if signup_log:
            signup_log.signup_completed_status = "Approved"

        await self.db.commit()
        await self.db.refresh(user)
        return True