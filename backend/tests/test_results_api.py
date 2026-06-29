from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
from app.models import (
    Competition,
    CompetitionStatus,
    Event,
    EventStatus,
    Judge,
    JudgeCriterion,
    JudgeCriterionVote,
    JudgeVote,
    Participant,
    PublicVote,
    PublicVoteMethod,
    VoterAccount,
    VotingSession,
    VotingSessionStatus,
)
from app.models.mixins import utc_now
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as session:
        yield session

    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_competition(
    db: Session,
    *,
    public_weight: float = 40,
    judge_weight: float = 60,
    public_voting_enabled: bool = True,
    judge_voting_enabled: bool = True,
) -> tuple[Competition, list[Participant], VotingSession]:
    event = Event(name="Serata Live", status=EventStatus.LIVE)
    competition = Competition(
        event=event,
        name="Contest",
        status=CompetitionStatus.VOTING_OPEN,
        public_vote_method=PublicVoteMethod.SINGLE_CHOICE,
        public_weight=public_weight,
        judge_weight=judge_weight,
        public_voting_enabled=public_voting_enabled,
        judge_voting_enabled=judge_voting_enabled,
        max_votes_per_user=3,
    )
    participants = [
        Participant(competition=competition, name=name.lower(), display_name=name, order_index=index)
        for index, name in enumerate(["A", "B", "C"], start=1)
    ]
    voting_session = VotingSession(
        competition=competition,
        label="Round 1",
        status=VotingSessionStatus.OPEN,
        opened_at=utc_now(),
    )
    db.add_all([event, competition, *participants, voting_session])
    db.commit()
    return competition, participants, voting_session


def _add_public_votes(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    participant: Participant,
    count: int,
    *,
    offset: int = 0,
) -> None:
    for index in range(count):
        voter = VoterAccount(
            event_id=competition.event_id,
            display_name=f"Voter {participant.display_name}-{offset + index}",
            access_code_hash="hash",
            access_token=f"token-{participant.display_name}-{offset + index}",
        )
        db.add(voter)
        db.flush()
        db.add(
            PublicVote(
                competition_id=competition.id,
                participant_id=participant.id,
                voting_session_id=voting_session.id,
                voter_account_id=voter.id,
                vote_method=PublicVoteMethod.SINGLE_CHOICE,
                value=1,
            )
        )
    db.commit()


def _add_judge_scores(
    db: Session,
    competition: Competition,
    voting_session: VotingSession,
    participants: list[Participant],
    scores_by_participant: dict[str, float],
    *,
    judge_count: int = 4,
) -> None:
    criterion = JudgeCriterion(
        competition_id=competition.id,
        name="Tecnica",
        min_score=0,
        max_score=100,
        weight=1,
    )
    db.add(criterion)
    db.flush()
    for judge_index in range(judge_count):
        judge = Judge(
            event_id=competition.event_id,
            name=f"judge-{judge_index}",
            display_name=f"Giudice {judge_index}",
            access_code_hash="hash",
        )
        db.add(judge)
        db.flush()
        for participant in participants:
            vote = JudgeVote(
                competition_id=competition.id,
                participant_id=participant.id,
                judge_id=judge.id,
                voting_session_id=voting_session.id,
            )
            vote.criterion_votes.append(
                JudgeCriterionVote(criterion_id=criterion.id, score=scores_by_participant[participant.id])
            )
            db.add(vote)
    db.commit()


