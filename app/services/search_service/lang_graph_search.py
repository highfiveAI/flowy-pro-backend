import asyncio
import aiohttp
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SerpAPIWrapper
from langgraph.graph import StateGraph, END
from langgraph.pregel import Pregel
from app.core.config import settings
from app.schemas.search import SearchState

openai_api_key = settings.OPENAI_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

if not openai_api_key or not serperapi_api_key:
    print("Warning: API keys not loaded.")

# 1. 환경 설정 및 LLM 초기화
search = SerpAPIWrapper()
llm = ChatOpenAI(temperature=0)

# 2. 도구 정의
@tool(description="Check if a URL is valid and reachable")
async def check_link_validity(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=5) as resp:
                if resp.status == 200:
                    return url
                else:
                    return ""
    except Exception:
        return ""

@tool(description="Search and extract links using SerpAPI")
async def search_and_extract_links(query: str) -> list[str]:
    try:
        results = await asyncio.to_thread(search.results, query)
        return [r.get("link") for r in results.get("organic_results", []) if r.get("link")]
    except Exception:
        return []

# 3. 그래프 노드 정의
async def search_node(state):
    query = state["query"]
    links = await search_and_extract_links.ainvoke(query)
    return {"links": links}

async def validate_node(state):
    links = state.get("links", [])
    results = await asyncio.gather(*[check_link_validity.ainvoke(link) for link in links])
    return {"valid_links": [link for link in results if link]}

# 4. 그래프 구성
graph = StateGraph(state_schema=SearchState)
graph.add_node("search", search_node)
graph.add_node("validate", validate_node)

graph.set_entry_point("search")
graph.add_edge("search", "validate")
graph.add_edge("validate", END)

search_graph = graph.compile()

# 5. 실행 예시
async def run():
    result = await search_graph.ainvoke({"query": "filetype:pdf resume template"})
    print("\n✅ 유효한 링크 결과:")
    for link in result.get("valid_links", []):
        print(link)

if __name__ == "__main__":
    asyncio.run(run())