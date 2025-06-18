# 역할 분배 agent (lang_role.py)
from langchain_openai import ChatOpenAI
import json
from typing import List, Dict, Any
import re

async def assign_roles(subject: str, full_meeting_sentences: List[str], attendees_list: List[Dict[str, Any]], output: dict, agenda: str = "", meeting_date: str = "") -> dict:
    """
    subject: 회의 주제 (str)
    chunks: 회의 내용 청크 리스트 (List[str])
    attendees_list: [{'name': ..., 'email': ..., 'role': ...}, ...] (List[Dict[str, Any]])
    output: lang_todo.py에서 반환된 할일 추출 결과(dict)
    """
    # print(f"[assign_roles] 전달받은 subject: {subject}", flush=True)
    # print(f"[assign_roles] 전달받은 attendees_list: {attendees_list}", flush=True)
    # print(f"[assign_roles] 전달받은 output: {output}", flush=True)
    print(f"[assign_roles] 전달받은 full_meeting_sentences: {full_meeting_sentences}", flush=True)
    print(f"[assign_roles] 전달받은 attendees_list: {attendees_list}", flush=True)
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # 참석자 이름 리스트 생성
    attendee_names = ", ".join([a.get("name", "") for a in attendees_list])
    # 회의 원문 텍스트 전체 생성 (청크 경계 포함)
    meeting_text = "\n".join(full_meeting_sentences)
    # 할일 리스트 추출 (Action + context)
    todos = output.get("todos") if isinstance(output, dict) else []

    prompt = f'''
너는 아래 "회의 원문 텍스트"와 "할일 리스트 (Action)"를 참고하여 할일을 적절한 담당자에게 배정하는 역할이다.

[회의 정보]
- 회의 주제: {subject}
- 회의 안건: {agenda if agenda else "안건 없음"}

[주요 규칙]
1️⃣ 회의 원문 텍스트에서 누가 해당 Action과 관련된 발언을 했는지 문맥을 분석한다.
2️⃣ 담당자가 명확하게 드러나면 그 사람으로 배정한다.
3️⃣ 명확하지 않지만 직무 기반으로 자연스럽게 추론 가능하면 적절한 참석자에게 배정한다.
4️⃣ 억지로 추측이 어려운 경우 "미지정" 으로 남긴다.

[참고 사항]
- 회의 주제와 (안건이 있는 경우) 회의 안건을 참고하여, 해당 회의 맥락과 참석자의 직무/발언을 고려해 Action의 담당자를 정확하게 배정하라.

[참고 정보]
- 참석자 목록: 이름, 직무, 이메일
- 할일 리스트: Action + context
- 회의 원문 텍스트: 전체 회의 내용

[출력 형식]
{{
  "assigned_todos": [
    {{
      "action": "",
      "assignee": "", // 참석자 이름, 없으면 "미지정",
      "schedule": "", // 해당 Action의 예상 일정 (예: "2024-06-10", "이번 주 내", "다음 회의 전", 일정 언급 없으면 "미정" 또는 "언급 없음" 등으로 표기)
      "context": ""
    }},
    ...
  ]
}}

지금부터 아래 정보를 참고하여 담당자를 배정해라:

[참석자 목록]
{json.dumps(attendees_list, ensure_ascii=False)}

[할일 리스트]
{json.dumps(todos, ensure_ascii=False, indent=2)}

[회의 원문 텍스트]
{meeting_text}
'''

    response = await llm.ainvoke(prompt)
    agent_output = response.content
    print("[assign_roles] agent_output:", agent_output, flush=True)

    # JSON 파싱 시도
    try:
        agent_output = agent_output.strip()
        if agent_output.startswith("```json"):
            agent_output = agent_output.removeprefix("```json").removesuffix("``` ").strip()
        match = re.search(r'\{.*\}', agent_output, re.DOTALL)
        if match:
            agent_output = match.group()
            result_json = json.loads(agent_output)
        else:
            result_json = {"assigned_todos": [], "error": "넘겨 받은 할일 리스트가 없습니다.", "raw": agent_output}
    except Exception as e:
        print(f"[assign_roles] JSON 파싱 오류: {e}", flush=True)
        result_json = {"assigned_todos": [], "error": str(e), "raw": agent_output}

    # schedule 항목 추가: action/context가 일치하는 output['todos']에서 schedule을 찾아서 넣기
    if result_json.get("assigned_todos") and todos:
        for assigned in result_json["assigned_todos"]:
            action = assigned.get("action", "")
            context = assigned.get("context", "")
            matched = next((t for t in todos if t.get("action", "") == action and t.get("context", "") == context), None)
            assigned["schedule"] = matched.get("schedule", "") if matched else ""

    return {
        "subject": subject,
        "attendees": attendees_list,
        "output": output,
        "assigned_roles": result_json,
        "agenda": agenda,
        "meeting_date": meeting_date
    } 