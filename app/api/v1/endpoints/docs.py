from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.docs_service.docs_recommend import run_doc_recommendation, recommend_docs_from_role

router = APIRouter()

# 요청/응답 모델
class DocumentRecommendRequest(BaseModel):
    query: str

class Document(BaseModel):
    id: str
    title: str
    similarity: float
    preview: str
    download_url: Optional[str]

class DocumentRecommendResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    documents: List[Document] = []

@router.post("/recommend", response_model=DocumentRecommendResponse)
async def recommend_documents(request: DocumentRecommendRequest):
    """
    역할 또는 업무 내용을 기반으로 관련 문서를 추천합니다.
    
    - **query**: 검색할 역할 또는 업무 내용
    """
    try:
        # recommend_docs_from_role 함수가 List[Dict] 또는 str을 반환할 수 있으므로 타입을 확인
        # (이전 service 코드에서는 파일명 차단 시 문자열을 반환했으므로 이를 처리)
        result = recommend_docs_from_role(request.query)

        if isinstance(result, str): # 파일명 차단 메시지인 경우
            return DocumentRecommendResponse(success=False, message=result)
        
        # 문서 리스트인 경우 Document 모델로 변환
        doc_objs = [Document(**doc) for doc in result]

        if not doc_objs: # 추천 문서가 없는 경우
            return DocumentRecommendResponse(success=True, message="추천할 문서를 찾지 못했습니다.", documents=[])

        return DocumentRecommendResponse(success=True, documents=doc_objs)
        
    except Exception as e:
        # service 코드에서 발생한 예외를 여기서 처리합니다.
        raise HTTPException(
            status_code=500,
            detail=f"문서 추천 중 오류 발생: {str(e)}"
        )
