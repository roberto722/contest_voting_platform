from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.public_vote import (
    PublicVoteSubmit,
    PublicVoteSubmitRead,
    PublicVoteSummaryRead,
    SelfExclusionRead,
    VoterVotingStatusRead,
)
from app.services import access_service, public_vote_service, voting_service
from app.services import audit_service
from app.services import screen_service
from app.websocket.screen import screen_manager

router = APIRouter(tags=["public votes"])


class VoterAccessByCode(BaseModel):
    event_id: str
    access_code: str


class VoterAccessRead(BaseModel):
    voter_account_id: str
    display_name: str
    access_token: str


@router.post("/api/vote/access", response_model=VoterAccessRead)
def voter_access_by_code(
    payload: VoterAccessByCode,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccessRead:
    va = access_service.get_voter_account_by_code(db, payload.event_id, payload.access_code)
    return VoterAccessRead(
        voter_account_id=va.id,
        display_name=va.display_name,
        access_token=va.access_token,
    )


@router.get("/api/vote/access", response_model=VoterAccessRead)
def voter_access_by_token(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccessRead:
    va = access_service.get_voter_account_by_token(db, token)
    return VoterAccessRead(
        voter_account_id=va.id,
        display_name=va.display_name,
        access_token=va.access_token,
    )


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
    x_voter_account_id: Annotated[str, Header()],
    x_voter_access_token: Annotated[str, Header()],
) -> PublicVoteSubmitRead:
    votes = public_vote_service.submit_public_vote(
        db,
        competition_id,
        payload,
        voter_account_id=x_voter_account_id,
        access_token=x_voter_access_token,
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
        "voter_account_id": votes[0].voter_account_id,
        "votes": votes,
    }


@router.get(
    "/api/competitions/{competition_id}/public-votes/self-exclusion",
    response_model=SelfExclusionRead,
)
def get_self_exclusion(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
    x_voter_account_id: Annotated[str, Header()],
    x_voter_access_token: Annotated[str, Header()],
) -> SelfExclusionRead:
    excluded_id = public_vote_service.get_self_exclusion(
        db,
        competition_id,
        voter_account_id=x_voter_account_id,
        access_token=x_voter_access_token,
    )
    return SelfExclusionRead(excluded_participant_id=excluded_id)


@router.get(
    "/api/competitions/{competition_id}/public-votes/status",
    response_model=VoterVotingStatusRead,
)
def get_public_voting_status(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
    x_voter_account_id: Annotated[str, Header()],
    x_voter_access_token: Annotated[str, Header()],
) -> VoterVotingStatusRead:
    has_voted = public_vote_service.has_voted_in_active_session(
        db,
        competition_id,
        voter_account_id=x_voter_account_id,
        access_token=x_voter_access_token,
    )
    competition = public_vote_service.get_competition(db, competition_id)
    active_session = voting_service.get_open_voting_session(db, competition_id)
    return VoterVotingStatusRead(
        voting_open=active_session is not None and active_session.public_voting_open,
        has_voted=has_voted,
        allow_vote_update=competition.allow_vote_update,
    )


@router.get(
    "/api/competitions/{competition_id}/public-votes/summary",
    response_model=PublicVoteSummaryRead,
)
def get_public_vote_summary(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> PublicVoteSummaryRead:
    return public_vote_service.get_public_vote_summary(db, competition_id)
