from fastapi import APIRouter, HTTPException, Depends
from app.schemas import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.jwt import create_admin_token
from app.core.config import settings
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.core.security import get_password_hash

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(models.Admin).where(models.Admin.username == data.username)
    )
    admin = result.scalar_one_or_none()


    if not admin:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu ou inactif")
    if not admin.is_active:
        raise HTTPException(status_code=401, detail="Compte administrateur inactif")
    if not verify_password(data.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")

    token = create_admin_token(admin.id)
    return {"access_token": token}