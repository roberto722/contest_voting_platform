from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccessMethod, Competition, CompetitionJudge, Judge, VoterSession
from app.models.mixins import utc_now


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def verify_judge_access(
    db: Session,
    judge_id: str,
    access_code: str,
) -> Judge:
    judge = db.get(Judge, judge_id)
    if judge is None or judge.access_code_hash != hash_secret(access_code) or not judge.active:
        raise JudgeAccessError("invalid judge credentials", status_code=403)
    return judge


def verify_public_competition_access(
    db: Session,
    competition_id: str,
    pin: str | None = None,
) -> Competition:
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise PublicAccessError("competition not found", status_code=404)
    if competition.access_method is AccessMethod.QR_PIN:
        if not pin or competition.access_pin_hash != hash_secret(pin):
            raise PublicAccessError("invalid competition pin", status_code=403)
    return competition


def list_judge_competitions(db: Session, judge_id: str, access_code: str) -> list[Competition]:
    judge = verify_judge_access(db, judge_id, access_code)
    assignments = db.scalars(
        select(Competition)
        .join(CompetitionJudge, CompetitionJudge.competition_id == Competition.id)
        .where(
            CompetitionJudge.judge_id == judge.id,
            CompetitionJudge.active.is_(True),
            Competition.id == CompetitionJudge.competition_id,
        )
        .order_by(Competition.created_at.desc())
    )
    return list(assignments)


class JudgeAccessError(Exception):
    def __init__(self, message: str, status_code: int = 403) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class PublicAccessError(Exception):
    def __init__(self, message: str, status_code: int = 403) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_or_create_voter_session(
    db: Session,
    event_id: str,
    voter_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VoterSession:
    voter_token_hash = hash_secret(voter_token)
    voter_session = db.scalar(
        select(VoterSession).where(
            VoterSession.event_id == event_id,
            VoterSession.voter_token_hash == voter_token_hash,
        )
    )
    now = utc_now()
    if voter_session is not None:
        voter_session.last_seen_at = now
        db.add(voter_session)
        db.flush()
        return voter_session

    voter_session = VoterSession(
        event_id=event_id,
        voter_token_hash=voter_token_hash,
        ip_hash=hash_secret(ip_address) if ip_address else None,
        user_agent_hash=hash_secret(user_agent) if user_agent else None,
        created_at=now,
        last_seen_at=now,
    )
    db.add(voter_session)
    db.flush()
    return voter_session
