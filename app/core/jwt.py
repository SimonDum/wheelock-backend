from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

def create_admin_token(admin_id: int):
    payload = {
        "sub": str(admin_id),
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES_ADMIN)
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

def decode_token(token: str):
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
