from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import ParticipantCreate, ParticipantRead, ParticipantUpdate
from app.services import admin_service

router = APIRouter(tags=["participants"])


@router.post(
    "/api/competitions/{competition_id}/participants",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_participant(
    competition_id: str,
    payload: ParticipantCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ParticipantRead:
    return admin_service.create_participant(db, competition_id, payload.model_dump())


@router.get("/api/competitions/{competition_id}/participants", response_model=list[ParticipantRead])
def list_participants(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[ParticipantRead]:
    return admin_service.list_participants(db, competition_id)


@router.patch("/api/participants/{participant_id}", response_model=ParticipantRead)
def update_participant(
    participant_id: str,
    payload: ParticipantUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ParticipantRead:
    return admin_service.update_participant(
        db,
        participant_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/api/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(participant_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    admin_service.delete_participant(db, participant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
