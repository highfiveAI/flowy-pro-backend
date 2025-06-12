from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi import APIRouter
from app.services.stt import stt_from_file
from app.services.tagging import tag_chunks_async
from app.services.orchestration import super_agent_for_meeting
import json
import os
import re
from typing import List, Optional, Dict
from pydantic import BaseModel, UUID4
from datetime import datetime
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.crud.crud_meeting import insert_meeting, get_project_users, insert_meeting_user
from app.models.project_user import ProjectUser
from app.models.flowy_user import FlowyUser
from app.models.role import Role
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

class Attendee(BaseModel):
    name: str
    email: str
    role: str

def parse_attendees(
    attendees: List[str] = Form(...)
):
    attendees_list = []
    for attendee_json in attendees:
        try:
            attendee = json.loads(attendee_json)
            if not all(k in attendee for k in ("name", "email", "role")):
                raise ValueError
            attendees_list.append(attendee)
        except Exception:
            raise HTTPException(status_code=400, detail="attendees 형식 오류 (name, email, role 필수, JSON 문자열로 입력)")
    return attendees_list

@router.post("/")
async def stt_api(
    file: UploadFile = File(...),
    subject: str = Form(...),
    agenda: str = Form(None),
    meeting_date: str = Form(...),
    attendees_name: List[str] = Form(...),
    attendees_email: List[str] = Form(...),
    attendees_role: List[str] = Form(...),
    project_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    print("=== stt_api called ===", flush=True)
    def split_items(items):
        result = []
        for item in items:
            result.extend([i.strip() for i in item.split(",") if i.strip()])
        return result

    names = split_items(attendees_name)
    emails = split_items(attendees_email)
    roles = split_items(attendees_role)

    if not (names and emails and roles):
        raise HTTPException(status_code=400, detail="모든 참석자 정보가 필요합니다.")
    if not (len(names) == len(emails) == len(roles)):
        raise HTTPException(status_code=400, detail="참석자 정보 개수가 일치하지 않습니다.")
    if len(names) < 1:
        raise HTTPException(status_code=400, detail="참석자는 1명 이상이어야 합니다.")
    attendees_list = [
        {"name": n, "email": e, "role": r}
        for n, e, r in zip(names, emails, roles)
    ]

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    result = stt_from_file(temp_path)
    os.remove(temp_path)
    print("subject:", subject, "chunks in result:", "chunks" in result, flush=True)
    return {
        **result,
        "attendees": attendees_list,
        "agenda": agenda,
        "meeting_date": meeting_date
    }

@router.post("/meeting-upload/")
async def meeting_upload_api(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    meeting_title: str = Form(...),
    meeting_agenda: str = Form(...),
    meeting_date: str = Form(...),  # 'YYYY-MM-DD HH:mm:ss' 형태
    attendees_name: List[str] = Form(...),
    attendees_email: List[str] = Form(...),
    attendees_role: List[str] = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # 1. 파일 저장
    save_dir = "app/temp_uploads"
    os.makedirs(save_dir, exist_ok=True)
    file_location = os.path.join(save_dir, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    # 2. meeting_date를 datetime으로 변환
    meeting_date_obj = datetime.strptime(meeting_date, "%Y-%m-%d %H:%M:%S")

    # 3. 회의 생성
    meeting = await insert_meeting(
        db=db,
        project_id=project_id,
        meeting_title=meeting_title,
        meeting_agenda=meeting_agenda,
        meeting_date=meeting_date_obj,
        meeting_audio_path=file_location
    )

    # 4. 참석자별 user_id, role_id 찾기 및 저장
    for name, email, role_name in zip(attendees_name, attendees_email, attendees_role):
        user = await db.execute(
            select(FlowyUser).where(FlowyUser.user_name == name, FlowyUser.user_email == email)
        )
        user_obj = user.scalar_one_or_none()
        if not user_obj:
            continue

        role = await db.execute(
            select(Role).where(Role.role_name == role_name)
        )
        role_obj = role.scalar_one_or_none()
        if not role_obj:
            continue

        await insert_meeting_user(
            db=db,
            meeting_id=meeting.meeting_id,
            user_id=user_obj.user_id,
            role_id=role_obj.role_id
        )

    return {"meeting_id": meeting.meeting_id, "meeting_audio_path": file_location}

@router.get("/project-users/{project_id}")
async def get_project_users(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    # 비동기 쿼리 실행
    stmt = select(ProjectUser).where(ProjectUser.project_id == project_id)
    result = await db.execute(stmt)
    project_users = result.scalars().all()
    
    print("=== Project Users Query Result ===")
    print(f"Project ID: {project_id}")
    print(f"Number of users found: {len(project_users)}")
    
    users = []
    for pu in project_users:
        # 비동기 쿼리 실행
        stmt = select(FlowyUser).where(FlowyUser.user_id == pu.user_id)
        result = await db.execute(stmt)
        flowy_user = result.scalar_one_or_none()
        
        if flowy_user:
            print(f"\nUser ID: {pu.user_id}")
            print(f"Role ID: {pu.role_id}")
            print(f"Name: {flowy_user.user_name}")
            print(f"Email: {flowy_user.user_email}")
            users.append({
                "user_id": pu.user_id,
                "role_id": pu.role_id,
                "name": flowy_user.user_name,
                "email": flowy_user.user_email,
                "user_jobname": flowy_user.user_jobname
            })
    
    return {"users": users}

@router.post("/analyze-meeting/")
async def analyze_meeting_api(
    meeting_id: str = Form(...),
    project_name: str = Form(...),
    subject: str = Form(...),
    chunks: str = Form(...),  # JSON 문자열로 전달받음
    attendees_list: str = Form(...),  # JSON 문자열로 전달받음
    agenda: str = Form(None),
    meeting_date: str = Form(None),
    db: Session = Depends(get_db)
):
    import json
    import re
    # chunks, attendees_list는 JSON 문자열로 받으므로 파싱
    parsed_chunks = json.loads(chunks)
    parsed_attendees = json.loads(attendees_list)
    # 분석 및 역할분담 로그 저장
    tag_result = await tag_chunks_async(
        project_name=project_name,
        subject=subject,
        chunks=parsed_chunks,
        attendees_list=parsed_attendees,
        agenda=agenda,
        meeting_date=meeting_date,
        db=db,
        meeting_id=meeting_id
    )
    # 분석 후처리: 추천문서 등
    # all_txt_result = " ".join(tag_result.get("all_sentences") or [])
    # search_result = super_agent_for_meeting(all_txt_result)
    # urls = re.findall(r'https?://\S+', search_result)
    urls = [
        "https://example.com",
        "https://example.org",
        "https://testsite.com/page1",
        "https://mywebsite.net/about",
        "https://service.io/api/data",
        "https://news.example.com/article123",
        "https://blog.example.org/post456",
        "https://shop.example.net/product789",
        "https://app.example.io/dashboard",
        "https://static.example.com/assets/img.png"
    ]

    # print(f"서칭 결과물 : {search_result}")
    return {
        "tagging": tag_result,
        "search_result": urls,
        "meeting_id": meeting_id
    }

