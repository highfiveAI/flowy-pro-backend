from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings
# from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.agent_toolkits import create_retriever_tool
# from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
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
tools = []

system_message = """
You are an intelligent agent designed to interact with a vector database and provide context-aware responses.
When you receive a user question, you must first use the `search_similar_scenarios` tool to search for relevant scenarios.
If no relevant results are found using the tool, you should then generate an appropriate and helpful response using your own knowledge based on the user's question.
You should not return empty strings (e.g., "") in the response.
All fields must include meaningful, non-empty values.
"""

description = (
    "Use semantic similarity search to retrieve the single most relevant entry from the vector database. "
    "You must execute this exactly once per input — no more, no less. For each search, retrieve only a single tuple from the database."
    "You must always include document content and metadata in your final answer."
)

suffix = """\
When searching for information related to the user’s query, always use the `search_similar_scenarios` tool.
You must execute this tool **exactly once per input** — no more, no less.
For each search, retrieve **only a single tuple** from the database.
You must always include both the document content and metadata in your final answer.

The contents of the `results` array must **only** include the data retrieved from the `search_similar_scenarios` tool.
Do **not** generate or fabricate any content inside the `results` array.
Do not include any data in the `results` array that does not exist in the vector database.
Never fabricate or hallucinate content in the `results` array — it must only contain actual retrieved data.

Your own response as a language model must be placed **only** inside the `llm_summary` field.
This is where you summarize, explain, or guide the user in natural language.

If the user asks an unclear, irrelevant, or nonsensical question, still do your best to generate a helpful and appropriate response in the `llm_summary` field.

You are an API responder. You must **always** output a valid JSON string inside a Markdown code block using ```json.

The JSON must contain:
- A `results` array, with at least one object having `document` and (optionally) `metadata.link`.
- A `llm_summary` field that contains your natural language explanation.

Rules:
- Use **double quotes only**. Never use single quotes in keys or string values.
- Do **not** include any text before or after the code block.
- The JSON must be valid and parsable with `JSON.parse()` in JavaScript.
- If Error occurs, return the error message in the `llm_summary` field. Do not return in the `results` array.

Output format example:

```json
{
  "results": [
    {
      "document": "only document",
      "metadata": {
        "link": "https://example.com"
      }
    }
  ],
  "llm_summary": "이 문서는 사용자의 질문에 관련된 정보를 담고 있습니다."
}
"""

system = f"{system_message}\n\n{suffix}"

# 3. 검색용 retriever 객체
retriever = vector_store.as_retriever(search_kwargs={"k": 1})


def custom_retriever_tool(query: str) -> str:
      # 유사도 검색 + 점수 포함
    results_with_score = vector_store.similarity_search_with_score(query=query, k=1)

    if not results_with_score:
        return json.dumps({"results": []}, ensure_ascii=False)

    doc, score = results_with_score[0]
    print(f"🔎 유사도 점수: {score:.3f}")

    THRESHOLD = 0.88  # 유사도 기준
    if score > THRESHOLD:
        return json.dumps({"results": []}, ensure_ascii=False)

    return json.dumps({
        "results": [{
            "document": doc.page_content,
            "metadata": doc.metadata,
        }]
    }, ensure_ascii=False, indent=2)

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

async def run_agent(query: str):
    if retriever_tool not in tools:
        tools.append(retriever_tool)
    agent = create_react_agent(llm, tools, prompt=system)
    last_response = None
    # docs = retriever.get_relevant_documents("What are my options in breathable fabric?")

    # for doc in docs:
    #     print("📄 Document:", doc.page_content)
    #     print("🧾 Metadata:", doc.metadata)  # 여기에 'cmetadata'가 포함되어야 합니다
    for step in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
       step["messages"][-1].pretty_print()
       last_response = step["messages"][-1].content
    
    return last_response