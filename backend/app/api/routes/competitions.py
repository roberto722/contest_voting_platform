from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import (
    CompetitionCreate,
    CompetitionRead,
    CompetitionSetupStatus,
    CompetitionUpdate,
)
from app.services import admin_service

router = APIRouter(tags=["competitions"])


@router.post(
    "/api/events/{event_id}/competitions",
    response_model=CompetitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_competition(
    event_id: str,
    payload: CompetitionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionRead:
    return admin_service.create_competition(db, event_id, payload.model_dump())


@router.get("/api/events/{event_id}/competitions", response_model=list[CompetitionRead])
def list_competitions(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[CompetitionRead]:
    return admin_service.list_competitions(db, event_id)


@router.get("/api/competitions/{competition_id}", response_model=CompetitionRead)
def get_competition(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionRead:
    return admin_service.get_competition(db, competition_id)


@router.get(
    "/api/competitions/{competition_id}/setup-status",
    response_model=CompetitionSetupStatus,
)
def get_competition_setup_status(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionSetupStatus:
    return admin_service.get_competition_setup_status(db, competition_id)


@router.patch("/api/competitions/{competition_id}", response_model=CompetitionRead)
def update_competition(
    competition_id: str,
    payload: CompetitionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionRead:
    return admin_service.update_competition(
        db,
        competition_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/api/competitions/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    admin_service.delete_competition(db, competition_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
