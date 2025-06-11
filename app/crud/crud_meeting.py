from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

# 아래는 예시 모델 import (실제 모델 경로/이름에 맞게 수정 필요)
# from app.models import SummaryLog, TaskAssignLog, Feedback

# summary_log 저장 함수
def insert_summary_log(db: Session, summary_contents: dict):
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
def insert_task_assign_log(db: Session, assigned_roles: dict):
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
def insert_feedback_log(db: Session, feedback_detail: dict, feedbacktype_id: str = None):
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
