from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import EventCreate, EventRead, EventUpdate
from app.services import admin_service

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Annotated[Session, Depends(get_db)]) -> EventRead:
    return admin_service.create_event(db, payload.model_dump())


@router.get("", response_model=list[EventRead])
def list_events(db: Annotated[Session, Depends(get_db)]) -> list[EventRead]:
    return admin_service.list_events(db)


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Annotated[Session, Depends(get_db)]) -> EventRead:
    return admin_service.get_event(db, event_id)


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    event_id: str,
    payload: EventUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    return admin_service.update_event(db, event_id, payload.model_dump(exclude_unset=True))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    admin_service.delete_event(db, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
