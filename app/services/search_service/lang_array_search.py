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


@tool(description="Tool to search and extract links from comma-separated keywords")
async def search_and_extract_links(keywords: str) -> str:
    keyword_list = [k.strip() for k in keywords.split(",")]
    results = {}

    for keyword in keyword_list:
        try:
            serp_results = await asyncio.to_thread(search.results, keyword)
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

tools = [search_and_extract_links, check_link_validity]

# llm = ChatOpenAI(temperature=0)
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

async def run_batch_keyword_search(keywords: list[str]) -> dict:
    results = {}
    prompt = f"Search each of the following keywords and provide 2 links per keyword. filter type: pdf: {', '.join(keywords)}"
    print(f"🤖 에이전트에 요청: {prompt}")

    try:
        response = await agent.ainvoke({"input": prompt})
           # ✅ Gemini 계열은 output 키 안에 있음
        text = response["output"].strip() if isinstance(response, dict) and "output" in response else str(response).strip()

        # 예시 응답 형식 가정:
        # 이력서 양식:
        # https://link1
        # https://link2
        #
        # 자기소개서 템플릿:
        # https://link3
        # https://link4

        # 키워드별로 분리
        sections = text.split('\n\n')
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
            key = lines[0].rstrip(':').strip()
            links = [line.strip() for line in lines[1:] if line.strip()]
            results[key] = links or ["링크를 찾을 수 없습니다."]
    except Exception as e:
        for keyword in keywords:
            results[keyword] = [f"검색 중 오류 발생: {e}"]

    return results


async def run_langchain_search(query: str) -> str:
    print(f"Running agent with query: {query}")
    response = await agent.ainvoke({"input": query})  # 또는 await agent.ainvoke(query)
    print(f"Agent response: {response}")
    return response

if __name__ == "__main__":
    keywords = ["이력서 양식", "자기소개서 템플릿"]
    result = asyncio.run(run_batch_keyword_search(keywords))
    print(result)