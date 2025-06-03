from langchain_community.chat_models import ChatOpenAI
from app.core.config import settings

def get_langchain_llm():
    return ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model_name="gpt-3.5-turbo")