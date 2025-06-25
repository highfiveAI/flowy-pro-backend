from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import settings
from app.schemas.signup_info import TokenPayload
from app.schemas.find_id import VerifiedPwTokenPayload
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import json

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 토큰 생성 함수
async def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise ValueError("Invalid token: no subject (sub) found")
        return username

    except ExpiredSignatureError:
        raise ValueError("Token has expired")

    except JWTError:
        raise ValueError("Could not validate token")

# 엑세스 토큰 해독 함수
async def verify_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    
    except ExpiredSignatureError:
        raise ValueError("Token has expired")

    except JWTError:
        raise ValueError("Could not validate token")

# 엑세스 토큰 검증 함수
async def check_access_token(request: Request):
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="쿠키에 access_token이 없습니다.")

    try:
        user: TokenPayload = await verify_access_token(token)

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT 파싱 오류: {str(e)}")

    except ValueError as ve:
        raise HTTPException(status_code=401, detail=f"토큰 검증 오류: {str(ve)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    
    return user

# 비밀번호변경 토큰 해독 함수
async def verify_password_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return VerifiedPwTokenPayload(**payload)
    
    except ExpiredSignatureError:
        raise ValueError("Token has expired")

    except JWTError:
        raise ValueError("Could not validate token")

# 비밀번호변경 토큰 검증 함수
async def check_password_token(request: Request):
    
    token = request.cookies.get("verified_pw_token")
    if not token:
        raise HTTPException(status_code=401, detail="쿠키에 verified_pw_token이 없습니다.")

    try:
        payload: VerifiedPwTokenPayload = await verify_password_token(token)

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT 파싱 오류: {str(e)}")

    except ValueError as ve:
        raise HTTPException(status_code=401, detail=f"토큰 검증 오류: {str(ve)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    
    return payload