from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nouvelle connexion. Total: {len(self.active_connections)}")
        print(f"Nouvelle connexion. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Connexion fermée. Total: {len(self.active_connections)}")
            print(f"Connexion fermée. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Envoie le message à tous les clients connectés
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                print(f"Message envoyé à {connection}: {message}")
            except Exception as e:
                # Marquer comme déconnecté si l'envoi échoue
                logger.warning(f"Erreur d'envoi: {e}")
                disconnected.append(connection)
        
        # Nettoyer les connexions fermées
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()