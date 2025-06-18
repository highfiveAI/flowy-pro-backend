import asyncio
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_community.utilities import SerpAPIWrapper
from langchain_openai import ChatOpenAI
from app.core.config import settings
from concurrent.futures import ThreadPoolExecutor

# API 키 설정
openai_api_key = settings.OPENAI_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

if not openai_api_key or not serperapi_api_key:
    print("Warning: API keys not loaded.")

# SerpAPI 검색 도구 초기화
search = SerpAPIWrapper()

async def search_and_extract_links(query: str) -> str:
    """SerpAPI를 통해 검색하고 링크 추출"""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, search.results, query)
        links = [r.get("link") for r in results.get("organic_results", []) if r.get("link")]
        return "\n".join(links or ["링크를 찾을 수 없습니다."])
    except Exception as e:
        return f"검색 중 오류 발생: {e}"

# 동기 래퍼 함수 (Tool은 동기 함수만 허용됨)
def sync_search_and_extract_links(query: str) -> str:
    return asyncio.run(search_and_extract_links(query))

# 도구 설정
tools = [
    Tool(
        name="Web Search",
        func=sync_search_and_extract_links,  # Tool은 동기 함수만 가능
        description="Use this tool to search the web for current information"
    )
]

# LLM 및 에이전트 초기화
llm = ChatOpenAI(temperature=0)

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

async def run_langchain_search(query: str) -> str:
    """Langchain 에이전트를 비동기로 실행"""
    print(f"Running agent with query: {query}")
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, agent.run, query)
    print(f"Agent response: {response}")
    return response

# 모듈이 직접 실행될 때만 테스트
if __name__ == "__main__":
    async def main():
        test_query = "filetype:pdf 이력서 양식 2개의 주소값을 결과값으로 가져와"
        search_result = await run_langchain_search(test_query)
        print("\n[검색 결과 요약]")
        print(search_result)

    asyncio.run(main())
