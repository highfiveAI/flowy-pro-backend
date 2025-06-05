import requests
from io import BytesIO
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain.schema import Document
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

connection_input_string = os.getenv("CONNECTION_STRING")
# 1. PDF 링크들
pdf_links = [
    "https://mac.inup.co.kr/main/download.jsp?id=1069091&ek=a14fb25ca02cc603895ff8360c9cd1f3"
]

all_documents = []

# 2. PDF 가져와서 텍스트 추출
for link in pdf_links:
    response = requests.get(link)
    pdf_file = BytesIO(response.content)
    reader = PdfReader(pdf_file)

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text

    # LangChain Document 객체로 변환
    doc = Document(
        page_content=full_text,
        metadata={"source": link}
    )
    all_documents.append(doc)

# 3. 문서 분할
splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
split_docs = splitter.split_documents(all_documents)

# 4. 임베딩 모델
embedding_model = OpenAIEmbeddings()  # 또는 HuggingFaceEmbeddings

# 5. PGVector에 저장


vectorstore = PGVector.from_documents(
    documents=split_docs,
    embedding=embedding_model,
    connection_string=connection_input_string,
    collection_name="test3"  # 테이블/컬렉션 이름
)

# 6. 테스트 검색
retriever = vectorstore.as_retriever()
results = retriever.invoke("자기소개서에서 필요하는 내용 찾아줘")

for doc in results:
    print("🔹", doc.metadata["source"])
    print(doc.page_content[:200], "\n---\n")
