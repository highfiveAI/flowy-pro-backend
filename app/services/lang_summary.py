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

    이 문장들을 참고해서, 회의 내용을 명사 위주의 항목별로 보기 좋게 정리해줘.
    각 항목은 회의 내용에 따라 너가 판단해서 자유롭게 정하되,
    - 제목은 이모지와 함께 직관적으로 붙여주고
    - 그 아래에는 관련된 **핵심 정보, 키워드, 요점, 일정, 책임자, 우려사항** 등을 구체적으로 정리해줘.

    **내용 구성 방식은 자유지만, 다음과 같은 특성을 반드시 지켜줘:**
    - 단순 키워드 나열이 아닌, **정보가 충분히 담긴 구체적인 정리**여야 해
    - 전체 내용은 문장이 아닌 **명사형 중심**으로 구성해
    - 각 항목 안에는 필요한 경우 일정, 담당자, 기준, 배경 설명 등을 포함해
    - 형식은 '소주제', '핵심 키워드', '설명' 같은 고정된 틀 없이, **너가 자율적으로 구성**해줘

    **중요:**
    시간 관련 표현이 상대적인 경우('오늘', '내일', '이번 주 금요일' 등), 회의 날짜({today_str}) 기준으로 실제 날짜로 바꿔서 괄호에 함께 표기해.
    - 예: '오늘' → 오늘({today_str}), '이번 주 내' → 이번 주 내({week_range_str})
    - 날짜가 여러 번 등장하면 모두 변환해서 표기하고,
    - 해석이 애매할 경우 반드시 회의 날짜를 기준으로 유추해.

    **결과는 반드시 아래와 같은 JSON 형식으로만 반환해.**
    항목 수나 항목 이름은 자유롭게 정해도 되지만, 전체는 무조건 JSON으로 출력해.

    ```json
    {{
      "📝 항목 제목 A": [
        "핵심 키워드 또는 개요 설명",
        "담당자, 일정, 우선순위 등 구체 정보",
        "실행 계획 또는 협업 방식 등"
      ],
      "📊 항목 제목 B": [
        "... 관련 내용들"
      ]
    }}
    """

    response = await llm.ainvoke(prompt)
    agent_output = response.content

    # JSON 파싱 시도 (코드블록 제거)
    try:
        content = str(agent_output).strip()
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