from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Competition,
    CompetitionStatus,
    JudgeCriterionVote,
    JudgeVote,
    Participant,
    PublicVote,
    ResultSnapshot,
    VotingSession,
)
from app.services.admin_service import get_competition

PUBLIC_SCORE_FORMULA = "100 * sqrt(votes / max_votes)"


@dataclass(frozen=True)
class PublicScore:
    votes: int
    max_votes: int
    score: float


@dataclass(frozen=True)
class JudgeScore:
    score: float
    votes_count: int
    criteria_breakdown: list[dict[str, Any]]


def get_competition_results(db: Session, competition_id: str) -> dict[str, object]:
    competition = get_competition(db, competition_id)
    snapshot = _get_final_snapshot(db, competition.id)
    if snapshot is not None or competition.status is CompetitionStatus.RESULTS_FROZEN:
        if snapshot is not None:
            results = dict(snapshot.results_json)
            results["is_final"] = True
            return results
    return calculate_live_results(db, competition)


def freeze_competition_results(
    db: Session,
    competition_id: str,
    created_by_admin_id: str | None = None,
) -> dict[str, object]:
    competition = get_competition(db, competition_id)
    existing_snapshot = _get_final_snapshot(db, competition.id)
    if existing_snapshot is not None:
        results = dict(existing_snapshot.results_json)
        results["is_final"] = True
        return results

    results = calculate_live_results(db, competition)
    results["is_final"] = True
    snapshot = ResultSnapshot(
        competition_id=competition.id,
        snapshot_name="Final results",
        results_json=results,
        created_by_admin_id=created_by_admin_id,
        is_final=True,
    )
    competition.status = CompetitionStatus.RESULTS_FROZEN
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return dict(snapshot.results_json)


def calculate_live_results(db: Session, competition: Competition) -> dict[str, object]:
    voting_session = _get_latest_voting_session(db, competition.id)
    participants = _list_active_participants(db, competition.id)
    public_scores = calculate_public_scores(db, competition, voting_session, participants)
    judge_scores = calculate_judge_scores(db, competition, voting_session, participants)
    public_weight, judge_weight = calculate_final_weights(competition)

    results: list[dict[str, Any]] = []
    for participant in participants:
        public_score = public_scores[participant.id]
        judge_score = judge_scores[participant.id]
        final_score = (
            public_score.score * public_weight
            + judge_score.score * judge_weight
        )
        results.append(
            {
                "participant_id": participant.id,
                "participant_name": participant.display_name,
                "display_name": participant.display_name,
                "rank": 0,
                "final_score": round_score(final_score),
                "public_score": public_score.score,
                "judge_score": judge_score.score,
                "public_votes": public_score.votes,
                "judge_votes_count": judge_score.votes_count,
                "details": {
                    "public": {
                        "votes": public_score.votes,
                        "max_votes": public_score.max_votes,
                        "formula": PUBLIC_SCORE_FORMULA,
                    },
                    "judges": {
                        "criteria_breakdown": judge_score.criteria_breakdown,
                        "judges_completed": judge_score.votes_count,
                    },
                },
            }
        )

    results = rank_participants(results)
    return {
        "competition_id": competition.id,
        "voting_session_id": voting_session.id if voting_session is not None else None,
        "is_final": False,
        "results": results,
    }


def calculate_public_scores(
    db: Session,
    competition: Competition,
    voting_session: VotingSession | None,
    participants: list[Participant],
) -> dict[str, PublicScore]:
    if not competition.public_voting_enabled or voting_session is None:
        return {
            participant.id: PublicScore(votes=0, max_votes=0, score=0.0)
            for participant in participants
        }

    counts = _public_vote_counts(db, competition.id, voting_session.id)
    max_votes = max(counts.values(), default=0)
    return {
        participant.id: PublicScore(
            votes=counts.get(participant.id, 0),
            max_votes=max_votes,
            score=calculate_public_score(counts.get(participant.id, 0), max_votes),
        )
        for participant in participants
    }


