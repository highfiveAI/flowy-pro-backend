import openai
import os
import json
import re
import datetime
import calendar
import asyncio
from typing import List, Dict, Any
from app.services.lang_role import assign_roles
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType

openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_relative_schedule(schedule_str: str, meeting_date: str) -> str:
    """
    상대적 일정 표현(오늘, 내일, 이번 주 금요일, 수요일 오전 11시 등)이 포함되어있는 문자열을 meeting_date 기준 실제 날짜(YYYY.MM.DD(요일) 또는 YYYY.MM.DD(요일) HH:MM)로 변환

    """
    if not meeting_date:
        return schedule_str
    try:
        date_match = re.match(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", meeting_date)
        if not date_match:
            return schedule_str
        year, month, day = map(int, date_match.groups())
        base_date = datetime.date(year, month, day)
        weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        # 오늘/내일/모레
        if schedule_str in ["오늘", "오늘 중"]:
            target = base_date
            time_part = ""
        elif schedule_str == "내일":
            target = base_date + datetime.timedelta(days=1)
            time_part = ""
        elif schedule_str == "모레":
            target = base_date + datetime.timedelta(days=2)
            time_part = ""
        # 이번 주/다음 주 요일 및 시간
        elif re.match(r"(이번 주|다음 주) [월화수목금토일](요일)?( [오전|오후][ 0-9:시분]+)?", schedule_str):
            m = re.match(r"(이번 주|다음 주) ([월화수목금토일])(요일)?( (오전|오후) ?([0-9]{1,2})(:[0-9]{2})?시?([0-9]{1,2}분)?)?", schedule_str)
            if m:
                week_type, day_name, _, _, ampm, hour, minute, min2 = m.groups()
                day_map = {"월":0, "화":1, "수":2, "목":3, "금":4, "토":5, "일":6}
                base_weekday = base_date.weekday()
                target_weekday = day_map[day_name]
                days_ahead = (target_weekday - base_weekday + 7) % 7
                if week_type == "다음 주":
                    days_ahead += 7
                elif days_ahead == 0:
                    days_ahead = 7
                target = base_date + datetime.timedelta(days=days_ahead)
                # 시간 파싱
                if ampm and hour:
                    h = int(hour)
                    if ampm == "오후" and h < 12:
                        h += 12
                    m_ = int(minute[1:]) if minute else 0
                    time_part = f" {h:02d}:{m_:02d}"
                else:
                    time_part = ""
            else:
                return schedule_str
        # 요일 및 시간 (예: 수요일 오전 11시)
        elif re.match(r"[월화수목금토일](요일)?( (오전|오후) ?[0-9]{1,2}(시)?([0-9]{1,2}분)?)?", schedule_str):
            m = re.match(r"([월화수목금토일])(요일)?( (오전|오후) ?([0-9]{1,2})(시)?([0-9]{1,2}분)?)?", schedule_str)
            if m:
                day_name, _, _, ampm, hour, _, minute = m.groups()
                day_map = {"월":0, "화":1, "수":2, "목":3, "금":4, "토":5, "일":6}
                base_weekday = base_date.weekday()
                target_weekday = day_map[day_name]
                days_ahead = (target_weekday - base_weekday + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target = base_date + datetime.timedelta(days=days_ahead)
                if ampm and hour:
                    h = int(hour)
                    if ampm == "오후" and h < 12:
                        h += 12
                    m_ = int(minute[:-1]) if minute else 0
                    time_part = f" {h:02d}:{m_:02d}"
                else:
                    time_part = ""
            else:
                return schedule_str
        # 'YYYY-MM-DD' 등 날짜 문자열이 이미 들어온 경우
        elif re.match(r"\d{4}[.-]\d{1,2}[.-]\d{1,2}", schedule_str):
            date_match2 = re.match(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", schedule_str)
            y, m, d = map(int, date_match2.groups())
            target = datetime.date(y, m, d)
            time_part = ""
        else:
            return schedule_str
        # 날짜 포맷: YYYY.MM.DD(요일) [HH:MM]
        weekday = weekday_map[target.weekday()]
        return f"{target.year}.{target.month:02d}.{target.day:02d}({weekday}){time_part}"
    except Exception:
        return schedule_str

def build_todo_prompt(subject: str, agenda: str, relevant_sentences: list, meeting_date: str = None) -> str:
    prompt = f'''
너는 회의 대화록에서 "정말 해야 하는 업무 (Action)"만 정확하게 추출하는 역할을 한다.

[목적]
이 프롬프트의 목적은 회의록에서 "실제 실행해야 하는 Action"만 추출하는 것이다.  
회의에서 논의된 문제점, 아이디어, 이슈 정리는 Action이 아니다 (이미 요약 Agent에서 처리된다).

[회의 정보]
- 회의 주제: {subject}
- 회의 안건: {agenda if agenda else "안건 없음"}

[주요 규칙]
1️⃣ "문제점/이슈/아이디어 정리"는 Action이 아니다 → 추출 금지
2️⃣ "누가 무엇을 하겠다 / 확인하겠다 / 수정하겠다 / 검토하겠다" 와 같이 *구체적인 수행 의지가 자연스럽게 드러난 경우* Action 으로 추출한다.
3️⃣ "수행 의지"란, 말한 사람이 그 업무를 실제로 **수행할 의도가 있는 것으로 자연스럽게 해석되는 경우**를 포함한다.
    - "제가 하겠습니다", "해보겠습니다", "정리할게요", "올리겠습니다", "공유하겠습니다" 등도 포함한다.
    - 단순히 "필요합니다", "고려해야 합니다" 등은 여전히 수행 의지가 없으므로 Action 아님.
4️⃣ Action은 "명확한 업무 단위"로 작성한다. (예: "오류 확인", "오류 수정", "매뉴얼 작성", "자료 준비", "회의 일정 확인")
5️⃣ "담당자 지정"은 하지 않는다. → 역할분배 Agent가 따로 담당한다.
6️⃣ **중복되거나 유사한 Action은 하나로 묶어서 추출한다.**
7️⃣ **불필요하게 세분화된 Action은 하나의 명확한 업무 단위로 묶어서 추출한다.**
8️⃣ **예정된 회의(예: 다음 미팅, 리뷰 미팅 등)도 Action으로 반드시 추출한다.**
9️⃣ **반드시 JSON만 출력하라. JSON 이외의 텍스트(설명, 안내, 영어 문장 등)는 절대 출력하지 마라.**

[Action 일정 추론 규칙]
- 각 Action별로 "언제까지 해야 하는지"의 예상 일정을 **회의 맥락 전체에서 반드시 추론하여** "schedule"에 입력한다.
- Action과 일정이 같은 문장에 없더라도, 회의록 전체에서 유추할 수 있으면 반드시 Action별로 가장 적합한 일정을 매핑한다.
- 예를 들어, 회의록 마지막에 "각자 월요일 오전까지 1차 정리해주시고요"라고 하면, 관련 Action의 schedule에 "월요일" 날짜를 반드시 넣는다.
- 일정(schedule)은 반드시 meeting_date를 기준으로 실제 날짜(YYYY.MM.DD(요일) 또는 YYYY.MM.DD(요일) HH:MM)로 변환해서 표기하라.
- "월요일", "수요일 오전 11시" 등 상대적/자유형식 표현은 절대 사용하지 마라.
- 변환이 불가능하면 "미정" 또는 "언급 없음"으로 표기하라.
- 일정이 여러 번 언급되거나 애매하면 가장 명확한 일정을 선택한다.
- 회의에서 일정이 전혀 언급되지 않은 Action만 "미정" 또는 "언급 없음"으로 표기한다.

[강화된 예외 규칙]  
- **"수정이 필요합니다", "해결해야 할 것 같습니다", "고려해봐야 합니다", "논의가 필요합니다", "문제가 있습니다"** → Action 아님 (단순 의견/제안/필요성 언급 → 수행 의지 없음 → Action 금지)
- "회의에서 실제로 실행 책임이 확정되지 않은 것"은 Action으로 추출 금지
- **이 문장에서 "수행하고자 하는 의지가 명확하게 보이는지" 반드시 판단하라. → 명확한 수행 의지가 없는 경우 Action으로 추출하지 않는다.**
- Action으로 추출할지 말지는 "수행 의지 여부"를 가장 우선 기준으로 삼는다.

[참고 사항]
- 회의 주제와 (안건이 있는 경우) 회의 안건을 참고하여, 해당 회의 맥락에서 실제 실행해야 하는 Action만 정확하게 추출하라.

[빈 경우 출력 규칙]
- 만약 회의 대화록에서 "구체적인 실행 업무 (Action)"가 전혀 발견되지 않는 경우, 아래 형식으로 출력한다:

{{
  "todos": [],
  "summary": "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다.",
  "total_count": 0
}}

- 빈 경우에도 반드시 위 형식 그대로 출력할 것.

반드시 JSON만 출력하라. JSON 이외의 텍스트(설명, 안내, 영어 문장 등)는 절대 출력하지 마라.

[출력 형식]
{{
  "todos": [
    {{
      "action": "",    // 명확한 업무 단위
      "context": "",   // 해당 Action이 나온 회의 원문 문장
      "schedule": ""   // 해당 Action의 예상 일정 (예: "2025-06-10(화)" 일정 언급 없으면 "미정" 또는 "언급 없음" 등으로 표기)
    }},
    ...
  ],
  "summary": "",      // 이번 회의에서 발생한 할일을 간단하게 요약
  "total_count": 0    // 총 할일 개수
}}

[중요]
- Action은 "실제 해야 하는 업무"만 추출한다.
- 반드시 "수행하고자 하는 의지가 보이는 발언"인 경우만 Action으로 추출한다.
- 담당자 배정은 하지 않는다. (speaker 정보도 포함하지 않는다)
- 이후 역할분배 Agent가 담당자를 배정할 것이므로, "Action + context" 만 정확하게 추출하는 것이 가장 중요하다.

지금부터 아래 대화록을 분석하여 위 기준으로 Action만 추출해줘:

<<< 회의 대화록 텍스트 >>>
{chr(10).join(relevant_sentences)}
'''
    return prompt

def extract_todos_tool(input_text: str) -> str:
    import asyncio
    llm = ChatOpenAI(temperature=0)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    response = loop.run_until_complete(llm.ainvoke(input_text))
    return response.content

# Tool 등록
tools = [
    Tool(
        name="Extract Todos",
        func=extract_todos_tool,
        description="회의록에서 할일만 추출 (동기 Tool)"
    )
]

llm = ChatOpenAI(temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

async def extract_todos(subject: str, chunks: List[str], attendees_list: List[Dict[str, Any]], sentence_scores: List[Dict[str, Any]], agenda: str = None, meeting_date: str = None) -> Dict[str, Any]:
    """
    회의 내용에서 할 일을 추출하는 함수 (langchain agent 기반)
    """
    relevant_sentences = [
        score["sentence"] for score in sentence_scores 
        if score["score"] is not None and score["score"] >= 2
    ]
    prompt = build_todo_prompt(subject, agenda, relevant_sentences, meeting_date)
    # agent 실행 (비동기, 파싱 오류 자동 처리)
    result = await agent.ainvoke({"input": prompt}, handle_parsing_errors=True)
    import json, re
    content = result["output"] if isinstance(result, dict) and "output" in result else str(result)
    if content.startswith("```json"):
        content = content.removeprefix("```json").removesuffix("```").strip()
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        content = match.group()
        result_json = json.loads(content)
    else:
        result_json = {
            "todos": [],
            "summary": "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다.",
            "total_count": 0
        }
    output = {
        "todos": result_json.get("todos", []),
        "summary": result_json.get("summary", "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다."),
        "total_count": result_json.get("total_count", len(result_json.get("todos", [])))
    }
    # schedule 변환 적용
    if meeting_date and output["todos"]:
        for todo in output["todos"]:
            if "schedule" in todo and todo["schedule"]:
                todo["schedule"] = parse_relative_schedule(todo["schedule"], meeting_date)
    # full_meeting_sentences 생성 (청크 경계 표시)
    full_meeting_sentences = []
    for idx, chunk in enumerate(chunks):
        full_meeting_sentences.append(f"=== 청크 {idx+1} 시작 ===")
        sentences = [s.strip() for s in chunk.split('\n') if s.strip()]
        full_meeting_sentences.extend(sentences)
    # 역할분배 agent 호출 (chunks 대신 full_meeting_sentences 전달)
    assigned_roles = await assign_roles(subject, full_meeting_sentences, attendees_list, output, agenda, meeting_date)
    return {
        "todos_result": output,
        "assigned_roles": assigned_roles,
        "agenda": agenda,
        "meeting_date": meeting_date
    }