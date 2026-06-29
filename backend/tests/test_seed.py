from app.db import Base
from app.models import VoterAccount
from app.seed import create_demo_data
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def test_create_demo_data_idempotent():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        event1 = create_demo_data(session)
        session.commit()
        event2 = create_demo_data(session)
        session.commit()
        assert event1.id == event2.id


def test_seed_creates_voter_accounts():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        event = create_demo_data(session)
        session.commit()
        accounts = list(session.scalars(
            select(VoterAccount).where(VoterAccount.event_id == event.id)
        ))
        assert len(accounts) == 6


def test_seed_links_participants_to_voter_accounts():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        event = create_demo_data(session)
        session.commit()
        session.refresh(event)
        for comp in event.competitions:
            linked = [p for p in comp.participants if p.voter_account_id is not None]
            assert len(linked) == 4
