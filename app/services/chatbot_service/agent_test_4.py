import asyncio
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI
from app.core.config import settings

google_api_key = settings.GOOGLE_API_KEY
# openai_api_key = settings.OPENAI_API_KEY
# 모델, 프롬프트, 파서 설정
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=google_api_key)
# model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=openai_api_key)
prompt = ChatPromptTemplate.from_template("tell me a joke about {topic}")
parser = StrOutputParser()

# 체인 구성
chain = prompt | model | parser

# 비동기 실행 함수 정의
async def main():
    async for event in chain.astream_events({"topic": "parrot"}):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            print(event, end="|", flush=True)
            await asyncio.sleep(0.03)

# 엔트리 포인트
if __name__ == "__main__":
    asyncio.run(main())
