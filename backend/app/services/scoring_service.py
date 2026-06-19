from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Competition,
    CompetitionStatus,
    JudgeCriterionVote,
    JudgeVote,
    Participant,
    PublicCriterionVote,
    PublicVote,
    PublicVoteMethod,
    ResultSnapshot,
    VotingSession,
)
from app.services import audit_service
from app.services.admin_service import get_competition

RANKED_CHOICE_POINTS = {1: 3.0, 2: 2.0, 3: 1.0}


@dataclass(frozen=True)
class ComponentScore:
    enabled: bool
    weight: float
    raw_score: float
    normalized_score: float


class ResultsFreezeError(Exception):
    def __init__(self, message: str, status_code: int = 409) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_competition_results(db: Session, competition_id: str) -> dict[str, object]:
    competition = get_competition(db, competition_id)
    final_snapshot = _get_final_snapshot(db, competition.id)
    if final_snapshot is not None:
        return final_snapshot.results_json
    return calculate_live_results(db, competition)


def calculate_live_results(db: Session, competition: Competition) -> dict[str, object]:
    voting_session = _get_latest_voting_session(db, competition.id)
    participants = _list_active_participants(db, competition.id)

    public_scores = _calculate_public_scores(db, competition, voting_session, participants)
    judge_scores = _calculate_judge_scores(db, competition, voting_session, participants)
    public_weight, judge_weight = _normalized_component_weights(competition)

    results = []
    for participant in participants:
        public_score = public_scores[participant.id]
        judge_score = judge_scores[participant.id]
        final_score = (
            public_score.normalized_score * public_weight
            + judge_score.normalized_score * judge_weight
        )
        results.append(
            {
                "participant_id": participant.id,
                "display_name": participant.display_name,
                "rank": 0,
                "final_score": round(final_score, 4),
                "public_score": _component_to_dict(public_score),
                "judge_score": _component_to_dict(judge_score),
            }
        )

    results.sort(key=lambda item: (-item["final_score"], item["display_name"]))
    for index, item in enumerate(results, start=1):
        item["rank"] = index

    return {
        "competition_id": competition.id,
        "voting_session_id": voting_session.id if voting_session is not None else None,
        "results": results,
    }


def freeze_competition_results(
    db: Session,
    competition_id: str,
    snapshot_name: str,
    created_by_admin_id: str | None = None,
) -> ResultSnapshot:
    competition = get_competition(db, competition_id)
    existing = _get_final_snapshot(db, competition.id)
    if existing is not None:
        raise ResultsFreezeError("competition results are already frozen")

    results = calculate_live_results(db, competition)
    snapshot = ResultSnapshot(
        competition_id=competition.id,
        snapshot_name=snapshot_name,
        results_json=results,
        created_by_admin_id=created_by_admin_id,
        is_final=True,
    )
    competition.status = CompetitionStatus.RESULTS_FROZEN
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_results_frozen",
        entity_type="result_snapshot",
        entity_id=snapshot.id,
        details_json={"snapshot_name": snapshot_name, "is_final": True},
    )
    return snapshot


def get_final_results(db: Session, competition_id: str) -> ResultSnapshot:
    competition = get_competition(db, competition_id)
    snapshot = _get_final_snapshot(db, competition.id)
    if snapshot is None:
        raise ResultsFreezeError("competition results are not frozen", status_code=404)
    return snapshot


def _get_final_snapshot(db: Session, competition_id: str) -> ResultSnapshot | None:
    return db.scalar(
        select(ResultSnapshot)
        .where(
            ResultSnapshot.competition_id == competition_id,
            ResultSnapshot.is_final.is_(True),
        )
        .order_by(ResultSnapshot.created_at.desc())
    )


def _list_active_participants(db: Session, competition_id: str) -> list[Participant]:
    return list(
        db.scalars(
            select(Participant)
            .where(
                Participant.competition_id == competition_id,
                Participant.active.is_(True),
            )
            .order_by(Participant.order_index, Participant.display_name)
        )
    )


def _get_latest_voting_session(db: Session, competition_id: str) -> VotingSession | None:
    return db.scalar(
        select(VotingSession)
        .where(VotingSession.competition_id == competition_id)
        .order_by(VotingSession.opened_at.desc(), VotingSession.created_at.desc())
    )


def _calculate_public_scores(
    db: Session,
    competition: Competition,
    voting_session: VotingSession | None,
    participants: list[Participant],
) -> dict[str, ComponentScore]:
    if not competition.public_voting_enabled or competition.public_weight <= 0:
        return _disabled_scores(participants)
    if voting_session is None:
        return _zero_scores(participants, enabled=True, weight=competition.public_weight)

    raw_scores = {participant.id: 0.0 for participant in participants}
    if competition.public_vote_method is PublicVoteMethod.SINGLE_CHOICE:
        raw_scores.update(_single_choice_raw_scores(db, competition.id, voting_session.id))
        return _normalize_raw_scores(raw_scores, participants, competition.public_weight)
    elif competition.public_vote_method is PublicVoteMethod.RANKED_CHOICE:
        raw_scores.update(_ranked_choice_raw_scores(db, competition.id, voting_session.id))
        return _normalize_raw_scores(raw_scores, participants, competition.public_weight)
    elif competition.public_vote_method is PublicVoteMethod.CRITERIA_RATING:
        raw_scores.update(_public_criteria_raw_scores(db, competition.id, voting_session.id))
        return _bounded_scores(raw_scores, participants, competition.public_weight)

    return _zero_scores(participants, enabled=True, weight=competition.public_weight)


