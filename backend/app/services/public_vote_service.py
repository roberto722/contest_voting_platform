from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Competition,
    Participant,
    PublicCriterionVote,
    PublicVote,
    PublicVoteCriterion,
    PublicVoteMethod,
    VotingSession,
    VotingSessionStatus,
)
from app.schemas.public_vote import PublicCriteriaRatingInput, PublicVoteSubmit
from app.services import access_service
from app.services import audit_service
from app.services.admin_service import get_competition
from app.services.voting_service import ensure_can_accept_votes


class PublicVoteError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def submit_public_vote(
    db: Session,
    competition_id: str,
    payload: PublicVoteSubmit,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> list[PublicVote]:
    competition = get_competition(db, competition_id)
    voting_session = ensure_can_accept_votes(db, competition_id)
    _validate_public_voting_enabled(competition, payload.method)

    voter_session = access_service.get_or_create_voter_session(
        db,
        event_id=competition.event_id,
        voter_token=payload.voter_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    voted_session_ids = _get_voted_session_ids_for_competition(db, competition.id, voter_session.id)
    if voting_session.id not in voted_session_ids:
        if len(voted_session_ids) + 1 > competition.max_votes_per_competition:
            raise PublicVoteError(
                f"voter has reached the maximum number of votes ({competition.max_votes_per_competition}) for this competition",
                status_code=409,
            )

    existing_votes = _list_existing_votes(db, voting_session.id, voter_session.id)
    if existing_votes and not competition.allow_vote_update:
        raise PublicVoteError("voter has already voted in this voting session", status_code=409)
    replaced_existing = bool(existing_votes)
    if existing_votes:
        _delete_existing_votes(db, voting_session.id, voter_session.id)

    votes = _build_votes(db, competition, voting_session, voter_session.id, payload)
    db.add_all(votes)
    db.commit()
    for vote in votes:
        db.refresh(vote)
    audit_service.record_audit_log(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        actor_type="public",
        actor_id=voter_session.id,
        actor_label="Votante anonimo",
        action="public_vote_submitted",
        entity_type="public_vote",
        entity_id=votes[0].id,
        details_json={
            "method": payload.method.value,
            "votes_saved": len(votes),
            "replaced_existing": replaced_existing,
        },
    )
    return votes


def get_public_vote_summary(db: Session, competition_id: str) -> dict[str, object]:
    competition = get_competition(db, competition_id)
    voting_session = _get_summary_voting_session(db, competition_id)
    participants = list(
        db.scalars(
            select(Participant)
            .where(Participant.competition_id == competition_id)
            .order_by(Participant.order_index, Participant.display_name)
        )
    )
    counts: Counter[str] = Counter()
    if voting_session is not None:
        counts.update(
            db.scalars(
                select(PublicVote.participant_id).where(
                    PublicVote.competition_id == competition.id,
                    PublicVote.voting_session_id == voting_session.id,
                )
            )
        )

    return {
        "competition_id": competition.id,
        "voting_session_id": voting_session.id if voting_session else None,
        "total_votes": sum(counts.values()),
        "participants": [
            {
                "participant_id": participant.id,
                "display_name": participant.display_name,
                "vote_count": counts[participant.id],
            }
            for participant in participants
        ],
    }


def _validate_public_voting_enabled(
    competition: Competition,
    submitted_method: PublicVoteMethod,
) -> None:
    if not competition.public_voting_enabled:
        raise PublicVoteError("public voting is disabled for this competition", status_code=409)
    if competition.public_vote_method != submitted_method:
        raise PublicVoteError("vote method does not match competition configuration")


def _get_voted_session_ids_for_competition(
    db: Session,
    competition_id: str,
    voter_session_id: str,
) -> set[str]:
    return set(
        db.scalars(
            select(PublicVote.voting_session_id)
            .where(
                PublicVote.competition_id == competition_id,
                PublicVote.voter_session_id == voter_session_id,
            )
            .distinct()
        )
    )


def _list_existing_votes(
    db: Session,
    voting_session_id: str,
    voter_session_id: str,
) -> list[PublicVote]:
    return list(
        db.scalars(
            select(PublicVote).where(
                PublicVote.voting_session_id == voting_session_id,
                PublicVote.voter_session_id == voter_session_id,
            )
        )
    )


def _delete_existing_votes(db: Session, voting_session_id: str, voter_session_id: str) -> None:
    vote_ids = list(
        db.scalars(
            select(PublicVote.id).where(
                PublicVote.voting_session_id == voting_session_id,
                PublicVote.voter_session_id == voter_session_id,
            )
        )
    )
    if not vote_ids:
        return
    db.execute(delete(PublicCriterionVote).where(PublicCriterionVote.public_vote_id.in_(vote_ids)))
    db.execute(delete(PublicVote).where(PublicVote.id.in_(vote_ids)))


def _build_votes(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    voter_session_id: str,
    payload: PublicVoteSubmit,
) -> list[PublicVote]:
    if payload.method is PublicVoteMethod.SINGLE_CHOICE:
        return [
            _build_single_choice_vote(
                db,
                competition,
                voting_session,
                voter_session_id,
                payload,
            )
        ]
    if payload.method is PublicVoteMethod.RANKED_CHOICE:
        return _build_ranked_choice_votes(
            db,
            competition,
            voting_session,
            voter_session_id,
            payload,
        )
    if payload.method is PublicVoteMethod.CRITERIA_RATING:
        return _build_criteria_rating_votes(
            db,
            competition,
            voting_session,
            voter_session_id,
            payload,
        )
    raise PublicVoteError("unsupported public vote method")


def _build_single_choice_vote(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    voter_session_id: str,
    payload: PublicVoteSubmit,
) -> PublicVote:
    if payload.participant_id is None:
        raise PublicVoteError("participant_id is required for single_choice")
    participant = _get_active_participant(db, competition.id, payload.participant_id)
    return PublicVote(
        competition_id=competition.id,
        participant_id=participant.id,
        voting_session_id=voting_session.id,
        voter_session_id=voter_session_id,
        vote_method=PublicVoteMethod.SINGLE_CHOICE,
        value=1,
    )


def _build_ranked_choice_votes(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    voter_session_id: str,
    payload: PublicVoteSubmit,
) -> list[PublicVote]:
    participant_ids = payload.ranked_participant_ids or []
    if not participant_ids:
        raise PublicVoteError("ranked_participant_ids is required for ranked_choice")
    if len(participant_ids) != len(set(participant_ids)):
        raise PublicVoteError("ranked_participant_ids cannot contain duplicates")
    if len(participant_ids) > competition.max_votes_per_user:
        raise PublicVoteError("ranked choice exceeds max_votes_per_user")

    active_participants = _get_active_participants_by_id(db, competition.id, participant_ids)
    return [
        PublicVote(
            competition_id=competition.id,
            participant_id=active_participants[participant_id].id,
            voting_session_id=voting_session.id,
            voter_session_id=voter_session_id,
            vote_method=PublicVoteMethod.RANKED_CHOICE,
            rank_position=index,
        )
        for index, participant_id in enumerate(participant_ids, start=1)
    ]


def _build_criteria_rating_votes(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    voter_session_id: str,
    payload: PublicVoteSubmit,
) -> list[PublicVote]:
    ratings = payload.ratings or []
    if not ratings:
        raise PublicVoteError("ratings is required for criteria_rating")
    participant_ids = [rating.participant_id for rating in ratings]
    if len(participant_ids) != len(set(participant_ids)):
        raise PublicVoteError("ratings cannot contain duplicate participants")
    if len(participant_ids) > competition.max_votes_per_user:
        raise PublicVoteError("criteria rating exceeds max_votes_per_user")

    participants = _get_active_participants_by_id(db, competition.id, participant_ids)
    criteria = _get_active_public_criteria_by_id(db, competition.id)
    return [
        _build_criteria_rating_vote(
            competition,
            voting_session,
            voter_session_id,
            participants[rating.participant_id],
            criteria,
            rating,
        )
        for rating in ratings
    ]


def _build_criteria_rating_vote(
    competition: Competition,
    voting_session: VotingSession,
    voter_session_id: str,
    participant: Participant,
    criteria: dict[str, PublicVoteCriterion],
    rating: PublicCriteriaRatingInput,
) -> PublicVote:
    criterion_ids = [criterion_vote.criterion_id for criterion_vote in rating.criteria]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise PublicVoteError("criteria rating cannot contain duplicate criteria")

    public_vote = PublicVote(
        competition_id=competition.id,
        participant_id=participant.id,
        voting_session_id=voting_session.id,
        voter_session_id=voter_session_id,
        vote_method=PublicVoteMethod.CRITERIA_RATING,
    )
    for criterion_vote in rating.criteria:
        criterion = criteria.get(criterion_vote.criterion_id)
        if criterion is None:
            raise PublicVoteError("criterion is not active for this competition")
        if not criterion.min_score <= criterion_vote.score <= criterion.max_score:
            raise PublicVoteError("criterion score is outside the allowed range")
        public_vote.criterion_votes.append(
            PublicCriterionVote(criterion_id=criterion.id, score=criterion_vote.score)
        )
    return public_vote


def _get_active_participant(db: Session, competition_id: str, participant_id: str) -> Participant:
    participant = db.scalar(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.competition_id == competition_id,
            Participant.active.is_(True),
        )
    )
    if participant is None:
        raise PublicVoteError("participant is not active for this competition")
    return participant


def _get_active_participants_by_id(
    db: Session,
    competition_id: str,
    participant_ids: list[str],
) -> dict[str, Participant]:
    participants = {
        participant.id: participant
        for participant in db.scalars(
            select(Participant).where(
                Participant.id.in_(participant_ids),
                Participant.competition_id == competition_id,
                Participant.active.is_(True),
            )
        )
    }
    if set(participant_ids) != set(participants):
        raise PublicVoteError("one or more participants are not active for this competition")
    return participants


def _get_active_public_criteria_by_id(
    db: Session,
    competition_id: str,
) -> dict[str, PublicVoteCriterion]:
    return {
        criterion.id: criterion
        for criterion in db.scalars(
            select(PublicVoteCriterion).where(
                PublicVoteCriterion.competition_id == competition_id,
                PublicVoteCriterion.active.is_(True),
            )
        )
    }


def _get_summary_voting_session(db: Session, competition_id: str) -> VotingSession | None:
    return db.scalar(
        select(VotingSession)
        .where(
            VotingSession.competition_id == competition_id,
            VotingSession.status.in_(
                [VotingSessionStatus.OPEN, VotingSessionStatus.CLOSED],
            ),
        )
        .options(selectinload(VotingSession.public_votes))
        .order_by(VotingSession.opened_at.desc(), VotingSession.created_at.desc())
    )
