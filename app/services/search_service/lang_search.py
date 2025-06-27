import asyncio
import aiohttp
from langchain.tools import tool
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.utilities import SerpAPIWrapper
# from langchain_openai import ChatOpenAI
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI

# openai_api_key = settings.OPENAI_API_KEY
google_api_key = settings.GOOGLE_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

# if not openai_api_key or not serperapi_api_key:
if not google_api_key or not serperapi_api_key:
    print("Warning: API keys not loaded.")

search = SerpAPIWrapper()

@tool(description="Check if a URL is valid and reachable")
async def check_link_validity(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=5) as resp:
                if resp.status == 200:
                    return f"Valid: {url}"
                else:
                    return f"Invalid ({resp.status}): {url}"
    except Exception as e:
        return f"Invalid (error): {url} - {e}"


@tool(description="Tool to search and extract links using SerpAPI")
async def search_and_extract_links(query: str) -> str:
    try:
        results = await asyncio.to_thread(search.results, query)
        links = [r.get("link") for r in results.get("organic_results", []) if r.get("link")]
        return "\n".join(links or ["링크를 찾을 수 없습니다."])
    except Exception as e:
        return f"검색 중 오류 발생: {e}"

tools = [search_and_extract_links, check_link_validity]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

async def run_langchain_search(query: str) -> str:
    print(f"Running agent with query: {query}")
    response = await agent.ainvoke({"input": query})  # 또는 await agent.ainvoke(query)
    print(f"Agent response: {response}")
    return response

if __name__ == "__main__":
    asyncio.run(run_langchain_search("filetype:pdf 이력서 양식 2개의 주소값을 결과값으로 가져와"))
