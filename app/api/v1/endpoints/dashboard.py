from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, or_, select, text
from sqlalchemy.orm import selectinload
import logging

from app.db.db_session import get_db_session
from app.models.meeting import Meeting
from app.models.feedback import Feedback
from app.models.feedbacktype import FeedbackType
from app.models.project import Project
from app.models.flowy_user import FlowyUser
from app.models.meeting_user import MeetingUser
from app.services.admin_service.admin_check import get_current_user
from app.api.v1.endpoints.dashboard_repo import get_summary_data, get_chart_data, get_table_data

router = APIRouter()

# Pydantic 모델 정의
from pydantic import BaseModel

# 로거 설정
logger = logging.getLogger(__name__)

class DashboardSummary(BaseModel):
    title: str
    unit: str
    target: float
    average: float
    labelTarget: str
    labelAvg: str
    color: str
    colorAvg: str
    yMax: int

class ChartData(BaseModel):
    year: str
    발생빈도: int
    처리시간: int
    period: str

class TableData(BaseModel):
    period: str
    target: str
    value: str
    pop: str
    prevValue: str
    growth: str

class DashboardResponse(BaseModel):
    summary: List[DashboardSummary]
    chartData: List[ChartData]
    tableData: List[TableData]

@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
    period: str = Query("month", description="기간 타입: year, quarter, month, week, day"),
    project_id: Optional[str] = Query(None, description="프로젝트 ID"),
    department: Optional[str] = Query(None, description="부서명"),
    user_id: Optional[str] = Query(None, description="사용자 ID"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)")
):
    """
    대시보드 통계 데이터를 조회합니다.
    """
    try:
        # 현재 로그인한 사용자의 실제 정보를 DB에서 조회
        user_query = select(FlowyUser).where(FlowyUser.user_login_id == current_user.login_id)
        user_result = await db.execute(user_query)
        current_user_info = user_result.scalar_one_or_none()
        
        if not current_user_info:
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
        
        # 날짜 문자열을 datetime으로 변환
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="시작 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="종료 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        
        # 기본 날짜 범위 설정 (최근 30일)
        if not parsed_start_date:
            parsed_start_date = datetime.now() - timedelta(days=30)
        if not parsed_end_date:
            parsed_end_date = datetime.now()

        # 필터 조건 구성 (회사 필터 추가)
        filters = []
        
        # 회사 필터는 Meeting → MeetingUser → FlowyUser 조인을 통해 적용
        # 기본적으로 현재 사용자가 속한 회사의 회의만 조회
        # (dashboard_repo.py에서 조인을 통해 필터링)
        
        logger.info(f"=== 필터 조건 구성 시작 ===")
        logger.info(f"현재 사용자 회사 ID: {current_user_info.user_company_id}")
        
        if project_id:
            try:
                project_uuid = UUID(project_id)
                filters.append(Meeting.project_id == project_uuid)
                logger.info(f"프로젝트 필터 추가: {project_id}")
            except ValueError:
                raise HTTPException(status_code=400, detail="프로젝트 ID 형식이 올바르지 않습니다.")
        if department:
            filters.append(FlowyUser.user_dept_name == department)
            logger.info(f"부서 필터 추가: {department}")
        if user_id:
            filters.append(FlowyUser.user_login_id == user_id)
            logger.info(f"사용자 필터 추가: {user_id}")
        if parsed_start_date and parsed_end_date:
            filters.append(Meeting.meeting_date.between(parsed_start_date, parsed_end_date))
            logger.info(f"날짜 필터 추가: {parsed_start_date} ~ {parsed_end_date}")
            
        # 회사 필터 추가 - 현재 사용자가 속한 회사의 데이터만
        filters.append(FlowyUser.user_company_id == current_user_info.user_company_id)
        logger.info(f"회사 필터 추가: {current_user_info.user_company_id}")
        logger.info(f"총 필터 조건 수: {len(filters)}")
        logger.info(f"=== 필터 조건 구성 완료 ===")

        # 1. Summary 데이터 조회
        summary_data = await get_summary_data(db, filters, parsed_start_date, parsed_end_date)
        
        # 2. 차트 데이터 조회
        chart_data = await get_chart_data(db, period, filters, parsed_start_date, parsed_end_date)
        
        # 3. 테이블 데이터 조회
        table_data = await get_table_data(db, filters, parsed_start_date, parsed_end_date)

        return DashboardResponse(
            summary=summary_data,
            chartData=chart_data,
            tableData=table_data
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"대시보드 데이터 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/filter-options")
async def get_dashboard_filter_options(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
    project_id: Optional[str] = Query(None, description="프로젝트 ID"),
    department: Optional[str] = Query(None, description="부서명")
):
    """
    대시보드 필터 옵션을 조회합니다.
    """
    try:
        # 디버깅: 현재 토큰에서 추출한 사용자 정보 출력
        logger.info(f"Token에서 추출한 사용자 정보: {current_user}")
        logger.info(f"사용자 login_id: {current_user.login_id}")
        
        # 현재 로그인한 사용자의 실제 정보를 DB에서 조회
        user_query = select(FlowyUser).where(FlowyUser.user_login_id == current_user.login_id)
        user_result = await db.execute(user_query)
        current_user_info = user_result.scalar_one_or_none()
        
        # 디버깅: DB에서 조회한 사용자 정보 출력
        if current_user_info:
            logger.info(f"DB에서 조회한 사용자 정보: {current_user_info.user_name}, 회사ID: {current_user_info.user_company_id}")
        else:
            logger.error(f"DB에서 사용자 정보를 찾을 수 없음: {current_user.login_id}")
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
        
        # 프로젝트 목록 - 현재 사용자가 속한 회사의 프로젝트만
        projects_query = (
            select(Project.project_id, Project.project_name)
            .select_from(Project)
            .where(Project.company_id == current_user_info.user_company_id)
        )
        
        # 디버깅: 프로젝트 쿼리 결과 출력
        projects_result = await db.execute(projects_query)
        projects = [{"id": str(p.project_id), "name": p.project_name} for p in projects_result.all()]
        logger.info(f"조회된 프로젝트 수: {len(projects)}")
        logger.info(f"프로젝트 목록: {projects}")
        
        # 전체 프로젝트 수도 확인 (디버깅용)
        all_projects_query = select(Project.project_id, Project.project_name)
        all_projects_result = await db.execute(all_projects_query)
        all_projects = [{"id": str(p.project_id), "name": p.project_name} for p in all_projects_result.all()]
        logger.info(f"전체 프로젝트 수: {len(all_projects)}")
        logger.info(f"전체 프로젝트 목록: {all_projects}")
        
        # 회사별 프로젝트 수 확인 (디버깅용)
        company_projects_query = (
            select(Project.project_id, Project.project_name, Project.company_id)
            .select_from(Project)
        )
        company_projects_result = await db.execute(company_projects_query)
        company_projects = company_projects_result.all()
        logger.info(f"모든 프로젝트의 회사 ID: {[(str(p.project_id), str(p.company_id)) for p in company_projects]}")
        
        # 현재 사용자 회사 ID와 일치하는 프로젝트만 필터링
        user_company_projects = [p for p in company_projects if p.company_id == current_user_info.user_company_id]
        logger.info(f"사용자 회사({current_user_info.user_company_id})의 프로젝트: {[(str(p.project_id), p.project_name) for p in user_company_projects]}")

        # 부서 목록 - 프로젝트 필터 적용
        if project_id:
            try:
                project_uuid = UUID(project_id)
                departments_query = (
                    select(FlowyUser.user_dept_name)
                    .distinct()
                    .select_from(FlowyUser)
                    .join(MeetingUser, FlowyUser.user_id == MeetingUser.user_id)
                    .join(Meeting, MeetingUser.meeting_id == Meeting.meeting_id)
                    .where(
                        FlowyUser.user_dept_name.isnot(None),
                        FlowyUser.user_company_id == current_user_info.user_company_id,
                        Meeting.project_id == project_uuid
                    )
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="프로젝트 ID 형식이 올바르지 않습니다.")
        else:
            departments_query = (
                select(FlowyUser.user_dept_name)
                .distinct()
                .where(
                    FlowyUser.user_dept_name.isnot(None),
                    FlowyUser.user_company_id == current_user_info.user_company_id
                )
            )
        
        departments_result = await db.execute(departments_query)
        departments = [{"name": d.user_dept_name} for d in departments_result.all()]

        # 사용자 목록 - 프로젝트 및 부서 필터 동시 적용
        logger.info(f"=== 사용자 목록 조회 조건 ===")
        logger.info(f"project_id: {project_id}")
        logger.info(f"department: {department}")
        
        if project_id and department:
            # 프로젝트와 부서 모두 선택된 경우 → 해당 프로젝트의 해당 부서 사용자만
            logger.info(f"조건: 프로젝트({project_id}) + 부서({department})")
            try:
                project_uuid = UUID(project_id)
                users_query = (
                    select(FlowyUser.user_id, FlowyUser.user_name, FlowyUser.user_login_id)
                    .distinct()
                    .select_from(FlowyUser)
                    .join(MeetingUser, FlowyUser.user_id == MeetingUser.user_id)
                    .join(Meeting, MeetingUser.meeting_id == Meeting.meeting_id)
                    .where(
                        Meeting.project_id == project_uuid,
                        FlowyUser.user_dept_name == department,
                        FlowyUser.user_company_id == current_user_info.user_company_id
                    )
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="프로젝트 ID 형식이 올바르지 않습니다.")
        elif department:
            # 부서만 선택된 경우 → 해당 부서 사용자만
            logger.info(f"조건: 부서만({department})")
            users_query = (
                select(FlowyUser.user_id, FlowyUser.user_name, FlowyUser.user_login_id)
                .distinct()
                .where(
                    FlowyUser.user_dept_name == department,
                    FlowyUser.user_company_id == current_user_info.user_company_id
                )
            )
        elif project_id:
            # 프로젝트만 선택된 경우 → 해당 프로젝트 참여자만
            logger.info(f"조건: 프로젝트만({project_id})")
            try:
                project_uuid = UUID(project_id)
                users_query = (
                    select(FlowyUser.user_id, FlowyUser.user_name, FlowyUser.user_login_id)
                    .distinct()
                    .select_from(FlowyUser)
                    .join(MeetingUser, FlowyUser.user_id == MeetingUser.user_id)
                    .join(Meeting, MeetingUser.meeting_id == Meeting.meeting_id)
                    .where(
                        Meeting.project_id == project_uuid,
                        FlowyUser.user_company_id == current_user_info.user_company_id
                    )
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="프로젝트 ID 형식이 올바르지 않습니다.")
        else:
            # 둘 다 선택되지 않은 경우 → 회사 내 전체 사용자
            logger.info(f"조건: 전체 사용자")
            users_query = (
                select(FlowyUser.user_id, FlowyUser.user_name, FlowyUser.user_login_id)
                .distinct()
                .where(FlowyUser.user_company_id == current_user_info.user_company_id)
            )
        
        users_result = await db.execute(users_query)
        users = [{"id": str(u.user_id), "name": u.user_name, "login_id": u.user_login_id} for u in users_result.all()]
        logger.info(f"조회된 사용자 수: {len(users)}")
        logger.info(f"사용자 목록: {[u['name'] for u in users]}")
        logger.info(f"=== 사용자 목록 조회 완료 ===")

        return {
            "projects": projects,
            "departments": departments,
            "users": users
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"필터 옵션 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/debug/data-structure")
async def debug_data_structure(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """
    데이터베이스 구조와 실제 데이터를 확인하는 디버깅 엔드포인트
    """
    try:
        # 1. 전체 테이블별 데이터 수 확인
        table_counts = {}
        
        # Meeting 테이블
        meeting_count = await db.execute(select(func.count(Meeting.meeting_id)))
        table_counts["meeting"] = meeting_count.scalar()
        
        # Feedback 테이블
        feedback_count = await db.execute(select(func.count(Feedback.feedback_id)))
        table_counts["feedback"] = feedback_count.scalar()
        
        # FeedbackType 테이블
        feedbacktype_count = await db.execute(select(func.count(FeedbackType.feedbacktype_id)))
        table_counts["feedbacktype"] = feedbacktype_count.scalar()
        
        # MeetingUser 테이블
        meeting_user_count = await db.execute(select(func.count(MeetingUser.meeting_user_id)))
        table_counts["meeting_user"] = meeting_user_count.scalar()
        
        # Project 테이블
        project_count = await db.execute(select(func.count(Project.project_id)))
        table_counts["project"] = project_count.scalar()
        
        # FlowyUser 테이블
        user_count = await db.execute(select(func.count(FlowyUser.user_id)))
        table_counts["flowy_user"] = user_count.scalar()
        
        # 2. 최근 회의 데이터 샘플
        recent_meetings = await db.execute(
            select(Meeting.meeting_id, Meeting.meeting_title, Meeting.meeting_date)
            .order_by(Meeting.meeting_date.desc())
            .limit(5)
        )
        recent_meetings_data = recent_meetings.all()
        
        # 3. 피드백 타입별 데이터 수
        feedback_by_type = await db.execute(
            select(FeedbackType.feedbacktype_name, func.count(Feedback.feedback_id))
            .select_from(FeedbackType)
            .join(Feedback)
            .group_by(FeedbackType.feedbacktype_name)
        )
        feedback_by_type_data = feedback_by_type.all()
        
        # 4. 회의별 참석자 수 분포
        participants_distribution = await db.execute(
            select(func.count(MeetingUser.user_id).label('participant_count'), func.count(Meeting.meeting_id).label('meeting_count'))
            .select_from(Meeting)
            .join(MeetingUser)
            .group_by(func.count(MeetingUser.user_id))
            .order_by(func.count(MeetingUser.user_id))
        )
        participants_distribution_data = participants_distribution.all()
        
        return {
            "table_counts": table_counts,
            "recent_meetings": [
                {
                    "meeting_id": str(m.meeting_id),
                    "title": m.meeting_title,
                    "date": str(m.meeting_date)
                } for m in recent_meetings_data
            ],
            "feedback_by_type": [
                {
                    "type": f.feedbacktype_name,
                    "count": f.count
                } for f in feedback_by_type_data
            ],
            "participants_distribution": [
                {
                    "participant_count": p.participant_count,
                    "meeting_count": p.meeting_count
                } for p in participants_distribution_data
            ]
        }
        
    except Exception as e:
        logger.error(f"데이터 구조 확인 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 구조 확인 오류: {str(e)}")

@router.get("/debug/user-info")
async def debug_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """
    현재 로그인한 사용자 정보를 디버깅용으로 확인
    """
    try:
        # 1. 토큰에서 추출한 정보
        token_info = {
            "sub": current_user.sub,
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "login_id": current_user.login_id,
            "sysrole": current_user.sysrole
        }
        
        # 2. DB에서 실제 사용자 정보 조회
        user_query = select(FlowyUser).where(FlowyUser.user_login_id == current_user.login_id)
        user_result = await db.execute(user_query)
        db_user = user_result.scalar_one_or_none()
        
        db_user_info = None
        if db_user:
            db_user_info = {
                "user_id": str(db_user.user_id),
                "user_name": db_user.user_name,
                "user_login_id": db_user.user_login_id,
                "user_company_id": str(db_user.user_company_id),
                "user_dept_name": db_user.user_dept_name
            }
        
        # 3. 전체 프로젝트 수와 사용자 회사 프로젝트 수 비교
        all_projects_query = select(func.count(Project.project_id))
        all_projects_result = await db.execute(all_projects_query)
        total_projects = all_projects_result.scalar()
        
        company_projects_count = 0
        if db_user:
            company_projects_query = select(func.count(Project.project_id)).where(Project.company_id == db_user.user_company_id)
            company_projects_result = await db.execute(company_projects_query)
            company_projects_count = company_projects_result.scalar()
        
        return {
            "token_info": token_info,
            "db_user_info": db_user_info,
            "total_projects_in_db": total_projects,
            "user_company_projects_count": company_projects_count,
            "success": True
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

@router.get("/debug/filter-test")
async def debug_filter_test(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
    project_id: Optional[str] = Query(None, description="프로젝트 ID"),
    department: Optional[str] = Query(None, description="부서명"),
    user_id: Optional[str] = Query(None, description="사용자 ID")
):
    """
    필터 조건과 실제 데이터를 비교하는 디버깅 엔드포인트
    """
    try:
        # 현재 로그인한 사용자의 실제 정보를 DB에서 조회
        user_query = select(FlowyUser).where(FlowyUser.user_login_id == current_user.login_id)
        user_result = await db.execute(user_query)
        current_user_info = user_result.scalar_one_or_none()
        
        if not current_user_info:
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
        
        logger.info(f"=== 필터 테스트 시작 ===")
        logger.info(f"현재 사용자: {current_user_info.user_name}, 회사ID: {current_user_info.user_company_id}")
        
        # 1. 전체 회의 수 (필터 없음)
        all_meetings_query = select(func.count(Meeting.meeting_id))
        all_meetings_result = await db.execute(all_meetings_query)
        all_meetings_count = all_meetings_result.scalar()
        logger.info(f"전체 회의 수: {all_meetings_count}")
        
        # 2. 현재 사용자 회사의 회의 수
        company_meetings_query = (
            select(func.count(func.distinct(Meeting.meeting_id)))
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .where(FlowyUser.user_company_id == current_user_info.user_company_id)
        )
        company_meetings_result = await db.execute(company_meetings_query)
        company_meetings_count = company_meetings_result.scalar()
        logger.info(f"현재 사용자 회사의 회의 수: {company_meetings_count}")
        
        # 3. 프로젝트별 회의 수
        if project_id:
            try:
                project_uuid = UUID(project_id)
                project_meetings_query = (
                    select(func.count(func.distinct(Meeting.meeting_id)))
                    .select_from(Meeting)
                    .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                    .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
                    .where(
                        Meeting.project_id == project_uuid,
                        FlowyUser.user_company_id == current_user_info.user_company_id
                    )
                )
                project_meetings_result = await db.execute(project_meetings_query)
                project_meetings_count = project_meetings_result.scalar()
                logger.info(f"프로젝트 {project_id}의 회의 수: {project_meetings_count}")
            except ValueError:
                logger.error(f"프로젝트 ID 형식 오류: {project_id}")
        
        # 4. 부서별 회의 수
        if department:
            dept_meetings_query = (
                select(func.count(func.distinct(Meeting.meeting_id)))
                .select_from(Meeting)
                .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
                .where(
                    FlowyUser.user_dept_name == department,
                    FlowyUser.user_company_id == current_user_info.user_company_id
                )
            )
            dept_meetings_result = await db.execute(dept_meetings_query)
            dept_meetings_count = dept_meetings_result.scalar()
            logger.info(f"부서 {department}의 회의 수: {dept_meetings_count}")
        
        # 5. 사용자별 회의 수
        if user_id:
            user_meetings_query = (
                select(func.count(func.distinct(Meeting.meeting_id)))
                .select_from(Meeting)
                .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                .join(FlowyUser, MeetingUser.user_id == MeetingUser.user_id)
                .where(
                    FlowyUser.user_login_id == user_id,
                    FlowyUser.user_company_id == current_user_info.user_company_id
                )
            )
            user_meetings_result = await db.execute(user_meetings_query)
            user_meetings_count = user_meetings_result.scalar()
            logger.info(f"사용자 {user_id}의 회의 수: {user_meetings_count}")
        
        # 6. 실제 회의 데이터 샘플
        sample_meetings_query = (
            select(Meeting.meeting_id, Meeting.meeting_title, Meeting.meeting_date, Meeting.project_id)
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .where(FlowyUser.user_company_id == current_user_info.user_company_id)
            .limit(5)
        )
        sample_meetings_result = await db.execute(sample_meetings_query)
        sample_meetings = sample_meetings_result.all()
        logger.info(f"샘플 회의 데이터: {[(str(m.meeting_id), m.meeting_title, str(m.project_id)) for m in sample_meetings]}")
        
        return {
            "current_user": {
                "name": current_user_info.user_name,
                "company_id": str(current_user_info.user_company_id)
            },
            "meeting_counts": {
                "all": all_meetings_count,
                "company": company_meetings_count,
                "project": project_meetings_count if project_id else None,
                "department": dept_meetings_count if department else None,
                "user": user_meetings_count if user_id else None
            },
            "sample_meetings": [
                {
                    "meeting_id": str(m.meeting_id),
                    "title": m.meeting_title,
                    "date": str(m.meeting_date),
                    "project_id": str(m.project_id)
                } for m in sample_meetings
            ]
        }
        
    except Exception as e:
        logger.error(f"필터 테스트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"필터 테스트 오류: {str(e)}") 