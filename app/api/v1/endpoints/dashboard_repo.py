from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String
from sqlalchemy.orm import selectinload
from typing import List, Any
from datetime import datetime, timedelta
from uuid import UUID
from app.models.task_assign_log import TaskAssignLog
from app.models.meeting import Meeting
from app.models.meeting_user import MeetingUser
from app.models.flowy_user import FlowyUser
from app.models.feedback import Feedback
from app.models.feedbacktype import FeedbackType
from app.schemas.dashboard import DashboardSummary, ChartData, TableData
from fastapi import HTTPException

async def calculate_feedback_count(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime, feedback_type: str) -> int:
    """
    5가지 피드백 유형별 조건에 따라 카운팅
    """
    try:
        count = 0
        if feedback_type == "회의 효율성 70% 이상":
            count = await count_efficiency_meetings(db, filters, start_date, end_date)
        elif feedback_type == "회의 잡담 20% 이상":
            count = await count_chit_chat_meetings(db, filters, start_date, end_date)
        elif feedback_type == "회의 안건 미논의":
            count = await count_missing_agenda_meetings(db, filters, start_date, end_date)
        elif feedback_type == "작업 대상 미논의":
            count = await count_unassigned_task_meetings(db, filters, start_date, end_date)
        elif feedback_type == "중복 발언 발생":
            count = await count_duplicate_speech_meetings(db, filters, start_date, end_date)
        else:
            count = 0
            
        return count
    except Exception as e:
        return 0

async def count_efficiency_meetings(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime) -> int:
    """회의 효율성 70% 이상: Score 2~3 비율이 70% 이상인 회의 수"""
    
    # 기본 쿼리 - 회의별로 score 2~3 비율 계산
    base_query = (
        select(Meeting.meeting_id)
        .select_from(Meeting)
        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
        .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        .where(Meeting.meeting_date.between(start_date, end_date))
    )
    
    for filter_condition in filters:
        base_query = base_query.where(filter_condition)
    
    # 조건을 만족하는 회의 ID들 조회
    meeting_ids_result = await db.execute(base_query.distinct())
    meeting_ids = [row[0] for row in meeting_ids_result.all()]
    
    if not meeting_ids:
        return 0
    
    # 실제 구현에서는 summary_log나 feedback 테이블에서 score 정보를 가져와야 함
    # 현재는 데이터가 없으므로 0 반환
    return 0

async def count_chit_chat_meetings(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime) -> int:
    """회의 잡담 20% 이상: Score 0~1 비율이 20% 이상인 회의 수"""
    
    base_query = (
        select(Meeting.meeting_id)
        .select_from(Meeting)
        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
        .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        .where(Meeting.meeting_date.between(start_date, end_date))
    )
    
    for filter_condition in filters:
        base_query = base_query.where(filter_condition)
    
    meeting_ids_result = await db.execute(base_query.distinct())
    meeting_ids = [row[0] for row in meeting_ids_result.all()]
    
    if not meeting_ids:
        return 0
    
    # 실제 구현에서는 summary_log나 feedback 테이블에서 score 정보를 가져와야 함
    # 현재는 데이터가 없으므로 0 반환
    return 0

async def count_missing_agenda_meetings(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime) -> int:
    """회의 안건 미논의: missing_agenda_issues 피드백에 실제 내용이 있는 회의 수"""
    
    # FeedbackType에서 missing_agenda_issues에 해당하는 feedbacktype_id 조회
    feedbacktype_query = (
        select(FeedbackType.feedbacktype_id)
        .where(FeedbackType.feedbacktype_name == 'missing_agenda_issues')
    )
    feedbacktype_result = await db.execute(feedbacktype_query)
    feedbacktype_id = feedbacktype_result.scalar()
    
    if not feedbacktype_id:
        return 0
    
    # 해당 피드백 유형의 피드백이 있고, 내용이 비어있지 않은 회의 수
    feedback_query = (
        select(func.count(func.distinct(Meeting.meeting_id)))
        .select_from(Meeting)
        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
        .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        .join(Feedback, Meeting.meeting_id == Feedback.meeting_id)
        .where(
            Meeting.meeting_date.between(start_date, end_date),
            Feedback.feedbacktype_id == feedbacktype_id,
            Feedback.feedback_detail.isnot(None),
            func.cast(Feedback.feedback_detail, String) != '',
            func.cast(Feedback.feedback_detail, String) != '[]',
            func.cast(Feedback.feedback_detail, String) != 'null'
        )
    )
    
    for filter_condition in filters:
        feedback_query = feedback_query.where(filter_condition)
    
    result = await db.execute(feedback_query)
    count = result.scalar() or 0
    return count

