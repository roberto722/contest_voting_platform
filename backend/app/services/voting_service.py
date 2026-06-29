from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, CompetitionStatus, VotingSession, VotingSessionStatus
from app.models.mixins import utc_now
from app.services import audit_service, setup_service
from app.services.admin_service import get_competition


class VotingStateError(Exception):
    def __init__(
        self,
        message: str,
        issues: list[str] | None = None,
        messages: list[str] | None = None,
    ) -> None:
        self.message = message
        self.issues = issues or []
        self.messages = messages or []
        super().__init__(message)


def list_voting_sessions(db: Session, competition_id: str) -> list[VotingSession]:
    get_competition(db, competition_id)
    return list(
        db.scalars(
            select(VotingSession)
            .where(VotingSession.competition_id == competition_id)
            .order_by(VotingSession.opened_at.desc(), VotingSession.created_at.desc())
        )
    )


def get_open_voting_session(db: Session, competition_id: str) -> VotingSession | None:
    return db.scalar(
        select(VotingSession).where(
            VotingSession.competition_id == competition_id,
            VotingSession.status == VotingSessionStatus.OPEN,
        )
    )


def open_voting_session(
    db: Session,
    competition_id: str,
    label: str | None = None,
    opened_by_admin_id: str | None = None,
) -> VotingSession:
    competition = get_competition(db, competition_id)
    _ensure_competition_can_open(db, competition)

    if get_open_voting_session(db, competition_id) is not None:
        raise VotingStateError("competition already has an open voting session")

    voting_session = VotingSession(
        competition=competition,
        label=label,
        status=VotingSessionStatus.OPEN,
        opened_at=utc_now(),
        opened_by_admin_id=opened_by_admin_id,
    )
    competition.status = CompetitionStatus.VOTING_OPEN
    db.add(voting_session)
    db.commit()
    db.refresh(voting_session)
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_voting_session_opened",
        entity_type="voting_session",
        entity_id=voting_session.id,
        details_json={"label": label, "opened_by_admin_id": opened_by_admin_id},
    )
    return voting_session


def close_voting_session(
    db: Session,
    competition_id: str,
    closed_by_admin_id: str | None = None,
) -> VotingSession:
    competition = get_competition(db, competition_id)
    voting_session = get_open_voting_session(db, competition_id)
    if voting_session is None:
        raise VotingStateError("competition has no open voting session")

    voting_session.status = VotingSessionStatus.CLOSED
    voting_session.closed_at = utc_now()
    voting_session.closed_by_admin_id = closed_by_admin_id
    competition.status = CompetitionStatus.VOTING_CLOSED
    db.commit()
    db.refresh(voting_session)
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_voting_session_closed",
        entity_type="voting_session",
        entity_id=voting_session.id,
        details_json={"closed_by_admin_id": closed_by_admin_id},
    )
    return voting_session


def ensure_can_accept_votes(db: Session, competition_id: str) -> VotingSession:
    voting_session = get_open_voting_session(db, competition_id)
    if voting_session is None:
        raise VotingStateError("competition has no open voting session")
    return voting_session


def _ensure_competition_can_open(db: Session, competition: Competition) -> None:
    if competition.status in {
        CompetitionStatus.REVEALED,
    }:
        raise VotingStateError("competition results are final")

    setup_status = setup_service.get_competition_setup_status(db, competition)
    if not setup_status["can_open_voting"]:
        issues_str = ", ".join(setup_status["open_issues"])
        raise VotingStateError(
            f"competition is not ready for voting: {issues_str}",
            issues=setup_status["open_issues"],
            messages=setup_status["messages"],
        )
