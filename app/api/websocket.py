import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets import manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/docks")
async def ws_docks(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Client déconnecté")
    except Exception as e:
        logger.error(f"Erreur WebSocket: {e}")
    finally:
        manager.disconnect(websocket)