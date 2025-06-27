# agent_core.py

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

google_api_key = settings.GOOGLE_API_KEY
serperapi_api_key = settings.SERPAPI_API_KEY

if not google_api_key or not serperapi_api_key:
    print("⚠️ Warning: API keys not properly loaded.")

chat_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=google_api_key,
)

@tool(description="Handles common scenario-based queries. Examples: business hours, shipping status, refund process.")
async def scenario_tool_func(user_input: str) -> str:
    SCENARIO_RESPONSES = {
        "운영시간": "저희 운영시간은 평일 오전 9시부터 오후 6시까지입니다.",
        "배송 조회": "주문번호를 입력해 주시면 배송 상태를 알려드릴게요.",
        "환불": "환불 절차를 도와드릴게요. 주문 번호를 입력해 주세요.",
    }
    for keyword, response in SCENARIO_RESPONSES.items():
        if keyword in user_input:
            return response
    return "No matching scenario response was found."

@tool(description="Ask me questions that would prompt me to say I didn't understand what the user was saying, or to ask if I was asking for a tracking or hours of operation. answer must be korean")
async def ai_tool_func(user_input: str) -> str:
    res = await chat_model.ainvoke(user_input)
    return res.content

agent = initialize_agent(
    tools=[scenario_tool_func, ai_tool_func],
    llm=chat_model,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)