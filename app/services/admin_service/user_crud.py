from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import logging
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session, joinedload, contains_eager
from app.core.config import settings
from app.models.flowy_user import FlowyUser
from app.models.signup_log import SignupLog
from app.models.company import Company
from app.models.company_position import CompanyPosition
from app.models.sysrole import Sysrole

# 로거 설정
logger = logging.getLogger(__name__)

# .env 파일에서 DB 설정 로드
load_dotenv()

# DB 연결 설정
DB_URL = settings.CONNECTION_STRING
# DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/flowy_db")
engine = create_engine(
    DB_URL,
    connect_args={'options': '-c client_encoding=utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserCRUD:
    def __init__(self):
        self.db: Session = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def create(self, user_data: dict) -> FlowyUser:
        """새로운 사용자를 생성합니다."""
        try:
            # 이메일 중복 검사
            if self._get_user_by_email(user_data["user_email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 이메일입니다."
                )

            # 로그인 ID 중복 검사
            if self._get_user_by_login_id(user_data["user_login_id"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 로그인 ID입니다."
                )

            # 사용자 생성
            user = FlowyUser(**user_data)
            self.db.add(user)
            self.db.flush()  # user_id를 얻기 위해 flush

            # 회원가입 이력 생성
            signup_log = SignupLog(
                signup_log_id=uuid4(),
                signup_request_user_id=user.user_id,
                signup_update_user_id=UUID("3c89c6ab-c755-4925-8e64-ab134668a253"),
                signup_status_changed_date=datetime.now(),
                signup_completed_status="Approved" # Approved, Pending, Rejected
            )
            self.db.add(signup_log)
            
            self.db.commit()
            self.db.refresh(user)
            return user
            
        except Exception as e:
            self.db.rollback()
            raise e

    def get_all(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """모든 사용자를 회원가입 상태와 함께 조회합니다."""
        try:
            print(f"사용자 목록 조회 시작 - skip: {skip}, limit: {limit}")
            
            # FlowyUser와 관련 테이블들을 조인하여 조회
            query = (
                self.db.query(
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
            results = query.all()
            print(f"조회된 사용자 수: {len(results)}")
            
            # 결과를 딕셔너리 리스트로 변환
            users_with_status = []
            for user, signup_completed_status, company_name, position_name, sysrole_name in results:
                try:
                    print(f"\n사용자 정보 변환 시작 ----------------")
                    print(f"user_id: {user.user_id}")
                    print(f"signup_completed_status 타입: {type(signup_completed_status)}")
                    print(f"signup_completed_status 값: {signup_completed_status}")
                    
                    status = "Pending" if signup_completed_status is None else signup_completed_status
                    print(f"최종 status 값: {status}")
                    
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
                    
                    print(f"변환된 user_dict: {user_dict}")
                    print("사용자 정보 변환 완료 ----------------\n")
                    
                    users_with_status.append(user_dict)
                except Exception as e:
                    print(f"사용자 데이터 변환 중 오류 발생: {str(e)}, user_id: {user.user_id}")
                    continue
            
            print(f"전체 변환된 데이터: {users_with_status}")
            return users_with_status
            
        except Exception as e:
            print(f"사용자 목록 조회 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"사용자 목록 조회 중 오류 발생: {str(e)}"
            )

    def get_by_id(self, user_id: UUID) -> dict:
        """ID로 사용자를 회원가입 상태와 함께 조회합니다."""
        try:
            print(f"사용자 조회 시작 - user_id: {user_id}")
            
            result = (
                self.db.query(
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
                .first()
            )
            
            if not result:
                print(f"사용자를 찾을 수 없음 - user_id: {user_id}")
                raise HTTPException(
                    status_code=404,
                    detail="사용자를 찾을 수 없습니다."
                )
            
            user, signup_completed_status, company_name, position_name, sysrole_name = result
            
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

    def update(self, user_id: UUID, user_data: dict) -> FlowyUser:
        """사용자 정보를 수정합니다."""
        try:
            user = self.get_by_id(user_id)

            # 이메일 중복 검사
            if "user_email" in user_data:
                existing_user = self._get_user_by_email(user_data["user_email"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 이메일입니다."
                    )

            # 로그인 ID 중복 검사
            if "user_login_id" in user_data:
                existing_user = self._get_user_by_login_id(user_data["user_login_id"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 사용 중인 로그인 ID입니다."
                    )

            for key, value in user_data.items():
                setattr(user, key, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, user_id: UUID) -> None:
        """사용자를 삭제합니다."""
        try:
            user = self.get_by_id(user_id)
            self.db.delete(user)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def _get_user_by_email(self, email: str) -> Optional[FlowyUser]:
        """이메일로 사용자를 조회합니다."""
        return self.db.query(FlowyUser).filter(FlowyUser.user_email == email).first()

    def _get_user_by_login_id(self, login_id: str) -> Optional[FlowyUser]:
        """로그인 ID로 사용자를 조회합니다."""
        return self.db.query(FlowyUser).filter(FlowyUser.user_login_id == login_id).first()

    def update_user_status(self, user_id: UUID, status: str) -> dict:
        """사용자의 승인 상태를 변경합니다."""
        try:
            print(f"사용자 상태 변경 시작 - user_id: {user_id}, status: {status}")
            
            # 사용자 존재 여부 확인
            user = (
                self.db.query(FlowyUser)
                .filter(FlowyUser.user_id == user_id)
                .first()
            )
            
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="사용자를 찾을 수 없습니다."
                )
            
            # 기존 signup_log가 있는지 확인
            signup_log = (
                self.db.query(SignupLog)
                .filter(SignupLog.signup_request_user_id == user_id)
                .first()
            )
            
            if signup_log:
                # 기존 로그 업데이트
                signup_log.signup_completed_status = status
                signup_log.signup_status_changed_date = datetime.now()
            else:
                # 새로운 로그 생성
                signup_log = SignupLog(
                    signup_log_id=uuid4(),
                    signup_request_user_id=user_id,
                    signup_update_user_id=UUID("3c89c6ab-c755-4925-8e64-ab134668a253"),  # 관리자 ID
                    signup_status_changed_date=datetime.now(),
                    signup_completed_status=status
                )
                self.db.add(signup_log)
            
            self.db.commit()
            
            # 업데이트된 사용자 정보 반환
            return self.get_by_id(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            print(f"사용자 상태 변경 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"사용자 상태 변경 중 오류 발생: {str(e)}"
            ) 