def calculate_public_score(votes: int, max_votes: int) -> float:
    if max_votes <= 0 or votes <= 0:
        return 0.0
    return round_score(100 * math.sqrt(votes / max_votes))


def calculate_judge_scores(
    db: Session,
    competition: Competition,
    voting_session: VotingSession | None,
    participants: list[Participant],
) -> dict[str, JudgeScore]:
    if not competition.judge_voting_enabled or voting_session is None:
        return {
            participant.id: JudgeScore(score=0.0, votes_count=0, criteria_breakdown=[])
            for participant in participants
        }

    participant_scores: defaultdict[str, list[tuple[str, float]]] = defaultdict(list)
    criteria_breakdowns: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
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
        score = calculate_single_judge_score(vote.criterion_votes)
        if score is None:
            continue
        participant_scores[vote.participant_id].append((vote.judge_id, score))
        criteria_breakdowns[vote.participant_id].extend(
            _judge_criteria_breakdown(vote.criterion_votes)
        )

    return {
        participant.id: _build_judge_score(
            participant_scores[participant.id],
            criteria_breakdowns[participant.id],
        )
        for participant in participants
    }


def calculate_single_judge_score(
    criterion_votes: list[JudgeCriterionVote],
) -> float | None:
    weighted_total = 0.0
    weight_total = 0.0
    for criterion_vote in criterion_votes:
        criterion = criterion_vote.criterion
        if criterion.max_score <= criterion.min_score or criterion.weight <= 0:
            continue
        normalized_score = 100 * (
            (criterion_vote.score - criterion.min_score)
            / (criterion.max_score - criterion.min_score)
        )
        weighted_total += normalized_score * criterion.weight
        weight_total += criterion.weight
    if weight_total <= 0:
        return None
    return weighted_total / weight_total


def calculate_final_weights(competition: Competition) -> tuple[float, float]:
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


def rank_participants(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda item: (
            -item["final_score"],
            -item["judge_score"],
            -item["public_score"],
            -item["public_votes"],
            item["participant_name"].casefold(),
            item["participant_id"],
        ),
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def round_score(value: float) -> float:
    return round(value + 0.000000001, 2)


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


def _public_vote_counts(
    db: Session,
    competition_id: str,
    voting_session_id: str,
) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    participant_ids = db.scalars(
        select(PublicVote.participant_id).where(
            PublicVote.competition_id == competition_id,
            PublicVote.voting_session_id == voting_session_id,
        )
    )
    for participant_id in participant_ids:
        counts[participant_id] += 1
    return dict(counts)


def _build_judge_score(
    scores_by_judge: list[tuple[str, float]],
    criteria_breakdown: list[dict[str, Any]],
) -> JudgeScore:
    if not scores_by_judge:
        return JudgeScore(score=0.0, votes_count=0, criteria_breakdown=[])
    judge_ids = {judge_id for judge_id, _ in scores_by_judge}
    average = sum(score for _, score in scores_by_judge) / len(scores_by_judge)
    return JudgeScore(
        score=round_score(average),
        votes_count=len(judge_ids),
        criteria_breakdown=criteria_breakdown,
    )


def _judge_criteria_breakdown(
    criterion_votes: list[JudgeCriterionVote],
) -> list[dict[str, Any]]:
    breakdown = []
    for criterion_vote in criterion_votes:
        criterion = criterion_vote.criterion
        if criterion.max_score <= criterion.min_score:
            continue
        normalized_score = 100 * (
            (criterion_vote.score - criterion.min_score)
            / (criterion.max_score - criterion.min_score)
        )
        breakdown.append(
            {
                "criterion_id": criterion.id,
                "criterion_name": criterion.name,
                "score": round_score(criterion_vote.score),
                "normalized_score": round_score(normalized_score),
                "weight": criterion.weight,
            }
        )
    return breakdown
