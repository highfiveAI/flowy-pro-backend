from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Any
from datetime import datetime, timedelta
from app.models.meeting import Meeting
from app.models.meeting_user import MeetingUser
from app.models.flowy_user import FlowyUser
from app.models.feedback import Feedback
from app.models.feedbacktype import FeedbackType
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def get_summary_data(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime):
    try:
        # 전체 회의 통계 - Meeting → MeetingUser → FlowyUser 조인으로 필터 적용 (중복 제거)
        query = (
            select(func.count(func.distinct(Meeting.meeting_id)))
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        )
        
        # 필터 조건 적용
        logger.info(f"=== dashboard_repo.py 필터 적용 시작 ===")
        logger.info(f"받은 필터 조건 수: {len(filters)}")
        for i, filter_condition in enumerate(filters):
            query = query.where(filter_condition)
            logger.info(f"필터 {i+1} 적용: {filter_condition}")
            
        result = await db.execute(query)
        total_meetings_count = result.scalar() or 0
        logger.info(f"필터링된 회의 수: {total_meetings_count}")
        logger.info(f"=== dashboard_repo.py 필터 적용 완료 ===")

        # 평균 회의시간 - 기본값 사용 (오디오 파일 길이 계산 제거)
        avg_duration = 30.0  # 기본 30분
        logger.info(f"평균 회의시간: {avg_duration}분 (기본값)")

        # 평균 회의빈도 (일별)
        days_diff = (end_date - start_date).days
        avg_frequency = total_meetings_count / max(days_diff, 1) * 30  # 월별로 변환

        # 평균 참석자 수 - 서브쿼리 사용 (조인 포함)
        participants_subquery = (
            select(
                func.count(MeetingUser.user_id).label('participant_count')
            )
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .group_by(Meeting.meeting_id)
        )
        for filter_condition in filters:
            participants_subquery = participants_subquery.where(filter_condition)
        participants_subquery = participants_subquery.subquery()
        avg_participants_query = select(func.avg(participants_subquery.c.participant_count))
        participants_result = await db.execute(avg_participants_query)
        avg_participants = float(participants_result.scalar() or 0)
        logger.info(f"평균 참석자 수: {avg_participants}")

        # 전체 평균값 계산 (필터 없이)
        try:
            # 전체 평균 회의시간 - 기본값 사용
            all_avg_duration = 30.0  # 기본 30분
            
            # 전체 평균 회의빈도 (최근 30일 기준)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_meetings_query = select(func.count(Meeting.meeting_id)).where(Meeting.meeting_date >= thirty_days_ago)
            recent_meetings_result = await db.execute(recent_meetings_query)
            recent_meetings_count = recent_meetings_result.scalar() or 0
            all_avg_frequency = float(recent_meetings_count * 30 / 30)
            
            # 전체 평균 참석자 수
            all_participants_subquery = (
                select(
                    func.count(MeetingUser.user_id).label('participant_count')
                )
                .select_from(Meeting)
                .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                .group_by(Meeting.meeting_id)
                .subquery()
            )
            all_avg_participants_query = select(func.avg(all_participants_subquery.c.participant_count))
            all_avg_participants_result = await db.execute(all_avg_participants_query)
            all_avg_participants = float(all_avg_participants_result.scalar() or 0)
        except Exception as e:
            logger.error(f"전체 평균 계산 오류: {str(e)}")
            all_avg_duration = 10.0
            all_avg_frequency = 0
            all_avg_participants = 0

        from app.api.v1.endpoints.dashboard import DashboardSummary
        return [
            DashboardSummary(
                title="평균 회의시간",
                unit="분",
                target=round(all_avg_duration, 1),
                average=round(avg_duration, 1),
                labelTarget="전체 평균",
                labelAvg="조회 대상 기준",
                color="#351745",
                colorAvg="#bdbdbd",
                yMax=max(70, int(all_avg_duration * 1.2))
            ),
            DashboardSummary(
                title="평균 회의빈도",
                unit="회",
                target=round(all_avg_frequency, 1),
                average=round(avg_frequency, 1),
                labelTarget="전체 평균",
                labelAvg="조회 대상 기준",
                color="#351745",
                colorAvg="#bdbdbd",
                yMax=max(800, int(all_avg_frequency * 1.2))
            ),
            DashboardSummary(
                title="평균 참석자 수",
                unit="명",
                target=round(all_avg_participants, 1),
                average=round(avg_participants, 1),
                labelTarget="전체 평균",
                labelAvg="조회 대상 기준",
                color="#351745",
                colorAvg="#bdbdbd",
                yMax=max(10, int(all_avg_participants * 1.2))
            )
        ]
    except Exception as e:
        logger.error(f"Summary 데이터 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary 데이터 조회 오류: {str(e)}")

