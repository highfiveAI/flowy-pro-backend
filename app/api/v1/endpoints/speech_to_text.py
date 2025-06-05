from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi import APIRouter
from app.services.stt import stt_from_file
from app.services.tagging import tag_chunks_async
from app.services.orchestration import super_agent_for_meeting
import json
import os
import re
from typing import List
from pydantic import BaseModel

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
    attendees_role: List[str] = Form(...)
):
    print("=== stt_api called ===", flush=True)
    # 콤마로 구분된 입력값도 분리해서 여러 명으로 처리
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
    tag_result = None
    if subject and "chunks" in result:
        print("calling tag_chunks...", flush=True)

        tag_result = await tag_chunks_async(subject, result["chunks"], attendees_list, agenda, meeting_date)
        # print(f"결과물 : {tag_result.get("all_sentences")}")
        all_txt_result = " ".join(tag_result.get("all_sentences"))
        search_result = super_agent_for_meeting(all_txt_result)
        urls = re.findall(r'https?://\S+', search_result)
        print(f"서칭 결과물 : {search_result}")
        


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

