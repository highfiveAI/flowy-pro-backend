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
    db: Session = Depends(get_db)
):
    print("=== stt_api called ===", flush=True)
    print("Received parameters:", flush=True)
    print(f"file: {file.filename}", flush=True)
    print(f"subject: {subject}", flush=True)
    print(f"agenda: {agenda}", flush=True)
    print(f"meeting_date: {meeting_date}", flush=True)
    print(f"attendees_name: {attendees_name}", flush=True)
    print(f"attendees_email: {attendees_email}", flush=True)
    print(f"attendees_role: {attendees_role}", flush=True)
    print(f"project_name: {project_name}", flush=True)

    try:
        # 파일 확장자 검사
        file_ext = file.filename.lower().split('.')[-1]
        if file_ext not in ['mp3', 'wav', 'm4a', 'ogg']:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. (지원 형식: mp3, wav, m4a, ogg)"
            )

        # 파일 크기 검사 (50MB 제한)
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(
                status_code=400,
                detail="파일 크기는 50MB를 초과할 수 없습니다."
            )
        
        # 파일 포인터를 다시 처음으로
        await file.seek(0)

        # 임시 파일로 저장
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        print(f"[STT] 임시 파일 생성 완료: {temp_path}", flush=True)
        
        # STT 변환
        result = stt_from_file(temp_path)
        
        # 임시 파일 삭제
        try:
            os.remove(temp_path)
            print(f"[STT] 임시 파일 삭제 완료: {temp_path}", flush=True)
        except Exception as e:
            print(f"[STT] 임시 파일 삭제 실패: {e}", flush=True)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        print("subject:", subject, "chunks in result:", "chunks" in result, flush=True)
        tag_result = None
        if subject and "chunks" in result:
            print("calling tag_chunks...", flush=True)
            tag_result = await tag_chunks_async(project_name, subject, result["chunks"], attendees_list, agenda, meeting_date, db)
            # print(f"결과물 : {tag_result.get("all_sentences")}")
            # all_txt_result = " ".join(tag_result.get("all_sentences"))
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
            


        else:
            print("tag_chunks 조건 불충분", flush=True)

        return {
            **result, 
            "tagging": tag_result, 
            "attendees": attendees_list,
            "agenda": agenda,
            "meeting_date": meeting_date,
            "search_result": urls
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")

