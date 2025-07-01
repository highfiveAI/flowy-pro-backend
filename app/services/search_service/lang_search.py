import asyncio
import aiohttp
from langchain.tools import tool
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.utilities import SerpAPIWrapper
# from langchain_openai import ChatOpenAI
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
# openai_api_key = settings.OPENAI_API_KEY
google_api_key = settings.GOOGLE_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

# if not openai_api_key or not serperapi_api_key:
if not google_api_key or not serperapi_api_key:
    print("Warning: API keys not loaded.")

search = SerpAPIWrapper()

# llm = ChatOpenAI(temperature=0)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=5,
    # other params...
)

system_message = """
You are a search agent.
Your task is to take an input keyword and use a search tool to retrieve relevant links.
After retrieving links, return only the verified and reachable ones.
Do not fabricate or guess URLs.
"""

suffix = """
Search the given keyword and provide 1 relevant links.
Filter type: pdf.

Use the function `search_and_extract_links` with a single keyword string.
Return only one pdf link.
Return the result in the following format:

"https://example.com"
"""

system = f"{system_message}\n\n{suffix}"

search_description="Tool to search and extract link"
validate_description="Check if a URL is valid and reachable"

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

@tool(description=search_description)
def search_and_extract_links(keywords: str) -> str:
    keyword_list = [k.strip() for k in keywords.split(",")]
    results = {}

    for keyword in keyword_list:
        try:
            serp_results = search.results(keyword)
            links = [
                r.get("link")
                for r in serp_results.get("organic_results", [])
                if r.get("link")
            ]
            results[keyword] = links or ["링크를 찾을 수 없습니다."]
        except Exception as e:
            results[keyword] = [f"검색 중 오류 발생: {e}"]

    # 결과 문자열 포맷
    output = []
    for k, v in results.items():
        output.append(f"{k}:\n" + "\n".join(v))
    return "\n\n".join(output)

check_link_validity_tool = Tool.from_function(
    name="check_link_validity",
    description=validate_description,
    func=check_link_validity,
)

tools = [search_and_extract_links]

async def run_single_keyword_search(keyword: str) -> str:
  # 리액트 에이전트 생성
    agent = create_react_agent(llm, tools, prompt=system)

    last_response = None
    for step in agent.stream(
        {"messages": [{"role": "user", "content": keyword}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()
        last_response = step["messages"][-1].content

    return last_response

if __name__ == "__main__":
    keyword = "이력서 양식"
    result = asyncio.run(run_single_keyword_search(keyword))
    print(result)