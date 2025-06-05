from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.chat_models import ChatOpenAI
from app.services.lang_search import run_langchain_search
from app.core.config import settings

openai_api_key = settings.OPENAI_API_KEY

# LLM 초기화
llm = ChatOpenAI(temperature=0)

# 하위 검색 에이전트 import


# 검색 도구로 등록할 함수
def smart_search(query: str) -> str:
    return run_langchain_search(query)

# 검색 도구 정의
search_tool = Tool(
    name="Web Search",
    func=smart_search,
    description="Use this tool to search for document templates like resumes, reports, or proposals."
)

# 상위 판단 함수: 문서 양식이 필요한지 여부를 LLM이 결정
def should_use_search_tool(meeting_text: str) -> bool:
    system_prompt = """
당신은 회의 분석 AI입니다. 아래 회의 내용을 읽고, 이 회의에서 문서 양식(예: 이력서 양식, 보고서 양식, 제안서 양식 등)을 외부에서 검색해야 할 필요가 있는지 판단하세요.

다음 중 하나라도 포함된다면 'Yes'라고 답하세요:
- 어떤 문서 양식을 찾으라는 지시가 있다
- 양식이 필요하다는 언급이 있다
- 문서 작성을 위해 참고 자료가 필요하다는 내용이 있다

단순히 회의 요약이나 업무 분배는 제외합니다.

'Yes' 또는 'No'만 출력하세요.
"""
    prompt = system_prompt + f"\n\n회의 내용:\n{meeting_text}"
    response = llm.predict(prompt)
    return "yes" in response.lower()

# 상위 에이전트 함수
def super_agent_for_meeting(meeting_text: str) -> str:
    print("[상위 에이전트] 회의 텍스트 분석 중...")

    # 판단: 검색할지 여부
    if should_use_search_tool(meeting_text):
        print("[상위 에이전트] 문서 양식 검색 필요 판단됨.")
        
        # 검색 키워드 추출 프롬프트
        extract_prompt = f"""
다음 회의 내용을 기반으로 필요한 문서 양식을 검색하기 위한 검색 키워드를 작성한 후, 해당 키워드로 실제 검색하여 관련 문서 링크를 포함한 문장을 작성해주세요.

**주의:** 결과 문장은 반드시 하나 이상의 실제 링크(URL)를 포함해야 하며, "해결 방법이 존재할 수 있습니다" 같은 일반적인 문구는 사용하지 마세요.

예시:
- 검색 키워드: "filetype:pdf 제안서 양식"
- 결과: 제안서 양식을 참고할 수 있는 링크는 다음과 같습니다: https://example.com/proposal-template.pdf

회의 내용:
{meeting_text}
"""
        keyword = llm.predict(extract_prompt)
        print(f"[상위 에이전트] 검색 키워드: {keyword}")

        # 실제 검색 수행
        return smart_search(keyword)
    else:
        return "이 회의에서는 문서 양식을 검색할 필요가 없습니다."

# 테스트용 실행 코드
if __name__ == "__main__":
    sample_meeting = """
이번 주 금요일까지 마케팅 전략 보고서를 작성해야 합니다. 이전 팀에서 사용했던 보고서 양식이 괜찮아 보였어요.
혹시 참고할 만한 보고서 템플릿이 있으면 공유 부탁드립니다.
"""
    result = super_agent_for_meeting(sample_meeting)
    print("\n[최종 응답]")
    print(result)