async def count_unassigned_task_meetings(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime) -> int:
    """작업 대상 미논의: updated_task_assign_contents에 "assignee": "미지정"이 있는 회의 수"""
    
    task_query = (
        select(func.count(func.distinct(Meeting.meeting_id)))
        .select_from(Meeting)
        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
        .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        .join(TaskAssignLog, Meeting.meeting_id == TaskAssignLog.meeting_id)
        .where(
            Meeting.meeting_date.between(start_date, end_date),
            TaskAssignLog.updated_task_assign_contents.contains('"assignee": "미지정"')
        )
    )
    
    for filter_condition in filters:
        task_query = task_query.where(filter_condition)
    
    try:
        result = await db.execute(task_query)
        count = result.scalar() or 0
        return count
    except Exception as e:
        return 0

async def count_duplicate_speech_meetings(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime) -> int:
    """중복 발언 발생: meeting_time_analysis 피드백에 "중복된 발언이 발견됨: "이 있는 회의 수"""
    
    # FeedbackType에서 meeting_time_analysis에 해당하는 feedbacktype_id 조회
    feedbacktype_query = (
        select(FeedbackType.feedbacktype_id)
        .where(FeedbackType.feedbacktype_name == 'meeting_time_analysis')
    )
    feedbacktype_result = await db.execute(feedbacktype_query)
    feedbacktype_id = feedbacktype_result.scalar()
    
    if not feedbacktype_id:
        return 0
    
    # 해당 피드백 유형의 피드백에서 중복 발언 키워드가 있는 회의 수
    feedback_query = (
        select(func.count(func.distinct(Meeting.meeting_id)))
        .select_from(Meeting)
        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
        .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
        .join(Feedback, Meeting.meeting_id == Feedback.meeting_id)
        .where(
            Meeting.meeting_date.between(start_date, end_date),
            Feedback.feedbacktype_id == feedbacktype_id,
            func.cast(Feedback.feedback_detail, String).contains('중복된 발언이 발견됨: ')
        )
    )
    
    for filter_condition in filters:
        feedback_query = feedback_query.where(filter_condition)
    
    try:
        result = await db.execute(feedback_query)
        count = result.scalar() or 0
        return count
    except Exception as e:
        return 0

