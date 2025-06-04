from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_community.utilities import SerpAPIWrapper
from langchain_openai import ChatOpenAI
from app.core.config import settings

# API 키 설정
openai_api_key = settings.OPENAI_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

if not openai_api_key or not serperapi_api_key:
    # 실제 애플리케이션에서는 예외를 발생시키거나 로깅을 하는 것이 좋습니다.
    print("Warning: API keys not loaded.")

# SerpAPI 검색 도구 초기화 (모듈 로드 시점에 한 번만 실행)
search = SerpAPIWrapper()

def search_and_extract_links(query: str) -> str:
    """Searches the web using SerpAPI and extracts organic result links."""
    try:
        # SerpAPIWrapper().run(query)는 기본적으로 문자열 요약을 반환합니다.
        # 원시 JSON을 얻으려면 search.results(query)를 사용합니다.
        results = search.results(query)  # JSON 형태
        links = [r.get("link") for r in results.get("organic_results", []) if r.get("link")]
        return "\n".join(links or ["링크를 찾을 수 없습니다."])
    except Exception as e:
        return f"검색 중 오류 발생: {e}"

# 도구 설정 (모듈 로드 시점에 한 번만 실행)
tools = [
    Tool(
        name="Web Search",
        func=search_and_extract_links,
        description="Use this tool to search the web for current information"
    )
]

# LLM 및 에이전트 초기화 (모듈 로드 시점에 한 번만 실행)
llm = ChatOpenAI(temperature=0)

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def run_langchain_search(query: str) -> str:
    """Runs the initialized Langchain agent with the given query."""
    print(f"Running agent with query: {query}")
    response = agent.run(query)
    print(f"Agent response: {response}")
    return response

# 모듈이 직접 실행될 때만 테스트 코드를 실행
if __name__ == "__main__":
    test_query = "filetype:pdf 이력서 양식 2개의 주소값을 결과값으로 가져와"
    search_result = run_langchain_search(test_query)
    print("\n[검색 결과 요약]")
    print(search_result)
