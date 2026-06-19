from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.public_vote import (
    PublicCompetitionAccess,
    PublicCompetitionAccessRead,
    PublicVoteSubmit,
    PublicVoteSubmitRead,
    PublicVoteSummaryRead,
)
from app.services import access_service, public_vote_service
from app.services import audit_service
from app.services import screen_service
from app.websocket.screen import screen_manager

router = APIRouter(tags=["public votes"])


@router.post(
    "/api/competitions/{competition_id}/public-access",
    response_model=PublicCompetitionAccessRead,
)
def validate_public_access(
    competition_id: str,
    payload: PublicCompetitionAccess,
    db: Annotated[Session, Depends(get_db)],
) -> PublicCompetitionAccessRead:
    competition = access_service.verify_public_competition_access(
        db,
        competition_id,
        pin=payload.pin,
    )
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        actor_type="public",
        actor_label="Pubblico",
        action="public_access_granted",
        entity_type="competition_access",
        entity_id=competition.id,
        details_json={"access_method": competition.access_method.value},
    )
    return {
        "competition_id": competition.id,
        "event_id": competition.event_id,
        "access_method": competition.access_method.value,
        "access_granted": True,
    }


@router.post(
    "/api/competitions/{competition_id}/public-votes",
    response_model=PublicVoteSubmitRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_public_vote(
    competition_id: str,
    payload: PublicVoteSubmit,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> PublicVoteSubmitRead:
    votes = public_vote_service.submit_public_vote(
        db,
        competition_id,
        payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    screen_state = screen_service.get_screen_state_for_competition(db, competition_id)
    if screen_state is not None:
        await screen_manager.broadcast(
            screen_state.event_id,
            {
                "type": "vote_update",
                "screen_state": screen_service.serialize_screen_state(screen_state),
            },
        )
    return {
        "voting_session_id": votes[0].voting_session_id,
        "voter_session_id": votes[0].voter_session_id,
        "votes": votes,
    }


@router.get(
    "/api/competitions/{competition_id}/public-votes/summary",
    response_model=PublicVoteSummaryRead,
)
def get_public_vote_summary(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> PublicVoteSummaryRead:
    return public_vote_service.get_public_vote_summary(db, competition_id)
