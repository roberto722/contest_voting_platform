from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Event, Participant, VoterAccount
from app.models.enums import EventStatus
from app.services.access_service import generate_voter_code, hash_secret
from app.services.admin_service import AdminStateError, ResourceNotFound, get_required


def create_voter_account(
    db: Session,
    event_id: str,
    data: dict[str, Any],
) -> tuple[VoterAccount, str]:
    event = get_required(db, Event, event_id, "event")
    _ensure_event_draft(event)
    code = generate_voter_code()
    va = VoterAccount(
        event_id=event_id,
        display_name=data["display_name"],
        notes=data.get("notes"),
        access_code_hash=hash_secret(code),
        access_token=str(uuid4()),
        active=data.get("active", True),
    )
    db.add(va)
    db.commit()
    db.refresh(va)
    return va, code


def list_voter_accounts(db: Session, event_id: str) -> list[VoterAccount]:
    get_required(db, Event, event_id, "event")
    return list(
        db.scalars(
            select(VoterAccount)
            .where(VoterAccount.event_id == event_id)
            .order_by(VoterAccount.display_name)
        )
    )


def get_voter_account(db: Session, voter_account_id: str) -> VoterAccount:
    return get_required(db, VoterAccount, voter_account_id, "voter_account")


def update_voter_account(
    db: Session,
    voter_account_id: str,
    data: dict[str, Any],
) -> VoterAccount:
    va = get_voter_account(db, voter_account_id)
    event = get_required(db, Event, va.event_id, "event")
    _ensure_event_draft(event)
    for key, value in data.items():
        setattr(va, key, value)
    db.add(va)
    db.commit()
    db.refresh(va)
    return va


def delete_voter_account(db: Session, voter_account_id: str) -> None:
    va = get_voter_account(db, voter_account_id)
    event = get_required(db, Event, va.event_id, "event")
    _ensure_event_draft(event)
    db.delete(va)
    db.commit()


def regenerate_voter_code(db: Session, voter_account_id: str) -> tuple[VoterAccount, str]:
    va = get_voter_account(db, voter_account_id)
    code = generate_voter_code()
    va.access_code_hash = hash_secret(code)
    db.add(va)
    db.commit()
    db.refresh(va)
    return va, code


def link_participant(
    db: Session,
    voter_account_id: str,
    participant_id: str,
) -> Participant:
    va = get_voter_account(db, voter_account_id)
    event = get_required(db, Event, va.event_id, "event")
    _ensure_event_draft(event)
    participant = get_required(db, Participant, participant_id, "participant")
    # Verify participant belongs to same event (via competition → event)
    if participant.competition.event_id != va.event_id:
        raise AdminStateError(
            "participant does not belong to the voter account's event",
            status_code=409,
        )
    existing_participant = db.scalars(
        select(Participant).where(
            or_(
                Participant.voter_account_id == va.id,
                Participant.voter_accounts.any(VoterAccount.id == va.id),
            ),
            Participant.competition_id == participant.competition_id,
            Participant.id != participant.id,
        )
    ).first()
    if existing_participant is not None:
        raise AdminStateError(
            "voter account is already linked to a participant in this competition",
            status_code=409,
        )
    if va not in participant.voter_accounts:
        participant.voter_accounts.append(va)
    if participant.voter_account_id is None:
        participant.voter_account_id = va.id
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def unlink_participant(
    db: Session,
    voter_account_id: str,
    participant_id: str,
) -> None:
    va = get_voter_account(db, voter_account_id)
    event = get_required(db, Event, va.event_id, "event")
    _ensure_event_draft(event)
    participant = get_required(db, Participant, participant_id, "participant")
    if va not in participant.voter_accounts and participant.voter_account_id != va.id:
        raise AdminStateError(
            "participant is not linked to this voter account",
            status_code=409,
        )
    if va in participant.voter_accounts:
        participant.voter_accounts.remove(va)
    if participant.voter_account_id == va.id:
        participant.voter_account_id = (
            participant.voter_accounts[0].id if participant.voter_accounts else None
        )
    db.add(participant)
    db.commit()


def _ensure_event_draft(event: Event) -> None:
    if event.status != EventStatus.DRAFT:
        raise AdminStateError(
            "voter account configuration is locked when event is not draft",
            status_code=409,
        )
