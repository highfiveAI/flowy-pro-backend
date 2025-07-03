import asyncio
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

google_api_key = settings.GOOGLE_API_KEY

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=google_api_key
)
prompt = ChatPromptTemplate.from_template("tell me a joke about {topic}")
parser = StrOutputParser()
chain = prompt | model | parser

async def main():
    async for chunk in chain.astream({"topic": "parrot"}):
        for char in chunk:
            print(char, end="", flush=True)
            await asyncio.sleep(0.03)  # 30ms 텀을 줘서 "타자 치는 느낌" 구현

if __name__ == "__main__":
    asyncio.run(main())
