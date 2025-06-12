# app/routers/docs.py (가정 경로)

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends # Form, Depends 임포트 추가
from pydantic import BaseModel
from typing import List, Optional, Annotated # Annotated 임포트 추가
from uuid import UUID
from datetime import datetime

from app.services.docs_service.docs_recommend import run_doc_recommendation, recommend_docs_from_role
from app.services.docs_service.docs_crud import (
    create_document,
    update_document,
    get_documents,
    get_document,
    delete_document
)
from sqlalchemy.orm import Session # Session 임포트 추가
from app.services.docs_service.docs_crud import get_db # get_db 함수 임포트 (서비스 파일에 정의되어 있음)

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

class DocumentResponse(BaseModel):
    interdocs_id: UUID
    interdocs_type_name: str
    interdocs_filename: str
    interdocs_contents: str
    interdocs_path: str
    interdocs_uploaded_date: datetime
    interdocs_updated_date: Optional[datetime]
    interdocs_update_user_id: UUID

    class Config:
        from_attributes = True

@router.post("/recommend", response_model=DocumentRecommendResponse)
async def recommend_documents(request: DocumentRecommendRequest):
    """
    역할 또는 업무 내용을 기반으로 관련 문서를 추천합니다.
    
    - **query**: 검색할 역할 또는 업무 내용
    """
    try:
        result = await recommend_docs_from_role(request.query)

        if isinstance(result, str):
            return DocumentRecommendResponse(success=False, message=result)
        
        doc_objs = [Document(**doc) for doc in result]

        if not doc_objs:
            return DocumentRecommendResponse(success=True, message="추천할 문서를 찾지 못했습니다.", documents=[])

        return DocumentRecommendResponse(success=True, documents=doc_objs)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 추천 중 오류 발생: {str(e)}"
        )

@router.post("/", response_model=DocumentResponse)
async def create_new_document(
    # FormData에서 값을 받으려면 Form()을 사용해야 합니다.
    # Annotated와 Form을 함께 사용하여 타입 힌트를 명확히 합니다.
    update_user_id: Annotated[UUID, Form(description="업로드 사용자 ID")],
    doc_type: Annotated[str, Form(description="문서 유형")],
    file: UploadFile = File(description="업로드할 파일"), # File(...)은 File()로 변경
    db: Session = Depends(get_db) # DB 세션 주입
):
    """
    새로운 문서를 업로드합니다.
    
    - **doc_type**: 문서 유형
    - **file**: 업로드할 파일
    - **update_user_id**: 업로드 사용자 ID
    """
    return await create_document(db, file, doc_type, update_user_id) # db 객체 전달

@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_existing_document(
    doc_id: UUID, # 경로 파라미터는 Form으로 받을 필요 없음
    update_user_id: Annotated[UUID, Form(description="수정 사용자 ID")],
    file: UploadFile = File(description="새로운 파일"), # File(...)은 File()로 변경
    db: Session = Depends(get_db) # DB 세션 주입
):
    """
    기존 문서를 수정합니다.
    
    - **doc_id**: 수정할 문서 ID
    - **file**: 새로운 파일
    - **update_user_id**: 수정 사용자 ID
    """
    return await update_document(db, doc_id, file, update_user_id) # db 객체 전달

@router.get("/", response_model=List[DocumentResponse])
async def get_all_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db) # DB 세션 주입
):
    """
    문서 목록을 조회합니다.
    
    - **skip**: 건너뛸 문서 수
    - **limit**: 조회할 문서 수
    """
    return await get_documents(db, skip, limit) # db 객체 전달

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_single_document(
    doc_id: UUID,
    db: Session = Depends(get_db) # DB 세션 주입
):
    """
    단일 문서를 조회합니다.
    
    - **doc_id**: 조회할 문서 ID
    """
    doc = await get_document(doc_id, db) # db 객체 전달
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc

@router.delete("/{doc_id}")
async def delete_existing_document(
    doc_id: UUID,
    db: Session = Depends(get_db) # DB 세션 주입
):
    """
    문서를 삭제합니다.
    
    - **doc_id**: 삭제할 문서 ID
    """
    result = await delete_document(db, doc_id) # db 객체 전달
    if result:
        return {"message": "문서가 성공적으로 삭제되었습니다"}
    raise HTTPException(status_code=500, detail="문서 삭제 중 오류가 발생했습니다")