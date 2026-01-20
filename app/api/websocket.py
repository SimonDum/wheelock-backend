import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets import manager

router = APIRouter()

@router.websocket("/ws/docks")
async def ws_docks(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(60)  # Garde la connexion ouverte sans attendre de message
    except (WebSocketDisconnect, RuntimeError):
        manager.disconnect(websocket)
