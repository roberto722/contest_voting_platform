from collections.abc import Generator

import pytest
from app.db import Base
from app.models import (
    AccessMethod,
    Competition,
    CompetitionJudge,
    CompetitionStatus,
    Event,
    EventStatus,
    Judge,
    JudgeCriterion,
    JudgeCriterionVote,
    JudgeVote,
    Participant,
    PublicCriterionVote,
    PublicVote,
    PublicVoteCriterion,
    PublicVoteMethod,
    ResultSnapshot,
    ScreenMode,
    ScreenState,
    VoterAccount,
    VotingSession,
    VotingSessionStatus,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as db:
        yield db

    Base.metadata.drop_all(engine)


def test_event_competition_participant_judge_and_criteria_relationships(session: Session) -> None:
    event = Event(name="Contest Live", description="Demo", status=EventStatus.DRAFT)
    competition = Competition(
        event=event,
        name="Competizione libera",
        description="Configurabile",
        public_vote_method=PublicVoteMethod.SINGLE_CHOICE,
        access_method=AccessMethod.PUBLIC_LINK,
        status=CompetitionStatus.READY,
    )
    participant = Participant(
        competition=competition,
        name="anna",
        display_name="Anna",
        order_index=1,
    )
    public_criterion = PublicVoteCriterion(
        competition=competition,
        name="Impatto",
        min_score=1,
        max_score=10,
        weight=1,
        order_index=1,
    )
    judge_criterion = JudgeCriterion(
        competition=competition,
        name="Tecnica",
        min_score=1,
        max_score=10,
        weight=2,
        order_index=1,
    )
    judge = Judge(event=event, name="judge-1", display_name="Giudice 1", access_code_hash="hash")
    assignment = CompetitionJudge(competition=competition, judge=judge)

    session.add_all([event, participant, public_criterion, judge_criterion, assignment])
    session.commit()

    saved_event = session.scalar(select(Event).where(Event.name == "Contest Live"))

    assert saved_event is not None
    assert saved_event.status is EventStatus.DRAFT
    assert saved_event.competitions[0].participants[0].display_name == "Anna"
    assert saved_event.competitions[0].public_criteria[0].name == "Impatto"
    assert saved_event.competitions[0].judge_criteria[0].weight == 2
    assert saved_event.judges[0].competitions[0].competition.name == "Competizione libera"


def test_voting_sessions_public_votes_and_judge_votes(session: Session) -> None:
    event = Event(name="Contest")
    competition = Competition(event=event, name="Open vote")
    participant = Participant(competition=competition, name="marco", display_name="Marco")
    voting_session = VotingSession(
        competition=competition,
        label="Round 1",
        status=VotingSessionStatus.OPEN,
    )
    voter = VoterAccount(
        event=event,
        display_name="Tester",
        access_code_hash="code-hash",
        access_token="token-uuid",
        active=True,
    )
    public_vote = PublicVote(
        competition=competition,
        participant=participant,
        voting_session=voting_session,
        voter_account=voter,
        vote_method=PublicVoteMethod.CRITERIA_RATING,
        value=1,
    )
    criterion = PublicVoteCriterion(competition=competition, name="Energia")
    criterion_vote = PublicCriterionVote(public_vote=public_vote, criterion=criterion, score=8)
    judge = Judge(event=event, name="judge", display_name="Judge", access_code_hash="judge-hash")
    judge_criterion = JudgeCriterion(competition=competition, name="Presenza")
    judge_vote = JudgeVote(
        competition=competition,
        participant=participant,
        judge=judge,
        voting_session=voting_session,
    )
    judge_score = JudgeCriterionVote(judge_vote=judge_vote, criterion=judge_criterion, score=9)

    session.add_all([event, criterion_vote, judge_score])
    session.commit()

    saved_competition = session.scalar(select(Competition).where(Competition.name == "Open vote"))

    assert saved_competition is not None
    assert saved_competition.voting_sessions[0].status is VotingSessionStatus.OPEN
    assert saved_competition.public_votes[0].criterion_votes[0].score == 8
    assert saved_competition.judge_votes[0].criterion_votes[0].score == 9


def test_result_snapshot_and_screen_state_store_json_payloads(session: Session) -> None:
    event = Event(name="Contest")
    competition = Competition(event=event, name="Finale")
    snapshot = ResultSnapshot(
        competition=competition,
        snapshot_name="Finale",
        results_json={"ranking": [{"participant": "Anna", "score": 100}]},
        is_final=True,
    )
    screen_state = ScreenState(
        event=event,
        competition=competition,
        mode=ScreenMode.SHOW_RESULTS,
        payload_json={"title": "Classifica"},
    )

    session.add_all([snapshot, screen_state])
    session.commit()

    saved_snapshot = session.scalar(select(ResultSnapshot))
    saved_screen = session.scalar(select(ScreenState))

    assert saved_snapshot is not None
    assert saved_snapshot.results_json["ranking"][0]["score"] == 100
    assert saved_snapshot.is_final is True
    assert saved_screen is not None
    assert saved_screen.mode is ScreenMode.SHOW_RESULTS
    assert saved_screen.payload_json["title"] == "Classifica"


def test_voter_account_creation(session: Session) -> None:
    event = Event(name="Test Event", description=None)
    session.add(event)
    session.flush()
    va = VoterAccount(
        event_id=event.id,
        display_name="Votante Test",
        access_code_hash="abc123hash",
        access_token="some-uuid-token",
        active=True,
    )
    session.add(va)
    session.flush()
    assert va.id is not None
    assert va.event_id == event.id
    assert va.access_token == "some-uuid-token"

