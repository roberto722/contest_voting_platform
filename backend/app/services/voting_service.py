from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, CompetitionStatus, VotingSession, VotingSessionStatus
from app.models.mixins import utc_now
from app.services import setup_service
from app.services.admin_service import get_competition

VoteChannel = Literal["public", "judge"]


class VotingStateError(Exception):
    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        self.message = message
        self.messages = message
        self.issues = issues or []
        super().__init__(message)


def list_voting_sessions(db: Session, competition_id: str) -> list[VotingSession]:
    return list(
        db.scalars(
            select(VotingSession)
            .where(VotingSession.competition_id == competition_id)
            .order_by(VotingSession.opened_at.desc())
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
    channels: list[str] | None = None,
) -> VotingSession:
    competition = get_competition(db, competition_id)
    _ensure_competition_can_open(db, competition)
    selected_channels = _resolve_channels(competition, channels)

    existing = get_open_voting_session(db, competition_id)
    if existing is not None:
        _open_channels(existing, selected_channels)
        db.commit()
        db.refresh(existing)
        return existing

    voting_session = VotingSession(
        competition=competition,
        label=label,
        status=VotingSessionStatus.OPEN,
        public_voting_open="public" in selected_channels,
        judge_voting_open="judge" in selected_channels,
        opened_at=utc_now(),
        opened_by_admin_id=opened_by_admin_id,
    )
    competition.status = CompetitionStatus.VOTING_OPEN
    db.add(voting_session)
    db.commit()
    db.refresh(voting_session)
    return voting_session


def close_voting_session(
    db: Session,
    competition_id: str,
    closed_by_admin_id: str | None = None,
    channels: list[str] | None = None,
) -> VotingSession:
    competition = get_competition(db, competition_id)
    voting_session = get_open_voting_session(db, competition_id)
    if voting_session is None:
        raise VotingStateError("competition has no open voting session")

    selected_channels = _resolve_channels(competition, channels)
    if "public" in selected_channels:
        voting_session.public_voting_open = False
    if "judge" in selected_channels:
        voting_session.judge_voting_open = False

    if not voting_session.public_voting_open and not voting_session.judge_voting_open:
        voting_session.status = VotingSessionStatus.CLOSED
        voting_session.closed_at = utc_now()
        voting_session.closed_by_admin_id = closed_by_admin_id
        competition.status = CompetitionStatus.VOTING_CLOSED

    db.commit()
    db.refresh(voting_session)
    return voting_session


def ensure_can_accept_votes(
    db: Session,
    competition_id: str,
    channel: VoteChannel | None = None,
) -> VotingSession:
    voting_session = get_open_voting_session(db, competition_id)
    if voting_session is None:
        raise VotingStateError("competition has no open voting session")
    if channel == "public" and not voting_session.public_voting_open:
        raise VotingStateError("public voting is closed")
    if channel == "judge" and not voting_session.judge_voting_open:
        raise VotingStateError("judge voting is closed")
    return voting_session


def _ensure_competition_can_open(db: Session, competition: Competition) -> None:
    if competition.status in {
        CompetitionStatus.RESULTS_FROZEN,
        CompetitionStatus.REVEALED,
    }:
        raise VotingStateError("competition results are final")

    setup_status = setup_service.get_competition_setup_status(db, competition)
    if not setup_status["can_open_voting"]:
        issues_str = ", ".join(setup_status["open_issues"])
        raise VotingStateError(
            f"competition is not ready for voting: {issues_str}",
            issues=setup_status["open_issues"],
        )


def _resolve_channels(competition: Competition, channels: list[str] | None) -> set[VoteChannel]:
    selected = set(channels or [])
    if not selected:
        if competition.public_voting_enabled:
            selected.add("public")
        if competition.judge_voting_enabled:
            selected.add("judge")

    invalid = selected - {"public", "judge"}
    if invalid:
        raise VotingStateError(f"invalid voting channels: {', '.join(sorted(invalid))}")
    if "public" in selected and not competition.public_voting_enabled:
        raise VotingStateError("public voting is disabled for this competition")
    if "judge" in selected and not competition.judge_voting_enabled:
        raise VotingStateError("judge voting is disabled for this competition")
    if not selected:
        raise VotingStateError("no voting channels selected")
    return selected  # type: ignore[return-value]


def _open_channels(voting_session: VotingSession, channels: set[VoteChannel]) -> None:
    if "public" in channels and voting_session.public_voting_open:
        raise VotingStateError("public voting is already open")
    if "judge" in channels and voting_session.judge_voting_open:
        raise VotingStateError("judge voting is already open")
    if "public" in channels:
        voting_session.public_voting_open = True
    if "judge" in channels:
        voting_session.judge_voting_open = True
