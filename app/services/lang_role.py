# 역할 분배 agent (lang_role.py)
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
import json
from typing import List, Dict, Any
import re

def build_role_assignment_prompt(subject: str, agenda: str, attendees_list: List[Dict[str, Any]], todos: list, meeting_text: str) -> str:
    """역할 분배를 위한 프롬프트 생성"""
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

**반드시 아래 JSON 형식으로만 출력해. JSON 이외의 텍스트는 절대 출력하지 마라.**

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
    return prompt

def assign_roles_tool(input_text: str) -> str:
    """역할 분배를 위한 Tool 함수 (동기)"""
    import asyncio
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        response = loop.run_until_complete(llm.ainvoke(input_text))
        content = str(response.content) if response.content else ""
        
        # JSON 형식 확인 및 추출
        if content.startswith("```json"):
            content = content.removeprefix("```json").removesuffix("```").strip()
        
        # JSON 패턴 찾기
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_content = match.group()
            # JSON 파싱 테스트
            json.loads(json_content)
            return json_content
        else:
            # JSON이 없으면 기본 구조 반환
            return '{"assigned_todos": []}'
            
    except Exception as e:
        print(f"[assign_roles_tool] 오류: {e}", flush=True)
        return '{"assigned_todos": []}'

# Tool 등록
tools = [
    Tool(
        name="Assign Roles",
        func=assign_roles_tool,
        description="회의록에서 할일에 담당자를 배정하는 Tool - 반드시 JSON 형식으로 출력"
    )
]

# Agent 초기화
llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

async def assign_roles(subject: str, full_meeting_sentences: List[str], attendees_list: List[Dict[str, Any]], output: dict, agenda: str = "", meeting_date: str = "") -> dict:
    """
    subject: 회의 주제 (str)
    full_meeting_sentences: 회의 내용 문장 리스트 (List[str])
    attendees_list: [{'name': ..., 'email': ..., 'role': ...}, ...] (List[Dict[str, Any]])
    output: lang_todo.py에서 반환된 할일 추출 결과(dict)
    """
    print(f"[assign_roles] 전달받은 full_meeting_sentences: {full_meeting_sentences}", flush=True)
    print(f"[assign_roles] 전달받은 attendees_list: {attendees_list}", flush=True)

    # 참석자 이름 리스트 생성
    attendee_names = ", ".join([a.get("name", "") for a in attendees_list])
    # 회의 원문 텍스트 전체 생성 (청크 경계 포함)
    meeting_text = "\n".join(full_meeting_sentences)
    # 할일 리스트 추출 (Action + context)
    todos = output.get("todos", []) if isinstance(output, dict) else []

    # 프롬프트 생성
    prompt = build_role_assignment_prompt(subject, agenda, attendees_list, todos, meeting_text)
    
    # 기본 JSON 구조 (파싱 실패 시 사용)
    default_result = {"assigned_todos": []}
    
    # agent 실행 (비동기, 파싱 오류 자동 처리)
    try:
        result = await agent.ainvoke({"input": prompt}, handle_parsing_errors=True)
        
        # result에서 출력 추출
        if isinstance(result, dict):
            if "output" in result:
                agent_output = result["output"]
            elif "result" in result:
                agent_output = result["result"]
            else:
                agent_output = str(result)
        else:
            agent_output = str(result)
            
        print("[assign_roles] agent_output:", agent_output, flush=True)
        
        # agent_output이 유효하지 않은 경우 처리
        if not agent_output or agent_output.strip() in ["I now know the final answer.", "", "None"]:
            print(f"[assign_roles] Agent가 유효하지 않은 출력 반환, 기본값 사용", flush=True)
            result_json = default_result
        else:
            # JSON 파싱 시도
            try:
                agent_output = agent_output.strip()
                if agent_output.startswith("```json"):
                    agent_output = agent_output.removeprefix("```json").removesuffix("```").strip()
                
                # JSON 패턴 찾기
                match = re.search(r'\{.*\}', agent_output, re.DOTALL)
                if match:
                    json_content = match.group()
                    result_json = json.loads(json_content)
                    
                    # assigned_todos 키가 없으면 추가
                    if "assigned_todos" not in result_json:
                        result_json["assigned_todos"] = []
                else:
                    print(f"[assign_roles] JSON 패턴을 찾을 수 없음, 기본값 사용", flush=True)
                    result_json = default_result
                    
            except json.JSONDecodeError as e:
                print(f"[assign_roles] JSON 파싱 오류: {e}, 기본값 사용", flush=True)
                result_json = default_result
                
    except Exception as e:
        print(f"[assign_roles] Agent 실행 오류: {e}, 기본값 사용", flush=True)
        result_json = default_result

    # schedule 항목 추가: action/context가 일치하는 output['todos']에서 schedule을 찾아서 넣기
    if result_json.get("assigned_todos") and todos:
        for assigned in result_json["assigned_todos"]:
            action = assigned.get("action", "")
            context = assigned.get("context", "")
            matched = next((t for t in todos if t.get("action", "") == action and t.get("context", "") == context), None)
            assigned["schedule"] = matched.get("schedule", "") if matched else ""

    # 최종 반환값 - 반드시 dict 형태로 보장
    return {
        "subject": subject,
        "attendees": attendees_list,
        "output": output,
        "assigned_roles": result_json,  # 항상 dict 형태 보장
        "agenda": agenda,
        "meeting_date": meeting_date
    } 