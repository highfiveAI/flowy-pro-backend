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

# Define prompt
prompt = ChatPromptTemplate.from_messages(
    [("system", "Write a concise summary of the following:\\n\\n{context}")]
)

# Instantiate chain
chain = create_stuff_documents_chain(llm, prompt)



# Invoke chain
# result = chain.invoke({"context": docs})
result = chain.invoke(docs)
print(result)