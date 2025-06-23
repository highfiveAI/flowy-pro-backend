import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from typing import List, Optional, Any
from pydantic import SecretStr
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta
from ics import Calendar, Event
import uuid
import urllib.parse

# 환경변수에서 값이 없을 때 기본값 처리 함수
def getenv_str(key: str, default: str = "") -> str:
    return os.getenv(key) or default

def getenv_secret(key: str, default: str = "") -> SecretStr:
    return SecretStr(os.getenv(key) or default)

conf = ConnectionConfig(
    MAIL_USERNAME=getenv_str("MAIL_USERNAME"),
    MAIL_PASSWORD=getenv_secret("MAIL_PASSWORD"),
    MAIL_FROM=getenv_str("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=getenv_str("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# 나눔휴먼 폰트 등록
FONT_PATH = "app/static/fonts/NanumHumanRegular.ttf"
pdfmetrics.registerFont(TTFont('NanumHuman', FONT_PATH))

async def send_email(
    subject: str,
    recipients: List[str],
    body: str,
    subtype: str = "html",
    attachments: List[str] = []
):
    """
    공통 이메일 전송 함수 (첨부파일 없이 알림만)
    """
    msg_type = MessageType(subtype)
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=msg_type,
        attachments=attachments
    )
    fm = FastMail(conf)
    await fm.send_message(message)

# 회의 분석 완료 알림 메일 전송 함수
async def send_meeting_email(meeting_info):
    """
    회의 분석 완료 알림 메일 전송 함수
    meeting_info: dict, info_n(참석자 리스트), dt(일시), subj(주제) 필수
    """
    for participant in meeting_info["info_n"]:
        name = participant["name"]
        email = participant["email"]
        subject = f"[FLOWY] {meeting_info['dt']} '{meeting_info['subj']}' 회의 분석 완료 알림"
        body = f"""
        안녕하세요, {name}님 FLOWY입니다.<br><br>
        {meeting_info['dt']}에 진행된 '{meeting_info['subj']}' 회의 분석이 완료되었습니다.<br><br>
        회의의 주요 내용과 논의 결과는 회의 관리에서 보실 수 있습니다.<br><br>
        <a href='http://localhost:5173/dashboard/{meeting_info['meeting_id']}'>http://localhost:5173/dashboard/{meeting_info['meeting_id']}</a><br><br>
        감사합니다.<br><br>
        Flowy pro 드림
        """
        await send_email(subject, [email], body) 

# 회원가입 알림 메일 회사 관리자에게 전송하는 함수
async def send_signup_email_to_admin(user_info, admin_emails):
    """
    회원가입 알림 메일 전송 함수
    user_info: dict, name(이름), email(이메일), user_id(USERID) 필수
    admin_emails: 회사 관리자 이메일 리스트
    """
    subject = f"[FLOWY PRO] 회원가입 요청 ('{user_info['name']}({user_info['user_id']})')"
    body = f"""
    안녕하세요, Flowy Pro 입니다.<br><br>
    '{user_info['name']}({user_info['user_login_id']})'님의 신규 회원가입 요청으로 알림 메일 드립니다.<br><br>
    회원가입 승인 여부를 확인해주세요.<br><br>
    <a href='http://localhost:5173/admin/user'>http://localhost:5173/admin/user</a><br><br>
    감사합니다.<br>
    Flowy pro 드림
    """
    await send_email(subject, admin_emails, body) 

# 회의 분석 결과 수정시 참석자들에게 수정 알림 메일을 전송하는 함수
async def send_meeting_update_email(meeting_info):
    """
    회의 분석 결과 수정 알림 메일 전송 함수
    meeting_info: dict, info_n(참석자 리스트), dt(일시), subj(주제), update_dt(수정일시), meeting_id(회의 ID) 등
    info_n만 있어도 최소 동작하도록 유연하게 처리
    """

    def format_datetime(dt_str):
        try:
            # ISO 포맷 처리
            if 'T' in dt_str:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            return dt_str
        except Exception:
            return dt_str

    dt = format_datetime(meeting_info.get('dt', ''))
    subj = meeting_info.get('subj', '')
    update_dt = format_datetime(meeting_info.get('update_dt', ''))
    meeting_id = meeting_info.get('meeting_id', '')

    for participant in meeting_info["info_n"]:
        name = participant.get("name", "")
        email = participant.get("email", "")
        roles = participant.get("roles", [])
        tasks_html = ""
        if roles and len(roles) > 0:
            for idx, role in enumerate(roles, 1):
                action = role.get("action", "-")
                schedule = role.get("schedule", "-")
                # 날짜 파싱 및 구글 캘린더 링크용 포맷
                try:
                    date_str = ''.join([c for c in schedule if c.isdigit() or c == '.'])
                    date_obj = datetime.strptime(date_str, "%Y.%m.%d")
                except Exception:
                    try:
                        date_obj = datetime.strptime(schedule, "%Y-%m-%d")
                    except Exception:
                        date_obj = datetime.now()
                dtstart = date_obj.replace(hour=10, minute=0, second=0)
                dtend = dtstart + timedelta(hours=1)
                start_str = dtstart.strftime('%Y%m%dT%H%M%SZ')
                end_str = dtend.strftime('%Y%m%dT%H%M%SZ')
                # 구글 캘린더 일정 추가 링크 생성
                gcal_url = (
                    "https://calendar.google.com/calendar/render?action=TEMPLATE"
                    f"&text={urllib.parse.quote(action)}"
                    f"&dates={start_str}/{end_str}"
                    f"&details={urllib.parse.quote('회의 중 발언 기반 자동 역할입니다.')}"
                    f"&location={urllib.parse.quote('온라인 회의')}"
                )
                tasks_html += f"• <b>업무 {idx}:</b> {action} <b>/ 완료 기한:</b> {schedule}<br>"
                tasks_html += f"📅 일정 등록을 원하시면 <a href='{gcal_url}'>Google Calendar에 바로 추가</a>하세요.<br>"
        else:
            tasks_html = f"이번 회의에서는 {name}님께 별도의 역할이 지정되지 않았습니다.<br>필요 시 회의 내용을 참고하시거나 관련자에게 문의해주세요.<br><br>"
        subject = f"[FLOWY PRO] '{dt}' '{subj}' 분석 결과 (수정)"
        body = f"""
        안녕하세요, {name}님  <br>
        Flowy Pro 입니다.<br><br>
        지난 '{dt}'에 진행된 「{subj}」의 분석 결과가 수정되었습니다.<br>
        이번 회의에서 {name}님께 할당된 역할이 아래와 같이 반영되었으니 확인 바랍니다.<br>
        <br>---<br><br>
        🗂️ <b>{name}님에게 할당된 업무</b><br><br>
        {tasks_html}
        <br>📌 해당 내용은 회의 중 발언을 기반으로 자동 추출되었습니다. 필요 시 담당자 또는 관리자에게 문의해주세요.<br>
        <br>---<br><br>
        🔍 <b>추가 확인 가능 내용</b><br><br>
        • 회의 요약 보기<br>
        • 회의 피드백 보기<br>
        • 회의 전체 역할 분담<br>
        • 관련 추천 문서<br><br>
        👉 전체 회의 분석 결과 보기: <a href='http://localhost:5173/dashboard/{meeting_id}'>회의 분석 결과 바로가기</a><br>
        <br>---<br><br>
        감사합니다.<br>
        Flowy Pro 드림
        """
        await send_email(subject, [email], body)

# 사용자 상태 변경 알림 메일 전송 함수
async def send_user_status_change_email(user_name: str, user_email: str, status: str):
    """
    사용자 상태 변경 알림 메일 전송 함수
    user_name: 사용자 이름
    user_email: 사용자 이메일
    status: 변경된 상태 (예: Approved, Rejected 등)
    """
    subject = f"[FLOWY PRO] 회원 상태 변경 안내"
    if status == "Approved":
        body = f"""
        안녕하세요, {user_name}님.<br><br>
        신규 회원가입 요청이 승인되었습니다.<br><br>
        <a href='http://www.flowyproapi.com/'>www.flowyproapi.com</a><br><br>
        감사합니다.<br>
        Flowy pro 드림
        """
    elif status == "Rejected":
        body = f"""
        안녕하세요, {user_name}님.<br><br>
        신규 회원가입 요청이 거절되었습니다.<br>
        거절 사유는 담당자를 통해 확인 부탁 드립니다.<br><br>
        <a href='http://www.flowyproapi.com/'>www.flowyproapi.com</a><br><br>
        감사합니다.<br>
        Flowy pro 드림
        """
    else:
        body = f"""
        안녕하세요, {user_name}님.<br><br>
        신규 회원가입 요청이 '{status}'되었습니다.<br><br>
        <a href='http://www.flowyproapi.com/'>www.flowyproapi.com</a><br><br>
        감사합니다.<br>
        Flowy pro 드림
        """
    await send_email(subject, [user_email], body)

    