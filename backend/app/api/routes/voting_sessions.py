from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import VotingSessionClose, VotingSessionCreate, VotingSessionRead
from app.services import voting_service
from app.services import screen_service
from app.websocket.screen import screen_manager

router = APIRouter(tags=["voting sessions"])


@router.post(
    "/api/competitions/{competition_id}/voting-sessions",
    response_model=VotingSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def open_voting_session(
    competition_id: str,
    payload: VotingSessionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> VotingSessionRead:
    voting_session = voting_service.open_voting_session(
        db,
        competition_id,
        label=payload.label,
        opened_by_admin_id=payload.opened_by_admin_id,
    )
    screen_state = screen_service.get_screen_state_for_competition(db, competition_id)
    if screen_state is not None:
        await screen_manager.broadcast(
            screen_state.event_id,
            {
                "type": "voting_session",
                "screen_state": screen_service.serialize_screen_state(screen_state),
            },
        )
    return voting_session


@router.get(
    "/api/competitions/{competition_id}/voting-sessions",
    response_model=list[VotingSessionRead],
)
def list_voting_sessions(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[VotingSessionRead]:
    return voting_service.list_voting_sessions(db, competition_id)


@router.post(
    "/api/competitions/{competition_id}/voting-sessions/close",
    response_model=VotingSessionRead,
)
async def close_voting_session(
    competition_id: str,
    payload: VotingSessionClose,
    db: Annotated[Session, Depends(get_db)],
) -> VotingSessionRead:
    voting_session = voting_service.close_voting_session(
        db,
        competition_id,
        closed_by_admin_id=payload.closed_by_admin_id,
    )
    screen_state = screen_service.get_screen_state_for_competition(db, competition_id)
    if screen_state is not None:
        await screen_manager.broadcast(
            screen_state.event_id,
            {
                "type": "voting_session",
                "screen_state": screen_service.serialize_screen_state(screen_state),
            },
        )
    return voting_session