async def get_summary_data(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime, period: str = "month"):
    """Summary 데이터 조회"""
    try:
        # 1. 회의 빈도 계산
        # 기본 쿼리 - 필터링된 회의 수
        meetings_query = (
            select(func.count(func.distinct(Meeting.meeting_id)))
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .where(Meeting.meeting_date.between(start_date, end_date))
        )
        
        for filter_condition in filters:
            meetings_query = meetings_query.where(filter_condition)
        
        total_meetings_result = await db.execute(meetings_query)
        total_meetings_count = total_meetings_result.scalar() or 0
        
        # 날짜 차이 계산
        days_diff = (end_date - start_date).days + 1
        
        # 기간별 평균 회의빈도 계산
        if period == "year":
            avg_frequency = (total_meetings_count / days_diff) * 365 if days_diff > 0 else 0
        elif period == "quarter":
            avg_frequency = (total_meetings_count / days_diff) * 90 if days_diff > 0 else 0
        elif period == "month":
            avg_frequency = (total_meetings_count / days_diff) * 30 if days_diff > 0 else 0
        elif period == "week":
            avg_frequency = (total_meetings_count / days_diff) * 7 if days_diff > 0 else 0
        elif period == "day":
            avg_frequency = total_meetings_count / days_diff if days_diff > 0 else 0
        else:
            avg_frequency = (total_meetings_count / days_diff) * 30 if days_diff > 0 else 0
        
        # 2. 참석자 수 계산
        participants_query = (
            select(func.count(MeetingUser.user_id))
            .select_from(Meeting)
            .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
            .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
            .where(Meeting.meeting_date.between(start_date, end_date))
        )
        
        for filter_condition in filters:
            participants_query = participants_query.where(filter_condition)
        
        total_participants_result = await db.execute(participants_query)
        total_participants = total_participants_result.scalar() or 0
        
        avg_participants = total_participants / total_meetings_count if total_meetings_count > 0 else 0
        
        # 3. 전체 평균 계산 (회사 전체 기준)
        try:
            # 회사 필터 추출
            company_filter = None
            for filter_condition in filters:
                if 'user_company_id' in str(filter_condition):
                    company_filter = filter_condition
                    break
            
            if company_filter:
                # 회사 전체 회의 빈도
                all_meetings_query = (
                    select(func.count(func.distinct(Meeting.meeting_id)))
                    .select_from(Meeting)
                    .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                    .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
                    .where(
                        Meeting.meeting_date.between(start_date, end_date),
                        company_filter
                    )
                )
                
                all_meetings_result = await db.execute(all_meetings_query)
                all_meetings_count = all_meetings_result.scalar() or 0
                
                if period == "year":
                    all_avg_frequency = (all_meetings_count / days_diff) * 365 if days_diff > 0 else 0
                elif period == "quarter":
                    all_avg_frequency = (all_meetings_count / days_diff) * 90 if days_diff > 0 else 0
                elif period == "month":
                    all_avg_frequency = (all_meetings_count / days_diff) * 30 if days_diff > 0 else 0
                elif period == "week":
                    all_avg_frequency = (all_meetings_count / days_diff) * 7 if days_diff > 0 else 0
                elif period == "day":
                    all_avg_frequency = all_meetings_count / days_diff if days_diff > 0 else 0
                else:
                    all_avg_frequency = (all_meetings_count / days_diff) * 30 if days_diff > 0 else 0
                
                # 회사 전체 참석자 수
                company_meeting_ids_query = (
                    select(Meeting.meeting_id)
                    .select_from(Meeting)
                    .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                    .join(FlowyUser, MeetingUser.user_id == FlowyUser.user_id)
                    .where(
                        Meeting.meeting_date.between(start_date, end_date),
                        company_filter
                    )
                    .distinct()
                )
                
                company_meeting_ids_result = await db.execute(company_meeting_ids_query)
                company_meeting_ids = [row[0] for row in company_meeting_ids_result.all()]
                
                if company_meeting_ids:
                    # 2단계: 각 회의의 전체 참석자 수 계산
                    all_participants_subquery = (
                        select(
                            func.count(MeetingUser.user_id).label('participant_count')
                        )
                        .select_from(Meeting)
                        .join(MeetingUser, Meeting.meeting_id == MeetingUser.meeting_id)
                        .where(Meeting.meeting_id.in_(company_meeting_ids))
                        .group_by(Meeting.meeting_id)
                    )
                    
                    all_avg_participants_query = select(func.avg(all_participants_subquery.c.participant_count))
                    all_participants_result = await db.execute(all_avg_participants_query)
                    all_avg_participants = float(all_participants_result.scalar() or 0)
                else:
                    all_avg_participants = 0.0
            else:
                all_avg_frequency = 0
                all_avg_participants = 0
            
        except Exception as e:
            all_avg_frequency = 0
            all_avg_participants = 0

        # yMax 값을 상대적 차이가 잘 보이도록 계산
        frequency_max_value = max(all_avg_frequency, avg_frequency)
        frequency_yMax = max(frequency_max_value * 1.3, 10)  # 최대값의 1.3배, 최소 10
        
        participants_max_value = max(all_avg_participants, avg_participants)
        participants_yMax = max(participants_max_value * 1.3, 5)  # 최대값의 1.3배, 최소 5
        
        return [
            DashboardSummary(
                title="평균 회의빈도",
                unit="회",
                target=round(avg_frequency, 1),  # 조회 대상 기준 (필터링된 결과)
                average=round(all_avg_frequency, 1),  # 전체 평균 (회사 전체)
                labelTarget="조회 대상 기준",
                labelAvg="전체 평균",
                color="#351745",
                colorAvg="#bdbdbd",
                yMax=int(frequency_yMax)
            ),
            DashboardSummary(
                title="평균 참석자 수",
                unit="명",
                target=round(avg_participants, 1),  # 조회 대상 기준 (필터링된 결과)
                average=round(all_avg_participants, 1),  # 전체 평균 (회사 전체)
                labelTarget="조회 대상 기준",
                labelAvg="전체 평균",
                color="#351745",
                colorAvg="#bdbdbd",
                yMax=int(participants_yMax)
            )
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary 데이터 조회 오류: {str(e)}")

async def get_chart_data(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime, period: str = "month"):
    try:
        allowed_periods = {"year", "quarter", "month", "week", "day"}
        if period not in allowed_periods:
            raise HTTPException(status_code=400, detail=f"period 파라미터는 {allowed_periods} 중 하나여야 합니다.")
        
        # 5가지 피드백 유형별 카운팅
        feedback_types = [
            "회의 효율성 70% 이상",
            "회의 잡담 20% 이상", 
            "회의 안건 미논의",
            "작업 대상 미논의",
            "중복 발언 발생"
        ]
        
        chart_data = []
        
        # 기간별 데이터 생성
        current_date = start_date
        period_count = 0
        max_periods = 50  # 무한 루프 방지
        
        while current_date <= end_date and period_count < max_periods:
            period_count += 1
            
            # 기간 키 생성
            if period == "year":
                period_key = current_date.strftime("%Y")
                period_start = datetime(current_date.year, 1, 1)
                period_end = datetime(current_date.year, 12, 31)
                next_date = datetime(current_date.year + 1, 1, 1)
            elif period == "quarter":
                quarter_num = (current_date.month - 1) // 3 + 1
                period_key = f"{current_date.strftime('%Y')}-Q{quarter_num}"
                quarter_start_month = (quarter_num - 1) * 3 + 1
                period_start = datetime(current_date.year, quarter_start_month, 1)
                if quarter_num == 4:
                    period_end = datetime(current_date.year, 12, 31)
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    period_end = datetime(current_date.year, quarter_start_month + 2, 28)  # 대략적
                    next_date = datetime(current_date.year, quarter_start_month + 3, 1)
            elif period == "month":
                period_key = current_date.strftime("%Y-%m")
                period_start = datetime(current_date.year, current_date.month, 1)
                if current_date.month == 12:
                    period_end = datetime(current_date.year, 12, 31)
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    period_end = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
                    next_date = datetime(current_date.year, current_date.month + 1, 1)
            elif period == "week":
                period_key = f"{current_date.strftime('%Y')}-W{current_date.isocalendar()[1]:02d}"
                period_start = current_date
                period_end = current_date + timedelta(days=6)
                next_date = current_date + timedelta(weeks=1)
            elif period == "day":
                period_key = current_date.strftime("%Y-%m-%d")
                period_start = current_date
                period_end = current_date
                next_date = current_date + timedelta(days=1)
            
            # 각 피드백 유형별 카운팅
            for feedback_type in feedback_types:
                count = await calculate_feedback_count(
                    db, filters, period_start, period_end, feedback_type
                )
                
                chart_data.append(ChartData(
                    year=period_key,
                    feedback_type=feedback_type,
                    count=count,
                    period=period
                ))
            
            current_date = next_date

        return chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart 데이터 조회 오류: {str(e)}")

async def get_table_data(db: AsyncSession, filters: List[Any], start_date: datetime, end_date: datetime, period: str = "month"):
    try:
        # 5가지 피드백 유형
        feedback_types = [
            "회의 효율성 70% 이상",
            "회의 잡담 20% 이상", 
            "회의 안건 미논의",
            "작업 대상 미논의",
            "중복 발언 발생"
        ]
        
        table_data = []
        
        # 기간별로 데이터를 나누어 처리 (차트 데이터와 동일한 로직)
        current_date = start_date
        period_count = 0
        max_periods = 50  # 무한 루프 방지
        
        while current_date <= end_date and period_count < max_periods:
            period_count += 1
            
            # 기간별 시작/종료 날짜와 표시 형식 계산
            if period == "year":
                period_start = datetime(current_date.year, 1, 1)
                period_end = datetime(current_date.year, 12, 31)
                period_display = current_date.strftime("%Y")
                next_date = datetime(current_date.year + 1, 1, 1)
            elif period == "quarter":
                quarter_num = (current_date.month - 1) // 3 + 1
                quarter_start_month = (quarter_num - 1) * 3 + 1
                period_start = datetime(current_date.year, quarter_start_month, 1)
                if quarter_num == 4:
                    period_end = datetime(current_date.year, 12, 31)
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    period_end = datetime(current_date.year, quarter_start_month + 2, 28)  # 대략적
                    next_date = datetime(current_date.year, quarter_start_month + 3, 1)
                period_display = f"{quarter_num}Q"
            elif period == "month":
                period_start = datetime(current_date.year, current_date.month, 1)
                if current_date.month == 12:
                    period_end = datetime(current_date.year, 12, 31)
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    period_end = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
                    next_date = datetime(current_date.year, current_date.month + 1, 1)
                period_display = f"{current_date.month:02d}월"
            elif period == "week":
                period_start = current_date
                period_end = current_date + timedelta(days=6)
                week_num = current_date.isocalendar()[1]
                period_display = f"WK{week_num:02d}"
                next_date = current_date + timedelta(weeks=1)
            elif period == "day":
                period_start = current_date
                period_end = current_date
                weekdays = ['월', '화', '수', '목', '금', '토', '일']
                weekday = weekdays[current_date.weekday()]
                period_display = f"{current_date.strftime('%Y-%m-%d')}({weekday})"
                next_date = current_date + timedelta(days=1)
            else:
                period_start = datetime(current_date.year, current_date.month, 1)
                if current_date.month == 12:
                    period_end = datetime(current_date.year, 12, 31)
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    period_end = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
                    next_date = datetime(current_date.year, current_date.month + 1, 1)
                period_display = current_date.strftime("%Y-%m")
            
            # 조회 기간을 벗어나면 period_end를 조정
            if period_end > end_date:
                period_end = end_date
            
            # 이전 기간 계산 (비교용)
            period_diff = period_end - period_start
            prev_period_start = period_start - period_diff - timedelta(days=1)
            prev_period_end = period_start - timedelta(days=1)
            
            # 현재 기간 필터 생성
            current_filters = []
            for filter_condition in filters:
                if 'meeting_date' not in str(filter_condition):
                    current_filters.append(filter_condition)
            
            # 이전 기간 필터 생성
            prev_filters = []
            for filter_condition in filters:
                if 'meeting_date' not in str(filter_condition):
                    prev_filters.append(filter_condition)
            
            # 각 피드백 유형별 데이터 생성
            for feedback_type in feedback_types:
                # 1. 조회 평균 (필터링된 결과)
                filtered_count = await calculate_feedback_count(
                    db, current_filters, period_start, period_end, feedback_type
                )
                
                # 2. 이전 기간 카운트 (PoP 계산용)
                prev_count = await calculate_feedback_count(
                    db, prev_filters, prev_period_start, prev_period_end, feedback_type
                )
                
                # 3. 전체 평균 (회사 전체 기준)
                # 회사 필터만 적용하여 전체 평균 계산
                company_filters = []
                for filter_condition in filters:
                    if 'user_company_id' in str(filter_condition):
                        company_filters.append(filter_condition)
                
                total_count = await calculate_feedback_count(
                    db, company_filters, period_start, period_end, feedback_type
                )
                
                # 4. PoP 계산 (이전 기간 대비 현재 기간)
                if prev_count > 0:
                    pop_rate = ((filtered_count - prev_count) / prev_count) * 100
                    pop = f"{pop_rate:+.1f}%"
                else:
                    pop = "+100.0%" if filtered_count > 0 else "0.0%"
                
                # 5. 전체 대비 계산 (조회 평균 vs 전체 평균)
                if total_count > 0:
                    vs_total_rate = ((filtered_count - total_count) / total_count) * 100
                    vs_total = f"{vs_total_rate:+.1f}%"
                else:
                    vs_total = "+100.0%" if filtered_count > 0 else "0.0%"
                
                table_data.append(TableData(
                    period=period_display,
                    feedback_type=feedback_type,
                    filtered_avg=f"{filtered_count}건",
                    pop=pop,
                    total_avg=f"{total_count}건",
                    vs_total=vs_total
                ))
            
            current_date = next_date

        return table_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table 데이터 조회 오류: {str(e)}")
