from langchain_openai import ChatOpenAI
import datetime
import re, json

async def lang_summary(subject, chunks, tag_result, attendees_list=None, agenda=None, meeting_date=None):
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # 점수 1~3인 문장만 추출
    filtered_tag = [
        s for s in tag_result if isinstance(s, dict) and s.get("score", 0) > 0
    ]
    # 점수 0인 문장은 문맥 파악용
    context_only = [
        s for s in tag_result if isinstance(s, dict) and s.get("score", 0) == 0
    ]

    # meeting_date를 기반으로 날짜 계산
    if meeting_date:
        try:
            # meeting_date에서 날짜 부분만 추출 (시간 제외)
            meeting_date_only = meeting_date.split()[0]
            # YYYY-MM-DD 형식으로 파싱
            meeting_date_obj = datetime.datetime.strptime(meeting_date_only, '%Y-%m-%d').date()
            # YYYY.MM.DD(요일) 형식으로 변환
            today_str = meeting_date_obj.strftime('%Y.%m.%d(%a)')
            # 해당 주의 시작일과 종료일 계산
            week_start = meeting_date_obj - datetime.timedelta(days=meeting_date_obj.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            week_range_str = f"{week_start.strftime('%Y.%m.%d(%a)')} ~ {week_end.strftime('%Y.%m.%d(%a)')}"
        except Exception as e:
            print(f"[lang_summary] 날짜 파싱 오류: {e}", flush=True)
            # 오류 발생 시 현재 날짜 사용
            today = datetime.date.today()
            today_str = today.strftime('%Y.%m.%d(%a)')
            week_start = today - datetime.timedelta(days=today.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            week_range_str = f"{week_start.strftime('%Y.%m.%d(%a)')} ~ {week_end.strftime('%Y.%m.%d(%a)')}"
    else:
        # meeting_date가 없는 경우 현재 날짜 사용
        today = datetime.date.today()
        today_str = today.strftime('%Y.%m.%d(%a)')
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)
        week_range_str = f"{week_start.strftime('%Y.%m.%d(%a)')} ~ {week_end.strftime('%Y.%m.%d(%a)')}"

    # 참석자 정보 프롬프트용 문자열 생성
    attendees_list_str = "참석자 정보 없음"
    if attendees_list and isinstance(attendees_list, list):
        attendees_list = "\n".join([
            f"- 이름: {a.get('name', '')}, 이메일: {a.get('email', '')}, 직무: {a.get('role', '')}"
            for a in attendees_list
        ])

    # 프롬프트: json 구조로만 반환하도록 명확히 지시
    prompt = f"""
    너는 회의록 작성 전문가야.

    회의 주제: {subject}

    참석자 목록:
    {attendees_list_str}

    아래는 회의에서 중요한 문장(점수 1~3)만 추린 리스트야:
    {[s['sentence'] for s in filtered_tag]}

    이 문장들을 참고해서, 회의 내용을 문장 나열이 아닌 명사 위주의 항목(키워드, 요점, 항목별 정리)으로 회의록 형식으로 보기 쉽게 정리해줘.
    각 항목은 이모지와 함께 제목을 붙이고, 그 아래에 관련된 핵심 키워드, 요점, 세부 항목을 명사 위주로 정리해.
    (예: 회의 정리, 기능 설계 및 개발 계획, 보안 및 사용자 경험, 개발 일정 및 협업, 팀원들의 확장 욕구 및 사이드 프로젝트 제안 등)
    문장으로 풀어서 쓰지 말고, 최대한 모든 대화 내용을 빠짐없이 포함해서 항목별로 보기 쉽게 정리해.
    각 항목별로 소주제, 세부 내용, 특징, 일정, 협업 방식 등도 명사 위주로 정리해줘.

    **중요:**
    일정, 날짜, 기간 등 시간 관련 표현이 '오늘', '이번주 내', '내일', '다음주' 등 상대적 표현으로 등장하면 반드시 실제 날짜로 변환해서 괄호 안에 명확하게 표기해.
    - 예시: 오늘 → 오늘({today_str}), 이번주 내 → 이번주 내({week_range_str})
    - 만약 '오늘'이 여러 번 등장하면 모두 실제 날짜로 변환해서 표기해.
    - 날짜 계산이 애매하면 반드시 회의 날짜({today_str}) 기준으로 표기해.

    **반드시 아래와 같은 JSON 구조로만 결과를 만들어줘.**
    {{
      "회의 정리": ["..."],
      "기능 설계 및 개발 계획": ["..."],
      "보안 및 사용자 경험": ["..."],
      "개발 일정 및 협업": ["..."],
      "팀원들의 확장 욕구 및 사이드 프로젝트 제안": ["..."]
    }}

    항목명, 항목 개수, 순서 등은 회의 내용에 맞게 자유롭게 정해도 되지만 반드시 JSON 구조로만 반환해.
    """

    response = await llm.ainvoke(prompt)
    agent_output = response.content

    # JSON 파싱 시도 (코드블록 제거)
    try:
        content = agent_output.strip()
        if content.startswith("```json"):
            content = content.removeprefix("```json").removesuffix("```").strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group()
            result_json = json.loads(content)
            # summary 키가 있으면 그 값만, 없으면 전체 딕셔너리 반환
            if "summary" in result_json and isinstance(result_json["summary"], dict):
                summary_json = result_json["summary"]
            else:
                summary_json = result_json
        else:
            summary_json = {}
    except Exception as e:
        print(f"[lang_summary] JSON 파싱 오류: {e}", flush=True)
        summary_json = {}

    print("[lang_summary] agent_output:", agent_output, flush=True)
    return {
        "tag_result": filtered_tag,
        "agent_output": summary_json
    } 