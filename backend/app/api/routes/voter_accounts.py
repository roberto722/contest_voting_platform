from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.voter_account import (
    VoterAccountCreate,
    VoterAccountCodeRegeneratedRead,
    VoterAccountCreatedRead,
    VoterAccountLinkParticipantRequest,
    VoterAccountRead,
    VoterAccountUpdate,
    LinkedParticipantRead,
)
from app.services import voter_account_service

router = APIRouter(tags=["voter accounts"])


@router.post(
    "/api/events/{event_id}/voter-accounts",
    response_model=VoterAccountCreatedRead,
    status_code=status.HTTP_201_CREATED,
)
def create_voter_account(
    event_id: str,
    payload: VoterAccountCreate,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccountCreatedRead:
    va, code = voter_account_service.create_voter_account(
        db, event_id, payload.model_dump()
    )
    return VoterAccountCreatedRead(
        voter_account=VoterAccountRead.model_validate(va),
        access_code=code,
    )


@router.get(
    "/api/events/{event_id}/voter-accounts",
    response_model=list[VoterAccountRead],
)
def list_voter_accounts(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[VoterAccountRead]:
    return voter_account_service.list_voter_accounts(db, event_id)


@router.get(
    "/api/voter-accounts/{voter_account_id}",
    response_model=VoterAccountRead,
)
def get_voter_account(
    voter_account_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccountRead:
    return voter_account_service.get_voter_account(db, voter_account_id)


@router.patch(
    "/api/voter-accounts/{voter_account_id}",
    response_model=VoterAccountRead,
)
def update_voter_account(
    voter_account_id: str,
    payload: VoterAccountUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccountRead:
    return voter_account_service.update_voter_account(
        db, voter_account_id, payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/api/voter-accounts/{voter_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_voter_account(
    voter_account_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    voter_account_service.delete_voter_account(db, voter_account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/voter-accounts/{voter_account_id}/regenerate-code",
    response_model=VoterAccountCodeRegeneratedRead,
)
def regenerate_voter_code(
    voter_account_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> VoterAccountCodeRegeneratedRead:
    va, code = voter_account_service.regenerate_voter_code(db, voter_account_id)
    return VoterAccountCodeRegeneratedRead(
        voter_account=VoterAccountRead.model_validate(va),
        access_code=code,
    )


@router.post(
    "/api/voter-accounts/{voter_account_id}/link-participant",
    response_model=LinkedParticipantRead,
)
def link_participant(
    voter_account_id: str,
    payload: VoterAccountLinkParticipantRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LinkedParticipantRead:
    participant = voter_account_service.link_participant(
        db, voter_account_id, payload.participant_id
    )
    return LinkedParticipantRead.model_validate(participant)


@router.delete(
    "/api/voter-accounts/{voter_account_id}/unlink-participant/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_participant(
    voter_account_id: str,
    participant_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    voter_account_service.unlink_participant(db, voter_account_id, participant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
