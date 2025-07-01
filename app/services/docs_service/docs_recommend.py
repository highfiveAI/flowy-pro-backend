import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
import aiopg
import json
from contextlib import asynccontextmanager
import aioboto3
from botocore.exceptions import ClientError
import re

load_dotenv()

# Gemini Pro 모델 초기화
google_api_key = os.getenv("GOOGLE_API_KEY", settings.GOOGLE_API_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=google_api_key)

# OpenAI 모델 초기화
# openai_api_key = settings.OPENAI_API_KEY
# llm = ChatOpenAI(temperature=0)

# AWS 설정
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

# S3 클라이언트 설정
session = aioboto3.Session(
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

@asynccontextmanager
async def get_db_connection():
    """데이터베이스 연결을 관리하는 컨텍스트 매니저"""
    async with aiopg.create_pool(**DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            yield conn

# 임베딩 모델 초기화
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

async def direct_vector_search(query_text: str, k: int = 3):
    """직접 SQL로 벡터 유사도 검색"""
    try:
        # 쿼리 벡터화
        query_embedding = embedding_model.embed_query(query_text)
        
        # DB 연결 및 검색
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                # 벡터 유사도 검색 쿼리
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
                
                await cursor.execute(sql, (query_embedding, query_embedding, k))
                results = await cursor.fetchall()

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

async def get_document_download_link(s3_key: str) -> str:
    """S3에서 문서의 프리사인드 URL을 생성합니다."""
    try:
        if not s3_key:
            return ""
            
        # 프리사인드 URL 생성 (1시간 유효)
        async with session.client('s3') as s3:
            url = await s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': AWS_BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=3600  # 1시간
            )
        return url
    except ClientError as e:
        print(f"다운로드 링크 생성 실패: {str(e)}")
        return ""
    except Exception as e:
        print(f"예상치 못한 오류 발생: {str(e)}")
        return ""

async def recommend_documents(role_text: str, k: int = 1) -> dict:
    """
    역할이나 업무 내용을 기반으로 관련 문서를 추천하는 함수
    
    Args:
        role_text: 역할이나 업무 내용 (str)
        k: 추천할 문서 개수 (int, default=1)
    
    Returns:
        dict: 추천 문서 정보가 담긴 딕셔너리
    """
    print(f"[recommend_documents] 문서 추천 실행: {role_text}")
    
    try:
        
        # 문서 검색
        docs = await direct_vector_search(role_text, k=k)
        print(f"[recommend_documents] 검색된 문서 수: {len(docs)}")
        
        if not docs:
            return {
                "documents": [],
                "message": "추천할 문서를 찾지 못했습니다."
            }
        
        # 문서 정보 구성
        doc_info_list = []
        for doc in docs:
            snippet = doc['content'][:300].strip().replace("\n", " ")
            doc_info_list.append({
                "filename": doc['interdocs_filename'],
                "content_preview": snippet,
                "similarity": doc['similarity_score']
            })
        
        # LLM을 사용하여 문서 추천 및 설명 생성
        prompt = f'''
다음은 "{role_text}"와 관련된 문서 검색 결과입니다.

검색된 문서들:
{json.dumps(doc_info_list, ensure_ascii=False, indent=2)}

위 문서들을 분석하여 사용자의 역할이나 업무와 가장 관련성이 높은 순서로 정렬하고, 
각 문서가 왜 추천되는지 간단한 설명을 포함하여 아래 JSON 형식으로 응답해주세요.

**중요 지침**
객관적인 판단으로 문서가 role_text와 직접적인 관련성이 낮다고 판단될 경우 "relevance_reason"에 "관련성 낮음"을 출력하세요

출력 형식:
{{
  "documents": [
    {{
      "title": "문서 제목",
      "download_url": "다운로드 URL",
      "similarity_score": "유사도 점수",
      "relevance_reason": "이 문서가 추천되는 이유 (한 문장으로 간단히)"
    }}
  ]
}}
'''

        response = await llm.ainvoke(prompt)
        agent_output = response.content
        print(f"[recommend_documents] LLM 응답: {agent_output}")

        # JSON 파싱
        try:
            agent_output = agent_output.strip()
            if agent_output.startswith("```json"):
                agent_output = agent_output.removeprefix("```json").removesuffix("```").strip()
            
            match = re.search(r'\{.*\}', agent_output, re.DOTALL)
            if match:
                agent_output = match.group()
                result_json = json.loads(agent_output)
            else:
                # 파싱 실패 시 기본 구조 생성
                result_json = {"documents": []}
                
        except Exception as e:
            print(f"[recommend_documents] JSON 파싱 오류: {e}")
            result_json = {"documents": []}
        
        # 다운로드 링크 생성 및 최종 결과 구성
        final_documents = []
        for i, doc in enumerate(docs):
            download_url = await get_document_download_link(doc['interdocs_path'])
            
            # LLM 결과에서 해당하는 문서 찾기
            llm_doc = None
            if result_json.get("documents") and i < len(result_json["documents"]):
                llm_doc = result_json["documents"][i]
            
            final_documents.append({
                "title": doc['interdocs_filename'],
                "download_url": download_url,
                "similarity_score": doc['similarity_score'],
                "relevance_reason": llm_doc.get("relevance_reason", "관련성 높은 문서") if llm_doc else "관련성 높은 문서"
            })
        
        return {
            "documents": final_documents
        }
            
    except Exception as e:
        print(f"[recommend_documents] 문서 추천 중 오류 발생: {e}")
        return {
            "documents": [],
            "error": f"문서 추천 중 오류 발생: {str(e)}"
        }

# 실행 함수
async def run_doc_recommendation(query: str) -> dict:
    """문서 추천 실행 함수"""
    print(f"\n[입력된 역할/업무 내용]\n{query}\n")
    result = await recommend_documents(query)
    print(f"\n[문서 추천 결과]\n{json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

# 테스트 실행
if __name__ == "__main__":
    import asyncio
    print("\n========== 문서 추천 테스트 실행 ==========")
    test_query = "회의에서 김대리는 회의록을 작성하기로 했다"
    asyncio.run(run_doc_recommendation(test_query))