def _single_choice_raw_scores(
    db: Session,
    competition_id: str,
    voting_session_id: str,
) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    for participant_id in db.scalars(
        select(PublicVote.participant_id).where(
            PublicVote.competition_id == competition_id,
            PublicVote.voting_session_id == voting_session_id,
            PublicVote.vote_method == PublicVoteMethod.SINGLE_CHOICE,
        )
    ):
        scores[participant_id] += 1
    return dict(scores)


def _ranked_choice_raw_scores(
    db: Session,
    competition_id: str,
    voting_session_id: str,
) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    votes = db.scalars(
        select(PublicVote).where(
            PublicVote.competition_id == competition_id,
            PublicVote.voting_session_id == voting_session_id,
            PublicVote.vote_method == PublicVoteMethod.RANKED_CHOICE,
        )
    )
    for vote in votes:
        if vote.rank_position is None:
            continue
        scores[vote.participant_id] += RANKED_CHOICE_POINTS.get(vote.rank_position, 0)
    return dict(scores)


def _public_criteria_raw_scores(
    db: Session,
    competition_id: str,
    voting_session_id: str,
) -> dict[str, float]:
    vote_scores: defaultdict[str, list[float]] = defaultdict(list)
    votes = db.scalars(
        select(PublicVote)
        .where(
            PublicVote.competition_id == competition_id,
            PublicVote.voting_session_id == voting_session_id,
            PublicVote.vote_method == PublicVoteMethod.CRITERIA_RATING,
        )
        .options(
            selectinload(PublicVote.criterion_votes).selectinload(PublicCriterionVote.criterion)
        )
    )
    for vote in votes:
        score = _weighted_criterion_score(vote.criterion_votes)
        if score is not None:
            vote_scores[vote.participant_id].append(score)
    return {
        participant_id: sum(scores) / len(scores)
        for participant_id, scores in vote_scores.items()
        if scores
    }


def _calculate_judge_scores(
    db: Session,
    competition: Competition,
    voting_session: VotingSession | None,
    participants: list[Participant],
) -> dict[str, ComponentScore]:
    if not competition.judge_voting_enabled or competition.judge_weight <= 0:
        return _disabled_scores(participants)
    if voting_session is None:
        return _zero_scores(participants, enabled=True, weight=competition.judge_weight)

    participant_scores: defaultdict[str, list[float]] = defaultdict(list)
    votes = db.scalars(
        select(JudgeVote)
        .where(
            JudgeVote.competition_id == competition.id,
            JudgeVote.voting_session_id == voting_session.id,
        )
        .options(
            selectinload(JudgeVote.criterion_votes).selectinload(JudgeCriterionVote.criterion)
        )
    )
    for vote in votes:
        score = _weighted_criterion_score(vote.criterion_votes)
        if score is not None:
            participant_scores[vote.participant_id].append(score)

    raw_scores = {
        participant.id: (
            sum(participant_scores[participant.id]) / len(participant_scores[participant.id])
            if participant_scores[participant.id]
            else 0.0
        )
        for participant in participants
    }
    return _bounded_scores(raw_scores, participants, competition.judge_weight)


def _weighted_criterion_score(
    criterion_votes: list[PublicCriterionVote] | list[JudgeCriterionVote],
) -> float | None:
    weighted_total = 0.0
    weight_total = 0.0
    for criterion_vote in criterion_votes:
        criterion = criterion_vote.criterion
        if criterion.max_score <= criterion.min_score:
            continue
        normalized_score = (
            (criterion_vote.score - criterion.min_score)
            / (criterion.max_score - criterion.min_score)
            * 100
        )
        weighted_total += normalized_score * criterion.weight
        weight_total += criterion.weight
    if weight_total <= 0:
        return None
    return weighted_total / weight_total


def _normalized_component_weights(competition: Competition) -> tuple[float, float]:
    public_weight = (
        competition.public_weight
        if competition.public_voting_enabled and competition.public_weight > 0
        else 0.0
    )
    judge_weight = (
        competition.judge_weight
        if competition.judge_voting_enabled and competition.judge_weight > 0
        else 0.0
    )
    total_weight = public_weight + judge_weight
    if total_weight <= 0:
        return 0.0, 0.0
    return public_weight / total_weight, judge_weight / total_weight


def _normalize_raw_scores(
    raw_scores: dict[str, float],
    participants: list[Participant],
    weight: float,
) -> dict[str, ComponentScore]:
    max_score = max(raw_scores.values(), default=0.0)
    return {
        participant.id: ComponentScore(
            enabled=True,
            weight=weight,
            raw_score=round(raw_scores.get(participant.id, 0.0), 4),
            normalized_score=round(
                raw_scores.get(participant.id, 0.0) / max_score * 100 if max_score > 0 else 0.0,
                4,
            ),
        )
        for participant in participants
    }


def _bounded_scores(
    raw_scores: dict[str, float],
    participants: list[Participant],
    weight: float,
) -> dict[str, ComponentScore]:
    return {
        participant.id: ComponentScore(
            enabled=True,
            weight=weight,
            raw_score=round(raw_scores.get(participant.id, 0.0), 4),
            normalized_score=round(min(max(raw_scores.get(participant.id, 0.0), 0.0), 100.0), 4),
        )
        for participant in participants
    }


def _zero_scores(
    participants: list[Participant],
    enabled: bool,
    weight: float,
) -> dict[str, ComponentScore]:
    return {
        participant.id: ComponentScore(
            enabled=enabled,
            weight=weight,
            raw_score=0.0,
            normalized_score=0.0,
        )
        for participant in participants
    }


def _disabled_scores(participants: list[Participant]) -> dict[str, ComponentScore]:
    return _zero_scores(participants, enabled=False, weight=0.0)


def _component_to_dict(score: ComponentScore) -> dict[str, float | bool]:
    return {
        "enabled": score.enabled,
        "weight": score.weight,
        "raw_score": score.raw_score,
        "normalized_score": score.normalized_score,
    }
