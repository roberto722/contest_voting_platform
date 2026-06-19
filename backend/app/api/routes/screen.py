from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.screen import ScreenStateRead, ScreenStateUpdate
from app.services import screen_service
from app.websocket.screen import screen_manager

router = APIRouter(tags=["screen"])


@router.get("/api/events/{event_id}/screen-state", response_model=ScreenStateRead)
def get_screen_state(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ScreenStateRead:
    return screen_service.get_screen_state(db, event_id)


@router.put("/api/events/{event_id}/screen-state", response_model=ScreenStateRead)
async def update_screen_state(
    event_id: str,
    payload: ScreenStateUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ScreenStateRead:
    screen_state = screen_service.update_screen_state(
        db,
        event_id=event_id,
        competition_id=payload.competition_id,
        mode=payload.mode,
        payload_json=payload.payload_json,
    )
    await screen_manager.broadcast(
        event_id,
        {
            "type": "screen_state",
            "screen_state": screen_service.serialize_screen_state(screen_state),
        },
    )
    return screen_state


@router.websocket("/ws/events/{event_id}/screen")
async def screen_websocket(
    event_id: str,
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    await screen_manager.connect(event_id, websocket)
    try:
        screen_state = screen_service.get_screen_state(db, event_id)
        await websocket.send_json(
            {
                "type": "screen_state",
                "screen_state": screen_service.serialize_screen_state(screen_state),
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        screen_manager.disconnect(event_id, websocket)
