from langchain.chat_models import init_chat_model
from app.core.config import settings
from langgraph.checkpoint.memory import MemorySaver
# from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

serperapi_api_key = settings.SERPAPI_API_KEY
google_api_key = settings.GOOGLE_API_KEY

memory = MemorySaver()
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=5,
    google_api_key=google_api_key,
)
# search = TavilySearch(max_results=2)
search_wrapper = SerpAPIWrapper()  # you can pass k=2 to limit results
search = Tool.from_function(
    func=search_wrapper.run,
    name="Search",
    description="Search the web using SerpAPI. Useful for answering questions about current events or recent information."
)

tools = [search]
agent_executor = create_react_agent(model, tools, checkpointer=memory)

config = {"configurable": {"thread_id": "abc123"}}

# input_message = {
#     "role": "user",
#     "content": "Hi, I'm Bob and I life in SF.",
# }
# input_message = {
#     "role": "user",
#     "content": "What's the weather where I live?im living in south korea",
# }
input_message1 = {"role": "user", "content": "Hi, I'm Bob!"}
input_message2 = {"role": "user", "content": "What's my name?"}

for step in agent_executor.stream(
    {"messages": [input_message1]}, config, stream_mode="values"
):
    step["messages"][-1].pretty_print()

for step in agent_executor.stream(
    {"messages": [input_message2]}, config, stream_mode="values"
):
    step["messages"][-1].pretty_print()
# for step, metadata in agent_executor.stream(
#     {"messages": [input_message]}, config=config, stream_mode="messages"
# ):
#     if metadata["langgraph_node"] == "agent" and (text := step.text()):
#         print(text, end="|")