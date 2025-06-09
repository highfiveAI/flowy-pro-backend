import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, AgentType, initialize_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
import psycopg2
from contextlib import contextmanager
import boto3
from botocore.exceptions import ClientError


# .env 파일 로드
load_dotenv()

# API 키 확인
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

# AWS 설정
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

# S3 클라이언트 초기화
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# DB 연결 정보
DB_CONFIG = {
    "host": settings.POSTGRES_HOST,
    "port": settings.POSTGRES_PORT,
    "database": settings.POSTGRES_DB,
    "user": settings.POSTGRES_USER,
    "password": settings.POSTGRES_PASSWORD
}

CONNECTION_STRING = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
# CONNECTION_STRING = settings.CONNECTION_STRING
@contextmanager
def get_db_connection():
    """데이터베이스 연결을 관리하는 컨텍스트 매니저"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

# 1. 임베딩 모델 초기화
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

# 2. pgvector 연결 (테이블 구조에 맞게 설정)
vectorstore = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="interdocs",
    embedding_function=embedding_model,
    pre_delete_collection=False,  # 기존 데이터 유지
    distance_strategy="cosine",  # 유사도 계산 방식
)

retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3, "score_threshold": 0.1}) # k=5로 변경

# 3. 문서 추천 툴 함수 정의 (직접 SQL 사용)
def direct_vector_search(query_text: str, k: int = 3):
    """직접 SQL로 벡터 유사도 검색"""
    try:
        # 쿼리 벡터화
        query_embedding = embedding_model.embed_query(query_text)
        
        # DB 연결 및 검색
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 벡터 유사도 검색 쿼리 (사용자 정보 포함)
                sql = """
                SELECT 
                    i.interdocs_id,
                    i.interdocs_filename,
                    i.interdocs_contents,
                    i.interdocs_path,
                    (i.interdocs_vector <=> %s::vector) as distance
                FROM interdocs i
                WHERE i.interdocs_vector IS NOT NULL
                ORDER BY i.interdocs_vector <=> %s::vector
                LIMIT %s
                """
                
                cursor.execute(sql, (query_embedding, query_embedding, k))
                results = cursor.fetchall()

        # 결과 포맷팅
        documents = []
        for row in results:
            doc_id, filename, content, path, distance = row
            documents.append({
                'interdocs_id': str(doc_id),
                'interdocs_filename': filename,
                'content': content,
                'interdocs_path': path,
                'similarity_score': 1 - distance
            })
            
        return documents
        
    except Exception as e:
        print(f"직접 벡터 검색 오류: {e}")
        return []

def get_document_download_link(s3_key: str) -> str:
    """S3에서 문서의 프리사인드 URL을 생성합니다."""
    try:
        if not s3_key:
            return "문서의 경로 정보가 없습니다."
            
        # 프리사인드 URL 생성 (1시간 유효)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': AWS_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=3600  # 1시간
        )
        return f"{url}"
    except ClientError as e:
        return f"다운로드 링크 생성 실패: {str(e)}"
    except Exception as e:
        return f"예상치 못한 오류 발생: {str(e)}"

def recommend_docs_from_role(role_text: str) -> str:
    try:
        # 툴 오용 방지: 파일명으로 검색하는 경우 차단
        if role_text.endswith(".hwp") or role_text.endswith(".docx"):
            return f"'{role_text}'는 파일명처럼 보입니다. 역할이나 업무 내용으로 입력해주세요."

        print(f"DEBUG: direct search for '{role_text}'")
        docs = direct_vector_search(role_text, k=3)
        print(f"DEBUG: Found {len(docs)} documents")
        
        if not docs:
            return "추천할 문서를 찾지 못했습니다."
            
        # result = ""
        # for i, doc in enumerate(docs, 1):
        #     doc_id = doc['interdocs_id']
        #     title = doc['interdocs_filename']
        #     similarity = doc['similarity_score']
        #     path = doc['interdocs_path']
        #     snippet = doc['content'][:200].strip().replace("\n", " ")
            
        #     # 다운로드 링크 생성
        #     download_link = get_document_download_link(path)
            
        #     result += f"{i}. 문서 ID: {doc_id}\n제목: {title}\n유사도: {similarity:.3f}\n내용 미리보기: {snippet}\n{download_link}\n\n"
        
        result_docs = []
        for i, doc in enumerate(docs, 1):
            doc_id = doc['interdocs_id']
            title = doc['interdocs_filename']
            similarity = doc['similarity_score']
            path = doc['interdocs_path']
            snippet = doc['content'][:200].strip().replace("\n", " ")
            
            # 다운로드 링크 생성
            download_link = get_document_download_link(path)
            
            result_docs.append({
                "id": doc_id,
                "title": title,
                "similarity": similarity,
                "preview": snippet,
                "download_url": download_link
            })
            
        return result_docs
            
            
        # return result
        
    except Exception as e:
        return f"문서 추천 중 오류 발생: {e}"

# 4. 에이전트용 툴 정의
tools = [
    Tool(
        name="RecommendInternalDocs",
        func=recommend_docs_from_role,
        description="""사용자의 역할 분담 내용에 따라 관련된 사내 문서를 한국어로 추천합니다. 
                     예: '회의록 작성', '신입 교육 자료', '경비 정산 규정' 등. 
                     절대 영어로 변환하지 말고, 한국어 그대로 툴의 인풋으로 전달해야 합니다."""
    ),
    Tool(
        name="GetDocumentDownloadLink",
        func=get_document_download_link,
        description="""S3 키를 받아 해당 문서의 다운로드 링크를 생성합니다.
                     입력 형식: "S3 키 경로" (예: "documents/example.pdf")"""
    )
]

# 5. LLM 및 에이전트 초기화
# 에이전트에게 한국어 사용을 명시적으로 지시하는 프롬프트 추가
llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0, model="gpt-3.5-turbo")

# 에이전트 프롬프트 구성
agent_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""당신은 FlowyPro의 사내 문서 추천 전문가입니다. 
                                    사용자의 질문에 대해 다음과 같은 순서로 작업을 수행합니다:
                                    1. RecommendInternalDocs 툴을 사용하여 관련 문서를 찾습니다.
                                    2. 문서를 찾으면, GetDocumentDownloadLink 툴을 사용하여 각 문서의 다운로드 링크를 생성합니다.
                                    
                                    모든 대화와 툴 사용은 한국어로 진행되어야 합니다.
                                    특히, RecommendInternalDocs 툴의 'role_text' 인풋은 절대 영어로 번역하지 말고,
                                    사용자가 입력한 한국어 내용을 그대로 전달해야 합니다.
                                    
                                    문서 추천을 찾지 못하면 사용자에게 다른 검색어를 제안하거나 직접 문의할 수 있습니다."""),
    HumanMessage(content="{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True, # 파싱 오류 처리
    agent_kwargs={
        "prompt": agent_prompt, # 정의한 프롬프트 사용
    }
)

# 6. 실행 함수 정의
def run_doc_recommendation(query: str) -> str:
    print(f"\n[입력된 역할 분담 내용]\n{query}\n")
    response = agent.invoke({"input": query})
    print(f"\n[에이전트 응답]\n{response}")
    return response

# 7. 테스트 실행
if __name__ == "__main__":
    print("\n========== 기존 테스트 실행 ==========")
    test_query = "회의에서 김대리는 회의록을 작성하기로 했다"
    run_doc_recommendation(test_query)
