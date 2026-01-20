from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Envoie le message à tous les clients connectés
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except (RuntimeError, ConnectionError):
                # Marquer comme déconnecté si l'envoi échoue
                disconnected.append(connection)
        
        # Nettoyer les connexions fermées
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()