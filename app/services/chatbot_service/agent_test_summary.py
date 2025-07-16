from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

google_api_key = settings.GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=5,
    google_api_key=google_api_key,
)

# 문서 로드
loader = WebBaseLoader(
    web_path="https://example.com",
    requests_kwargs={
        "headers": {
            "User-Agent": "Mozilla/5.0 (compatible; FlowyBot/1.0)"
        }
    }
)
docs = loader.load()
if not docs:
    raise ValueError("문서를 불러오지 못했습니다.")

print(type(docs[0]))
print(docs[0])

filtered_docs = [doc for doc in docs if doc.page_content.strip() and len(doc.page_content.strip()) > 50]
if not filtered_docs:
    raise ValueError("쓸 수 있는 문서 내용이 없습니다.")

# context를 입력 변수로 받는 prompt
prompt = ChatPromptTemplate.from_messages(
    [("system", "Write a concise summary of the following:\n\n{context}")]
)

# chain 생성
chain = create_stuff_documents_chain(llm, prompt)

# context에 Document 리스트 전달
result = chain.invoke({"context": filtered_docs})

print(result)
