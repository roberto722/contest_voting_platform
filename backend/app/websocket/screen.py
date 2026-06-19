from fastapi import WebSocket


class ScreenConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, event_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(event_id, set()).add(websocket)

    def disconnect(self, event_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(event_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(event_id, None)

    async def broadcast(self, event_id: str, payload: dict) -> None:
        connections = list(self._connections.get(event_id, set()))
        stale_connections: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.disconnect(event_id, websocket)


screen_manager = ScreenConnectionManager()
