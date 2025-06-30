from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
import asyncio

# 1. 임베딩 모델 준비
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")
# 2. PGVector에 연결
vector_store = PGVector(
    collection_name="scenarios", 
    connection="postgresql+psycopg2://postgres:0587@localhost:5432/postgres",
    embeddings=embeddings, 
)

google_api_key = settings.GOOGLE_API_KEY
db = SQLDatabase.from_uri("postgresql+psycopg2://postgres:0587@localhost:5432/postgres")

if not google_api_key:
    print("Warning: API keys not properly loaded.")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=google_api_key,
)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()

system_message = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect,
    top_k=5,
)

description = (
    "Use semantic similarity search to retrieve the single most relevant entry from the vector database. "
    "This must be done once per input"
)

suffix = (
    "When searching for information related to the user’s query, always use the search_similar_scenarios tool "
    "at least once to retrieve relevant and similar content before answering."
    "If you find a suitable result using the search_similar_scenarios tool, you may conclude your response without using any other tools."
)

system = f"{system_message}\n\n{suffix}"

# 3. 검색용 retriever 객체
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

retriever_tool = create_retriever_tool(
    retriever,
    name="search_similar_scenarios",
    description=description,
)

async def run_agent(query: str):
    if retriever_tool not in tools:
        tools.append(retriever_tool)
    agent = create_react_agent(llm, tools, prompt=system)
    for step in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()


# 5. 실행 예시
if __name__ == "__main__":
    query = "아 집가고 싶다"
    asyncio.run(run_agent(query))