async def get_chart_data(db: AsyncSession, period: str, filters: List[Any], start_date: datetime, end_date: datetime):
    try:
        allowed_periods = {"year", "quarter", "month", "week", "day"}
        if period not in allowed_periods:
            raise HTTPException(status_code=400, detail=f"period 파라미터는 {allowed_periods} 중 하나여야 합니다.")
        
        # 피드백 통계 조회 - Meeting → MeetingUser → FlowyUser 조인
        feedback_query = (
            select(Feedback)
            .options(selectinload(Feedback.meeting))
            .select_from(Feedback)
            .join(FeedbackType)
            .join(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        )
        for filter_condition in filters:
            feedback_query = feedback_query.where(filter_condition)
        feedback_result = await db.execute(feedback_query)
        feedbacks = feedback_result.scalars().all()
        logger.info(f"조회된 피드백 수: {len(feedbacks)}")
        
        chart_data = []
        if period == "month":
            for i in range(3):
                month_date = start_date - timedelta(days=30*i)
                month_key = month_date.strftime("%Y-%m")
                month_feedbacks = [f for f in feedbacks if f.meeting.meeting_date.month == month_date.month]
                month_feedback_count = len(month_feedbacks)
                # 처리시간 - 기본값 사용 (오디오 파일 길이 계산 제거)
                total_processing_time = month_feedback_count * 30  # 피드백당 30분으로 가정
                from app.api.v1.endpoints.dashboard import ChartData
                chart_data.append(ChartData(
                    year=month_key,
                    발생빈도=month_feedback_count,
                    처리시간=int(total_processing_time),
                    period="month"
                ))
        elif period == "week":
            for i in range(4):
                week_date = start_date - timedelta(weeks=i)
                week_key = f"{week_date.strftime('%Y')}-W{week_date.isocalendar()[1]}"
                week_feedbacks = [f for f in feedbacks if 
                    f.meeting.meeting_date.isocalendar()[1] == week_date.isocalendar()[1]]
                week_feedback_count = len(week_feedbacks)
                # 처리시간 - 기본값 사용
                total_processing_time = week_feedback_count * 30  # 피드백당 30분으로 가정
                from app.api.v1.endpoints.dashboard import ChartData
                chart_data.append(ChartData(
                    year=week_key,
                    발생빈도=week_feedback_count,
                    처리시간=int(total_processing_time),
                    period="week"
                ))
        else:
            for i in range(3):
                month_date = start_date - timedelta(days=30*i)
                month_key = month_date.strftime("%Y-%m")
                month_feedbacks = [f for f in feedbacks if f.meeting.meeting_date.month == month_date.month]
                month_feedback_count = len(month_feedbacks)
                # 처리시간 - 기본값 사용
                total_processing_time = month_feedback_count * 30  # 피드백당 30분으로 가정
                from app.api.v1.endpoints.dashboard import ChartData
                chart_data.append(ChartData(
                    year=month_key,
                    발생빈도=month_feedback_count,
                    처리시간=int(total_processing_time),
                    period="month"
                ))
        if not chart_data or all(c.발생빈도 == 0 for c in chart_data):
            logger.info("실제 데이터가 없어서 빈 배열 반환")
            return []
        return chart_data
    except Exception as e:
        logger.error(f"차트 데이터 조회 오류: {str(e)}")
        return []

async def get_table_data(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime):
    try:
        # 피드백 타입별 통계 - Meeting → MeetingUser → FlowyUser 조인
        feedback_stats_query = (
            select(
                FeedbackType.feedbacktype_name,
                func.count(Feedback.feedback_id).label('count')
            )
            .select_from(FeedbackType)
            .join(Feedback)
            .join(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .group_by(FeedbackType.feedbacktype_name)
        )
        for filter_condition in filters:
            feedback_stats_query = feedback_stats_query.where(filter_condition)
        feedback_stats_result = await db.execute(feedback_stats_query)
        feedback_stats = feedback_stats_result.all()
        logger.info(f"조회된 피드백 타입별 통계: {len(feedback_stats)}개")
        table_data = []
        for stat in feedback_stats:
            logger.info(f"피드백 타입: {stat.feedbacktype_name}, 개수: {stat.count}")
            prev_start_date = start_date - timedelta(days=30)
            prev_end_date = start_date - timedelta(days=1)
            prev_feedback_query = (
                select(
                    func.count(Feedback.feedback_id).label('prev_count')
                )
                .select_from(FeedbackType)
                .join(Feedback)
                .join(Meeting)
                .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
                .where(
                    FeedbackType.feedbacktype_name == stat.feedbacktype_name,
                    Meeting.meeting_date.between(prev_start_date, prev_end_date)
                )
            )
            for filter_condition in filters:
                if not str(filter_condition).startswith('meeting.meeting_date'):
                    prev_feedback_query = prev_feedback_query.where(filter_condition)
            prev_result = await db.execute(prev_feedback_query)
            prev_count = prev_result.scalar() or 0
            if prev_count > 0:
                growth_rate = ((stat.count - prev_count) / prev_count) * 100
                growth_str = f"{growth_rate:+.1f}%"
            else:
                growth_str = "0.0%"
            from app.api.v1.endpoints.dashboard import TableData
            table_data.append(TableData(
                period=start_date.strftime("%Y"),
                target=f"{stat.feedbacktype_name}",
                value=f"{stat.count}건",
                pop=growth_str,
                prevValue=f"{prev_count}건",
                growth=growth_str
            ))
        if not table_data:
            logger.info("실제 데이터가 없어서 빈 배열 반환")
            return []
        return table_data
    except Exception as e:
        logger.error(f"테이블 데이터 조회 오류: {str(e)}")
        return [] 