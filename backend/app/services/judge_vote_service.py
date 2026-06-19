from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Competition,
    CompetitionJudge,
    JudgeCriterion,
    JudgeCriterionVote,
    JudgeVote,
    Participant,
    VotingSession,
)
from app.schemas.judge_vote import JudgeVoteSubmit
from app.services import access_service, audit_service
from app.services.admin_service import get_competition
from app.services.voting_service import ensure_can_accept_votes


class JudgeVoteError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def list_accessible_competitions(
    db: Session,
    judge_id: str,
    access_code: str,
) -> list[Competition]:
    return access_service.list_judge_competitions(db, judge_id, access_code)


def submit_judge_vote(
    db: Session,
    competition_id: str,
    payload: JudgeVoteSubmit,
) -> JudgeVote:
    judge = access_service.verify_judge_access(db, payload.judge_id, payload.access_code)
    competition = get_competition(db, competition_id)
    _ensure_judge_can_vote(db, competition, judge.id)
    voting_session = ensure_can_accept_votes(db, competition_id)
    participant = _get_active_participant(db, competition.id, payload.participant_id)

    _validate_criteria_payload(db, competition.id, payload.criteria)
    _delete_existing_vote(db, competition.id, voting_session.id, judge.id, participant.id)

    judge_vote = JudgeVote(
        competition_id=competition.id,
        participant_id=participant.id,
        judge_id=judge.id,
        voting_session_id=voting_session.id,
    )
    for criterion_vote in payload.criteria:
        judge_vote.criterion_votes.append(
            JudgeCriterionVote(
                criterion_id=criterion_vote.criterion_id,
                score=criterion_vote.score,
            )
        )
    db.add(judge_vote)
    db.commit()
    db.refresh(judge_vote)
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        actor_type="judge",
        actor_id=judge.id,
        actor_label=judge.display_name,
        action="judge_vote_submitted",
        entity_type="judge_vote",
        entity_id=judge_vote.id,
        details_json={
            "participant_id": participant.id,
            "criteria_count": len(payload.criteria),
            "voting_session_id": voting_session.id,
        },
    )
    return judge_vote


def list_judge_votes(
    db: Session,
    competition_id: str,
    judge_id: str,
    access_code: str,
) -> list[JudgeVote]:
    judge = access_service.verify_judge_access(db, judge_id, access_code)
    competition = get_competition(db, competition_id)
    _ensure_judge_can_vote(db, competition, judge.id)
    voting_session = _get_relevant_voting_session(db, competition_id)
    if voting_session is None:
        return []
    return list(
        db.scalars(
            select(JudgeVote)
            .where(
                JudgeVote.competition_id == competition_id,
                JudgeVote.judge_id == judge.id,
                JudgeVote.voting_session_id == voting_session.id,
            )
            .options(selectinload(JudgeVote.criterion_votes))
            .order_by(JudgeVote.created_at.asc())
        )
    )


def get_judge_vote_status(
    db: Session,
    competition_id: str,
    judge_id: str,
    access_code: str,
) -> dict[str, object]:
    competition = get_competition(db, competition_id)
    judge = access_service.verify_judge_access(db, judge_id, access_code)
    _ensure_judge_can_vote(db, competition, judge.id)
    voting_session = _get_relevant_voting_session(db, competition_id)
    total_participants = db.scalar(
        select(func.count()).select_from(Participant).where(
            Participant.competition_id == competition_id,
            Participant.active.is_(True),
        )
    )
    total_participants = total_participants or 0
    voted_participants = 0
    session_status = None
    voting_session_id = None
    if voting_session is not None:
        voting_session_id = voting_session.id
        session_status = voting_session.status
        voted_participants = db.scalar(
            select(func.count(func.distinct(JudgeVote.participant_id))).where(
                JudgeVote.competition_id == competition_id,
                JudgeVote.judge_id == judge.id,
                JudgeVote.voting_session_id == voting_session.id,
            )
        ) or 0
    return {
        "competition_id": competition_id,
        "judge_id": judge.id,
        "voting_session_id": voting_session_id,
        "voting_session_status": session_status,
        "total_participants": total_participants,
        "voted_participants": voted_participants,
        "completed": voting_session is not None and voted_participants == total_participants,
    }


def _ensure_judge_can_vote(db: Session, competition: Competition, judge_id: str) -> None:
    if not competition.judge_voting_enabled:
        raise JudgeVoteError("judge voting is disabled for this competition", status_code=409)
    assignment = db.scalar(
        select(CompetitionJudge).where(
            CompetitionJudge.competition_id == competition.id,
            CompetitionJudge.judge_id == judge_id,
            CompetitionJudge.active.is_(True),
        )
    )
    if assignment is None:
        raise JudgeVoteError("judge is not assigned to this competition", status_code=403)


def _validate_criteria_payload(
    db: Session,
    competition_id: str,
    criteria_payload,
) -> None:
    criteria = {
        criterion.id: criterion
        for criterion in db.scalars(
            select(JudgeCriterion).where(
                JudgeCriterion.competition_id == competition_id,
                JudgeCriterion.active.is_(True),
            )
        )
    }
    criterion_ids = [item.criterion_id for item in criteria_payload]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise JudgeVoteError("criteria cannot contain duplicates")
    if set(criterion_ids) != set(criteria):
        raise JudgeVoteError("one or more judge criteria are invalid")
    for item in criteria_payload:
        criterion = criteria[item.criterion_id]
        if not criterion.min_score <= item.score <= criterion.max_score:
            raise JudgeVoteError("criterion score is outside the allowed range")


def _delete_existing_vote(
    db: Session,
    competition_id: str,
    voting_session_id: str,
    judge_id: str,
    participant_id: str,
) -> None:
    vote_ids = list(
        db.scalars(
            select(JudgeVote.id).where(
                JudgeVote.competition_id == competition_id,
                JudgeVote.voting_session_id == voting_session_id,
                JudgeVote.judge_id == judge_id,
                JudgeVote.participant_id == participant_id,
            )
        )
    )
    if not vote_ids:
        return
    db.execute(delete(JudgeCriterionVote).where(JudgeCriterionVote.judge_vote_id.in_(vote_ids)))
    db.execute(delete(JudgeVote).where(JudgeVote.id.in_(vote_ids)))


def _get_active_participant(db: Session, competition_id: str, participant_id: str) -> Participant:
    participant = db.scalar(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.competition_id == competition_id,
            Participant.active.is_(True),
        )
    )
    if participant is None:
        raise JudgeVoteError("participant is not active for this competition")
    return participant


def _get_relevant_voting_session(db: Session, competition_id: str) -> VotingSession | None:
    return db.scalar(
        select(VotingSession)
        .where(VotingSession.competition_id == competition_id)
        .order_by(VotingSession.opened_at.desc(), VotingSession.created_at.desc())
    )
