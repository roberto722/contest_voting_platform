from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import Competition, Event, Judge, Participant
from app.seed import create_demo_data


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as db:
        yield db

    Base.metadata.drop_all(engine)


def test_create_demo_data_populates_event_competitions_participants_and_judges(
    session: Session,
) -> None:
    event = create_demo_data(session)
    session.commit()

    saved_event = session.scalar(select(Event).where(Event.id == event.id))
    competitions = session.scalars(select(Competition)).all()
    participants = session.scalars(select(Participant)).all()
    judges = session.scalars(select(Judge)).all()

    assert saved_event is not None
    assert saved_event.name == "Serata Contest Demo"
    assert {competition.name for competition in competitions} == {
        "Miglior Performance Musicale",
        "Miglior Costume",
    }
    assert len(participants) == 8
    assert len(judges) == 3
    assert all(competition.judge_criteria for competition in competitions)
