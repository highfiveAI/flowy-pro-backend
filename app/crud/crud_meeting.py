from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from app.models.meeting import Meeting  # 실제 모델 경로에 맞게 수정
from app.models.project_user import ProjectUser
from app.models.flowy_user import FlowyUser
from typing import List, Dict

# 아래는 예시 모델 import (실제 모델 경로/이름에 맞게 수정 필요)
# from app.models import SummaryLog, TaskAssignLog, Feedback

# meeting 저장 함수
async def insert_meeting(
    db: Session,
    project_id: str,
    meeting_title: str,
    meeting_agenda: str,
    meeting_date: datetime,
    meeting_audio_path: str = None
):
    meeting = Meeting(
        meeting_id=str(uuid4()),
        project_id=project_id,
        meeting_title=meeting_title,
        meeting_agenda=meeting_agenda,
        meeting_date=meeting_date,
        meeting_audio_path=meeting_audio_path
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting 


# summary_log 저장 함수
async def insert_summary_log(db: Session, summary_contents: dict):
    print(f"insert_summary_log called! summary_contents={summary_contents}", flush=True)
    from app.models import SummaryLog
    
    # assigned_todos만 추출
    assigned_todos = summary_contents.get("assigned_roles", {}).get("assigned_todos", [])
    
    summary_log = SummaryLog(
        summary_log_id=str(uuid4()),
        updated_summary_contents={"assigned_todos": assigned_todos},  # assigned_todos만 저장
        updated_summary_date=datetime.now()
    )
    db.add(summary_log)
    db.commit()
    db.refresh(summary_log)
    return summary_log

# 역할분담 로그 저장 함수
async def insert_task_assign_log(db: Session, assigned_roles: dict):
    print(f"insert_task_assign_log called! assigned_roles={assigned_roles}", flush=True)
    from app.models import TaskAssignLog
    task_assign_log = TaskAssignLog(
        task_assign_log_id=str(uuid4()),
        updated_task_assign_contents=assigned_roles,
        updated_task_assign_date=datetime.now()
    )
    db.add(task_assign_log)
    db.commit()
    db.refresh(task_assign_log)
    return task_assign_log

# 피드백 저장 함수
async def insert_feedback_log(db: Session, feedback_detail: dict, feedbacktype_id: str = None):
    print(f"insert_feedback_log called! feedback_detail={feedback_detail}", flush=True)
    from app.models import Feedback
    feedback = Feedback(
        feedback_id=str(uuid4()),
        feedbacktype_id=feedbacktype_id,
        feedback_detail=feedback_detail,
        feedback_created_date=datetime.now()
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback 

def get_project_users(db: Session, project_id: str) -> List[Dict]:
    result = db.query(
        FlowyUser.user_id,
        FlowyUser.user_name,
        FlowyUser.user_email,
        FlowyUser.user_phonenum,
        FlowyUser.user_position_id,
        FlowyUser.user_jobname,
        ProjectUser.role_id
    ).join(
        ProjectUser,
        FlowyUser.user_id == ProjectUser.user_id
    ).filter(
        ProjectUser.project_id == project_id
    ).all()
    
    return [
        {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_email": user.user_email,
            "user_phonenum": user.user_phonenum,
            "user_position_id": user.user_position_id,
            "user_jobname": user.user_jobname,
            "role_id": user.role_id
        }
        for user in result
    ]