def test_results_apply_requested_public_sqrt_formula_and_40_60_final_score(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(db_session)
    _add_public_votes(db_session, competition, voting_session, participants[0], 80)
    _add_public_votes(db_session, competition, voting_session, participants[1], 50, offset=100)
    _add_public_votes(db_session, competition, voting_session, participants[2], 20, offset=200)
    _add_judge_scores(
        db_session,
        competition,
        voting_session,
        participants,
        {
            participants[0].id: 78,
            participants[1].id: 90,
            participants[2].id: 85,
        },
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["participant_name"] for item in results] == ["A", "B", "C"]
    assert [item["final_score"] for item in results] == [86.8, 85.62, 71.0]
    assert [item["public_score"] for item in results] == [100.0, 79.06, 50.0]
    assert [item["judge_score"] for item in results] == [78.0, 90.0, 85.0]
    assert [item["public_votes"] for item in results] == [80, 50, 20]
    assert results[0]["details"]["public"]["formula"] == "100 * sqrt(votes / max_votes)"
    assert results[0]["details"]["public"]["max_votes"] == 80
    assert results[0]["judge_votes_count"] == 4


def test_results_public_score_is_zero_when_max_votes_is_zero(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, _, _ = _create_competition(
        db_session,
        public_weight=100,
        judge_weight=0,
        judge_voting_enabled=False,
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    assert [item["public_score"] for item in response.json()["results"]] == [0.0, 0.0, 0.0]
    assert [item["final_score"] for item in response.json()["results"]] == [0.0, 0.0, 0.0]


def test_results_average_four_judges_with_weighted_criteria(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=0,
        judge_weight=100,
        public_voting_enabled=False,
    )
    criteria = [
        JudgeCriterion(competition_id=competition.id, name="A", min_score=1, max_score=10, weight=2),
        JudgeCriterion(competition_id=competition.id, name="B", min_score=0, max_score=5, weight=1),
    ]
    db_session.add_all(criteria)
    db_session.flush()
    for judge_index, scores in enumerate([(10, 5), (8, 4), (6, 3), (4, 2)], start=1):
        judge = Judge(
            event_id=competition.event_id,
            name=f"judge-{judge_index}",
            display_name=f"Giudice {judge_index}",
            access_code_hash="hash",
        )
        db_session.add(judge)
        db_session.flush()
        vote = JudgeVote(
            competition_id=competition.id,
            participant_id=participants[0].id,
            judge_id=judge.id,
            voting_session_id=voting_session.id,
        )
        vote.criterion_votes.extend(
            [
                JudgeCriterionVote(criterion_id=criteria[0].id, score=scores[0]),
                JudgeCriterionVote(criterion_id=criteria[1].id, score=scores[1]),
            ]
        )
        db_session.add(vote)
    db_session.commit()

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["participant_name"] == "A"
    assert result["judge_score"] == 67.78
    assert result["final_score"] == 67.78
    assert result["judge_votes_count"] == 4


def test_results_apply_50_50_final_score(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=50,
        judge_weight=50,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 80)
    _add_judge_scores(
        db_session,
        competition,
        voting_session,
        participants,
        {
            participants[0].id: 78,
            participants[1].id: 0,
            participants[2].id: 0,
        },
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    assert response.json()["results"][0]["final_score"] == 89.0


def test_results_ignore_public_component_when_public_weight_is_zero(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=0,
        judge_weight=100,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 10)
    _add_judge_scores(
        db_session,
        competition,
        voting_session,
        participants,
        {
            participants[0].id: 20,
            participants[1].id: 80,
            participants[2].id: 0,
        },
        judge_count=1,
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["participant_name"] == "B"
    assert results[0]["final_score"] == 80.0


def test_results_ignore_judge_component_when_judge_weight_is_zero(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=100,
        judge_weight=0,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 10)
    _add_public_votes(db_session, competition, voting_session, participants[1], 5, offset=100)
    _add_judge_scores(
        db_session,
        competition,
        voting_session,
        participants,
        {
            participants[0].id: 0,
            participants[1].id: 100,
            participants[2].id: 0,
        },
        judge_count=1,
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["participant_name"] == "A"
    assert results[0]["final_score"] == 100.0


def test_results_tie_break_uses_higher_judge_score(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=50,
        judge_weight=50,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 1)
    _add_judge_scores(
        db_session,
        competition,
        voting_session,
        participants,
        {
            participants[0].id: 0,
            participants[1].id: 100,
            participants[2].id: 0,
        },
        judge_count=1,
    )

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["participant_name"] == "B"
    assert results[0]["final_score"] == results[1]["final_score"]
    assert results[0]["judge_score"] > results[1]["judge_score"]


def test_results_tie_break_uses_higher_public_score_when_judge_score_is_equal(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=0,
        judge_weight=0,
        judge_voting_enabled=False,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 10)
    _add_public_votes(db_session, competition, voting_session, participants[1], 5, offset=100)

    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["participant_name"] == "A"
    assert results[0]["final_score"] == results[1]["final_score"]
    assert results[0]["judge_score"] == results[1]["judge_score"]
    assert results[0]["public_score"] > results[1]["public_score"]


def test_freeze_results_returns_snapshot_and_does_not_recalculate(
    client: TestClient,
    db_session: Session,
) -> None:
    competition, participants, voting_session = _create_competition(
        db_session,
        public_weight=100,
        judge_weight=0,
        judge_voting_enabled=False,
    )
    _add_public_votes(db_session, competition, voting_session, participants[0], 1)

    freeze_response = client.post(f"/api/competitions/{competition.id}/results/freeze")
    assert freeze_response.status_code == 200
    frozen_results = freeze_response.json()["results"]
    assert frozen_results[0]["participant_name"] == "A"

    _add_public_votes(db_session, competition, voting_session, participants[1], 10, offset=100)
    response = client.get(f"/api/competitions/{competition.id}/results")

    assert response.status_code == 200
    assert response.json()["is_final"] is True
    assert response.json()["results"] == frozen_results
