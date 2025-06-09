# app/services/docs_service/docs_crud.py

import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import tempfile
import subprocess

import boto3
import PyPDF2
import docx
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.interdoc import Interdoc

# 환경 변수 로드
load_dotenv()

# DB 연결 설정
DATABASE_URL = os.getenv('CONNECTION_STRING')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# S3 클라이언트 설정
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# OpenAI 클라이언트 설정
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 문서 임베딩 모델 초기화
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

def extract_text_from_hwp(file_path: str) -> str:
    """HWP 파일에서 텍스트를 추출하는 함수"""
    try:
        result = subprocess.run(
            ['hwp5txt', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            raise ValueError(f"HWP 파일 변환 실패: {result.stderr}")
            
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        raise ValueError(f"HWP 파일 처리 실패: {str(e)}")
    except Exception as e:
        raise ValueError(f"HWP 파일 읽기 실패: {str(e)}")

def read_file_content(file: UploadFile) -> str:
    """파일 형식에 따라 내용을 읽는 함수"""
    content = ""
    file_ext = file.filename.lower().split('.')[-1]
    
    file.file.seek(0) # 중요: 파일 포인터 초기화
    
    try:
        if file_ext == 'txt':
            content = file.file.read().decode('utf-8')
        
        elif file_ext == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file.file)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        
        elif file_ext in ['doc', 'docx']:
            doc = docx.Document(file.file)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
        elif file_ext == 'hwp':
            file.file.seek(0) 
            with tempfile.NamedTemporaryFile(delete=False, suffix='.hwp') as temp_file:
                temp_file.write(file.file.read())
                temp_path = temp_file.name
            
            try:
                content = extract_text_from_hwp(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        else:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 파일 형식입니다. (지원 형식: txt, pdf, doc, docx, hwp)"
            )
            
        if not content.strip():
            raise HTTPException(
                status_code=400,
                detail="파일에서 텍스트를 추출할 수 없습니다."
            )
            
        return content
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 읽기 실패: {str(e)}"
        )

def extract_text_from_file(file: UploadFile) -> str:
    """LLM을 이용해 파일 내용을 요약하는 함수"""
    try:
        file.file.seek(0) 
        content = read_file_content(file)
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "주어진 문서의 전체적인 구조를 파악하여, 1~2문장 요약을 작성해주세요. 예를 들어, ‘목차, 목표, 일정, 예산 등으로 구성된 프로젝트 기획안’과 같이, 문서의 구성 요소를 중심으로 문서 종류와 연결되는 자연스러운 문장으로 만들어 주세요. 문서의 구체적 내용보다는 형식적·조직적 구성을 중심으로 정리해 주세요."},
                {"role": "user", "content": content}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 요약 실패: {str(e)}"
        )

def create_document(
    db: Session, # db를 맨 앞으로 옮김
    file: UploadFile,
    doc_type: str,
    update_user_id: UUID
) -> Interdoc:
    """문서 생성 함수"""
    try:
        content = extract_text_from_file(file)
        embedding = model.encode(content)
        
        s3_path = f"documents/{file.filename}"
        
        file.file.seek(0) 
        s3_client.upload_fileobj(
            file.file,
            os.getenv('AWS_BUCKET_NAME'),
            s3_path
        )
        
        doc = Interdoc(
            interdocs_type_name=doc_type,
            interdocs_filename=file.filename,
            interdocs_contents=content[:255],
            interdocs_vector=embedding,
            interdocs_path=s3_path,
            interdocs_uploaded_date=datetime.now(),
            interdocs_update_user_id=update_user_id
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        return doc
        
    except Exception as e:
        if 's3_path' in locals():
            try:
                s3_client.delete_object(
                    Bucket=os.getenv('AWS_BUCKET_NAME'),
                    Key=s3_path
                )
            except:
                pass
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def update_document(
    db: Session, # db를 맨 앞으로 옮김
    doc_id: UUID,
    file: UploadFile,
    update_user_id: UUID
) -> Interdoc:
    """문서 수정 함수"""
    try:
        doc = db.query(Interdoc).filter(Interdoc.interdocs_id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
            
        content = extract_text_from_file(file)
        embedding = model.encode(content)
        
        old_s3_path = doc.interdocs_path
        new_s3_path = f"documents/{file.filename}"
        
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file,
            os.getenv('AWS_BUCKET_NAME'),
            new_s3_path
        )
        
        s3_client.delete_object(
            Bucket=os.getenv('AWS_BUCKET_NAME'),
            Key=old_s3_path
        )
        
        doc.interdocs_filename = file.filename
        doc.interdocs_contents = content[:255]
        doc.interdocs_vector = embedding
        doc.interdocs_path = new_s3_path
        doc.interdocs_updated_date = datetime.now()
        doc.interdocs_update_user_id = update_user_id
        
        db.commit()
        db.refresh(doc)
        
        return doc
        
    except Exception as e:
        if 'new_s3_path' in locals():
            try:
                s3_client.delete_object(
                    Bucket=os.getenv('AWS_BUCKET_NAME'),
                    Key=new_s3_path
                )
            except:
                pass
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_documents(
    db: Session,
    skip: int = 0,
    limit: int = 10
) -> List[Interdoc]:
    """문서 목록 조회 함수"""
    print("get_documents 함수 시작") # 추가
    try:
        print(f"DB 세션 객체: {db}") # 추가
        print(f"Interdoc 모델: {Interdoc}") # 추가
        # 실제로 쿼리가 실행되는지 확인
        documents = db.query(Interdoc).offset(skip).limit(limit).all()
        print(f"조회된 문서 수: {len(documents)}") # 추가
        return documents
    except Exception as e:
        print(f"!!! get_documents 에러 발생: {e}") # 추가
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 실패: {str(e)}")

def get_document(
    db: Session, # db를 맨 앞으로 옮김
    doc_id: UUID
) -> Optional[Interdoc]:
    """단일 문서 조회 함수"""
    try:
        return db.query(Interdoc).filter(Interdoc.interdocs_id == doc_id).first()
    except Exception as e: # --- 추가: except 블록 ---
        raise HTTPException(status_code=500, detail=f"단일 문서 조회 실패: {str(e)}")

def delete_document(
    db: Session, # db를 맨 앞으로 옮김
    doc_id: UUID
) -> bool:
    """문서 삭제 함수"""
    try:
        doc = db.query(Interdoc).filter(Interdoc.interdocs_id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
            
        s3_client.delete_object(
            Bucket=os.getenv('AWS_BUCKET_NAME'),
            Key=doc.interdocs_path
        )
        
        db.delete(doc)
        db.commit()
        
        return True
        
    except ClientError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"S3 삭제 실패: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))