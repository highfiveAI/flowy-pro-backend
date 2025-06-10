# auth.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.core.config import settings
from app.schemas.signup_info import TokenPayload
# JWT 설정
SECRET_KEY = settings.SECRET_KEY  # 환경변수로 관리 권장
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# JWT 생성 함수
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 검증 함수
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise ValueError("Invalid token")
        return username
    except JWTError:
        raise ValueError("Could not validate token")

def verify_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except (JWTError, ValueError):
        raise ValueError("Could not validate token")