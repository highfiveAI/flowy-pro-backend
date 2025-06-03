# 역할 분배 agent (lang_role.py)
from langchain_openai import ChatOpenAI
import json

def assign_roles(subject, chunks, attendees_list, tag_result):
    """
    subject: 회의 주제 (str)
    attendees_list: [{'name': ..., 'email': ..., 'role': ...}, ...]
    tag_result: tagging.py에서 반환된 태깅 결과(dict)
    """
    print(f"[assign_roles] 전달받은 subject: {subject}", flush=True)
    print(f"[assign_roles] 전달받은 attendees_list: {attendees_list}", flush=True)
    print(f"[assign_roles] 전달받은 tag_result: {tag_result}", flush=True)
    print(f"[assign_roles] 전달받은 chunks: {chunks}", flush=True)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 참석자 이름 리스트 생성
    attendee_names = ", ".join([a.get("name", "") for a in attendees_list])
    # 회의 텍스트 전체 생성 (중요 문장만 합침)
    meeting_text = "\n".join([s["sentence"] for s in tag_result if isinstance(s, dict) and s.get("sentence")])

    prompt = f"""
    너는 회의록 분석을 통해 참석자별 역할을 분배하는 AI Assistant야.

    [회의 주제]
    {subject}

    [참석자]
    {attendee_names}

    [회의 내용]
    {meeting_text}

    [역할분배 기준]
    1️⃣ 실제 업무 실행이 필요한 발언이 나온 경우 → 해당 참석자에게 역할로 배정
    2️⃣ 의견 제시, 아이디어 제안 → 담당자 또는 실행 담당자에게 할당
    3️⃣ 직접 실행을 맡겠다고 한 경우 → 해당 참석자에게 명확하게 할당
    4️⃣ 명확하지 않은 경우에는 '추가 확인 필요'로 표시

    [출력 형식 예시]
    ```json
    {{
      "역할분배": [
        {{
          "참석자": "홍길동",
          "역할": "서비스 UI 개선안 구체화 및 디자인 시안 작성",
          "비고": ""
        }},
        {{
          "참석자": "김철수",
          "역할": "백엔드 API 성능 개선 테스트",
          "비고": "추가 확인 필요"
        }}
      ]
    }}
    ```
    반드시 위와 같은 JSON 구조로만 결과를 만들어줘.
    """

    response = llm.invoke(prompt)
    agent_output = response.content
    print("[assign_roles] agent_output:", agent_output, flush=True)

    # JSON 파싱 시도
    try:
        # 코드블록 제거
        if agent_output.strip().startswith("```json"):
            agent_output = agent_output.strip().removeprefix("```json").removesuffix("```")
        result_json = json.loads(agent_output)
    except Exception as e:
        print(f"[assign_roles] JSON 파싱 오류: {e}", flush=True)
        result_json = {"역할분배": [], "error": str(e), "raw": agent_output}

    return {
        "subject": subject,
        "attendees": attendees_list,
        "tag_result": tag_result,
        "assigned_roles": result_json
    } 