from langchain_openai import ChatOpenAI

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

    # 구조화된 요약 프롬프트
    prompt = f"""
    너는 회의록 작성 전문가야.

    회의 주제: {subject}

    아래는 회의에서 중요한 문장(점수 1~3)만 추린 리스트야:
    {filtered_tag}

    이 문장들을 참고해서, 회의 내용을 적절한 구조(예: 주요 논의사항, 결정사항, 추후 과제 등)로 정리해줘.
    각 구조(섹션)는 회의 내용을 가장 잘 설명할 수 있도록 네가 판단해서 만들어.
    각 섹션별로 관련 문장(또는 요약)을 넣어줘.

    출력 예시:
    ## 주요 논의사항
    - 내용1
    - 내용2

    ## 결정사항
    - 내용1

    ## 추후 과제
    - 내용1

    점수 0인 문장은 참고만 하고, 요약 내용에는 넣지 마.
    """

    response = llm.invoke(prompt)
    agent_output = response.content

    print("[lang_summary] agent_output:", agent_output, flush=True)
    return {
        "agent_output": agent_output,
        "tag_result": filtered_tag
    } 