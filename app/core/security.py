from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.jwt import decode_token
from app.core.config import settings
from app.database import get_db
from app import models

pwd_context = CryptContext(schemes=["bcrypt"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

async def require_admin(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = decode_token(creds.credentials)

        if payload.get("role") != "admin":
            raise HTTPException(status_code=403)
        
        admin_id = int(payload["sub"])
        admin = await db.get(models.Admin, admin_id)

        if not admin or not admin.is_active:
            raise HTTPException(status_code=401)

        return admin
    except JWTError:
        raise HTTPException(status_code=401)

def require_sensor_key(x_api_key: str = Header(...)):
    if x_api_key != settings.SENSOR_API_KEY:
        logger.warning(f"Tentative d'accès sensor avec clé invalide")
        raise HTTPException(status_code=403)
