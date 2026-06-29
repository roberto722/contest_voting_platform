from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EventStatus, ScreenMode, ScreenState
from app.services import audit_service
from app.services.admin_service import get_competition, get_event


class ScreenStateError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_screen_state(db: Session, event_id: str) -> ScreenState:
    get_event(db, event_id)
    screen_state = db.scalar(select(ScreenState).where(ScreenState.event_id == event_id))
    if screen_state is not None:
        return screen_state

    screen_state = ScreenState(
        event_id=event_id,
        competition_id=None,
        mode=ScreenMode.IDLE,
        payload_json={},
    )
    db.add(screen_state)
    db.commit()
    db.refresh(screen_state)
    return screen_state


def update_screen_state(
    db: Session,
    event_id: str,
    competition_id: str | None,
    mode: ScreenMode,
    payload_json: dict | None = None,
) -> ScreenState:
    event = get_event(db, event_id)
    if event.status != EventStatus.LIVE:
        raise ScreenStateError("event must be live to update screen state", status_code=409)
    if competition_id is not None:
        competition = get_competition(db, competition_id)
        if competition.event_id != event_id:
            raise ScreenStateError("competition does not belong to event")

    screen_state = get_screen_state(db, event_id)
    screen_state.competition_id = competition_id
    screen_state.mode = mode
    screen_state.payload_json = payload_json or {}
    db.add(screen_state)
    db.commit()
    db.refresh(screen_state)
    audit_service.record_audit_log(
        db,
        event_id=event_id,
        competition_id=competition_id,
        action="admin_screen_state_updated",
        entity_type="screen_state",
        entity_id=screen_state.id,
        details_json={
            "mode": mode.value,
            "payload_keys": sorted((payload_json or {}).keys()),
        },
    )
    return screen_state


def serialize_screen_state(screen_state: ScreenState) -> dict:
    return {
        "id": screen_state.id,
        "event_id": screen_state.event_id,
        "competition_id": screen_state.competition_id,
        "mode": screen_state.mode.value,
        "payload_json": screen_state.payload_json,
    }


def get_screen_state_for_competition(db: Session, competition_id: str) -> ScreenState | None:
    competition = get_competition(db, competition_id)
    return db.scalar(
        select(ScreenState).where(
            ScreenState.event_id == competition.event_id,
            ScreenState.competition_id == competition.id,
        )
    )
