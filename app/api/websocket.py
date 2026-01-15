from fastapi import APIRouter, WebSocket
from jose import JWTError

from app.core.jwt import decode_token
from app.websockets import manager

router = APIRouter()

@router.websocket("/ws/spots")
async def ws_spots(websocket: WebSocket):
    await manager.connect(websocket)
