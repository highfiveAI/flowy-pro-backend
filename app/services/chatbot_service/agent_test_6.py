from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings
# from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.agent_toolkits import create_retriever_tool
# from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
from langchain_core.messages import AIMessage
import asyncio
import json

google_api_key = settings.GOOGLE_API_KEY
CONNECTION_STRING = settings.SYNC_CONNECTION_STRING

# 1. 임베딩 모델 준비
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")
# 2. PGVector에 연결
vector_store = PGVector(
    collection_name="scenarios", 
    connection=CONNECTION_STRING,
    embeddings=embeddings, 
)


# db = SQLDatabase.from_uri(CONNECTION_STRING)

if not google_api_key:
    print("Warning: API keys not properly loaded.")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=5,
    google_api_key=google_api_key,
)

# toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# tools = toolkit.get_tools()


system_message = """
You are Flowy AI Chatbot. Always keep this in mind.  
You are an intelligent agent designed to interact with a vector database and provide context-aware responses.
When you receive a user question, you must first use the `search_similar_scenarios` tool to search for relevant scenarios.
You must provide appropriate responses based on the results obtained from using the `search_similar_scenarios` tool.
If no relevant results are found using the tool, you should then generate an appropriate and helpful response using your own knowledge based on the user's question.
You should not return empty strings (e.g., "") in the response.
All responses must be in plain text format only - never return JSON, objects, or structured data.
"""

description = (
    "Use semantic similarity search to retrieve the single most relevant entry from the vector database. "
    "You must execute this exactly once per input — no more, no less. For each search, retrieve only a single tuple from the database."
)

suffix = """
CRITICAL INSTRUCTIONS FOR RESPONSE FORMAT:
- You must NEVER return JSON format responses
- You must NEVER use code blocks (```)  
- You must NEVER return structured data or objects
- ALWAYS return responses as plain text strings only

When searching for information related to the user's query, always use the `search_similar_scenarios` tool.
You must execute this tool **exactly once per input** — no more, no less.
For each search, retrieve **only a single tuple** from the database.

Never fabricate or hallucinate content in your response — it must only contain actual retrieved data combined with your natural language explanation.

Provide your complete response as a single plain text string that includes:
- The relevant information retrieved from the database
- Your natural language explanation, summary, or guidance
- Any helpful context or clarification for the user

RESPONSE FORMAT RULES:
- Return ONLY plain text - no JSON, no code blocks, no structured formats
- Write naturally as if speaking to the user directly
- Combine retrieved data with explanatory text in a conversational manner
- If an error occurs, explain the issue in plain text
- Base your response on actual retrieved data, don't fabricate information

Example of correct response format:
"Based on the information I found, here's what I can tell you about your question... [explanation and guidance in natural language]"
"""

system = f"{system_message}\n\n{suffix}"

# 3. 검색용 retriever 객체
retriever = vector_store.as_retriever(search_kwargs={"k": 1})


def custom_retriever_tool(query: str) -> str:
    # 유사도 검색 + 점수 포함
    results_with_score = vector_store.similarity_search_with_score(query=query, k=1)

    if not results_with_score:
        return "검색 결과를 찾을 수 없습니다."

    doc, score = results_with_score[0]
    print(f"🔎 유사도 점수: {score:.3f}")

    THRESHOLD = 0.88  # 유사도 기준
    if score > THRESHOLD:
        return "관련된 정보를 찾을 수 없습니다. 다른 키워드로 검색해보세요."

    # 메타데이터에서 링크 정보 추출 (있는 경우)
    link_info = ""
    if hasattr(doc, 'metadata') and doc.metadata:
        if 'link' in doc.metadata:
            link_info = f"\n참고 링크: {doc.metadata['link']}"
        elif 'source' in doc.metadata:
            link_info = f"\n출처: {doc.metadata['source']}"

    # 플레인 텍스트로 결과 반환
    return f"{doc.page_content}{link_info}"

# retriever_tool = create_retriever_tool(
#     retriever,
#     name="search_similar_scenarios",
#     description=description,
# )

retriever_tool = Tool.from_function(
    name="search_similar_scenarios",
    description=description,
    func=custom_retriever_tool
)

tools = [retriever_tool]

async def run_agent_stream(query: str, debug: bool = True):
    agent = create_react_agent(llm, tools, prompt=system)
    last_response = ""
    prev_messages = []  # 이전 메시지 누적용

    async for step in agent.astream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
        messages = step.get("messages", [])

        # 디버그 모드: 새 메시지만 출력
        if debug:
            new_messages = messages[len(prev_messages):]
            for msg in new_messages:
                msg.pretty_print()
            prev_messages = messages  # 갱신

        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                content = last_msg.content
                if content and content != last_response:
                    new_part = content[len(last_response):]
                    for char in new_part:
                        yield f"data: {char}\n\n"
                        if not debug:
                            print(char, end="", flush=True)
                        await asyncio.sleep(0.02)
                    last_response = content