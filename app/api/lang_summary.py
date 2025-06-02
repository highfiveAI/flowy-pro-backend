from langchain_openai import ChatOpenAI
import datetime

def lang_summary(subject, chunks, tag_result):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 점수 1~3인 문장만 추출
    filtered_tag = [
        s for s in tag_result if isinstance(s, dict) and s.get("score", 0) > 0
    ]
    # 점수 0인 문장은 문맥 파악용
    context_only = [
        s for s in tag_result if isinstance(s, dict) and s.get("score", 0) == 0
    ]

    # 오늘 날짜와 이번주 범위 계산
    today = datetime.date.today()
    today_str = today.strftime('%Y.%m.%d(%a)')
    week_start = today - datetime.timedelta(days=today.weekday())
    week_end = week_start + datetime.timedelta(days=6)
    week_range_str = f"{week_start.strftime('%Y.%m.%d(%a)')} ~ {week_end.strftime('%Y.%m.%d(%a)')}"

    # 프롬프트: json 구조로만 반환하도록 명확히 지시
    prompt = f"""
    너는 회의록 작성 전문가야.

    회의 주제: {subject}

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
    - 날짜 계산이 애매하면 반드시 오늘 날짜({today_str}) 기준으로 표기해.

    **반드시 아래와 같은 JSON 구조로만 결과를 만들어줘.**
    ```json
    {{
      "회의 정리": ["..."],
      "기능 설계 및 개발 계획": ["..."],
      "보안 및 사용자 경험": ["..."],
      "개발 일정 및 협업": ["..."],
      "팀원들의 확장 욕구 및 사이드 프로젝트 제안": ["..."]
    }}
    ```
    항목명, 항목 개수, 순서 등은 회의 내용에 맞게 자유롭게 정해도 되지만 반드시 JSON 구조로만 반환해.
    """

    response = llm.invoke(prompt)
    agent_output = response.content

    print("[lang_summary] agent_output:", agent_output, flush=True)
    return {
        "agent_output": agent_output,
        "tag_result": filtered_tag
    } 