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
Your task is to take a list of input keywords and use a search tool to retrieve relevant links.
After retrieving links, use a verification tool to check whether each link is valid and correctly formatted.

Only return links that have been successfully verified.
Do not fabricate or guess URLs.
Always ensure the returned links are accurate, reachable, and relevant to the given keywords.
If no valid links are found, clearly state that no suitable results were retrieved.

You must begin by performing the search using the provided keywords.
Then, validate the results before returning them.
Never skip the validation step.
""".format()

suffix = """
Search each of the following keywords and provide 2 links per keyword.
filter type: pdf
Use the function search_and_extract_links with the following format for the input parameter.
{keyword1, keyword2 ...}
After performing the search, return the results in the following format:
result {
    keyword1: {links...},
    keyword2: {links...},
    ...
}
"""

system = f"{system_message}\n\n{suffix}"

search_description="Tool to search and extract links from comma-separated keywords"
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



# agent = initialize_agent(
#     tools,
#     llm,
#     agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#     verbose=True
# )

async def run_batch_keyword_search(keywords: list[str]) -> dict:
    agent = create_react_agent(llm, tools, prompt=system)
    # results = {}
    # prompt = f"Search each of the following keywords and provide 2 links per keyword. filter type: pdf: {', '.join(keywords)}"
    # print(f"🤖 에이전트에 요청: {prompt}")

    # try:
    #     response = await agent.ainvoke({"input": prompt})
    #        #  Gemini 계열은 output 키 안에 있음
    #     text = response["output"].strip() if isinstance(response, dict) and "output" in response else str(response).strip()
    #     sections = text.split('\n\n')
    #     for section in sections:
    #         lines = section.strip().split('\n')
    #         if not lines:
    #             continue
    #         key = lines[0].rstrip(':').strip()
    #         links = [line.strip() for line in lines[1:] if line.strip()]
    #         results[key] = links or ["링크를 찾을 수 없습니다."]
    # except Exception as e:
    #     for keyword in keywords:
    #         results[keyword] = [f"검색 중 오류 발생: {e}"]
    last_response = None
    for step in agent.stream(
        {"messages": [{"role": "user", "content": keywords}]},
        stream_mode="values",
    ):
       step["messages"][-1].pretty_print()
       last_response = step["messages"][-1].content
    
    return last_response

if __name__ == "__main__":
    keywords = ["이력서 양식", "자기소개서 템플릿"]
    result = asyncio.run(run_batch_keyword_search(keywords))
    print(result)