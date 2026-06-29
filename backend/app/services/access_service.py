import random
import string
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, CompetitionJudge, Judge, VoterAccount
from app.models.mixins import utc_now

_VOTER_CODE_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_VOTER_CODE_LENGTH = 8


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def generate_voter_code() -> str:
    return "".join(random.choices(_VOTER_CODE_CHARSET, k=_VOTER_CODE_LENGTH))


def verify_voter_account(
    db: Session,
    voter_account_id: str,
    access_token: str,
) -> VoterAccount:
    va = db.get(VoterAccount, voter_account_id)
    if va is None or va.access_token != access_token or not va.active:
        raise VoterAccessError("invalid voter credentials", status_code=403)
    return va


def get_voter_account_by_token(db: Session, access_token: str) -> VoterAccount:
    va = db.scalar(
        select(VoterAccount).where(VoterAccount.access_token == access_token)
    )
    if va is None or not va.active:
        raise VoterAccessError("voter account not found or inactive", status_code=404)
    return va


def get_voter_account_by_code(
    db: Session,
    event_id: str,
    access_code: str,
) -> VoterAccount:
    code_hash = hash_secret(access_code)
    va = db.scalar(
        select(VoterAccount).where(
            VoterAccount.event_id == event_id,
            VoterAccount.access_code_hash == code_hash,
            VoterAccount.active.is_(True),
        )
    )
    if va is None:
        raise VoterAccessError("invalid access code", status_code=403)
    return va


def verify_judge_access(
    db: Session,
    judge_id: str,
    access_code: str,
) -> Judge:
    judge = db.get(Judge, judge_id)
    if judge is None or judge.access_code_hash != hash_secret(access_code) or not judge.active:
        raise JudgeAccessError("invalid judge credentials", status_code=403)
    return judge



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


class VoterAccessError(Exception):
    def __init__(self, message: str, status_code: int = 403) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


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


def get_or_create_voter_session(*args, **kwargs):  # type: ignore[no-untyped-def]
    raise NotImplementedError("VoterSession removed; use VoterAccount instead")
