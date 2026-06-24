import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Competition, Event, Participant, VoterAccount
from app.services import voter_account_service
from app.services.admin_service import AdminStateError


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def event(db_session):
    e = Event(name="E", description=None)
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def competition(db_session, event):
    c = Competition(event_id=event.id, name="C")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture()
def participant(db_session, competition):
    p = Participant(competition_id=competition.id, name="anna", display_name="Anna")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def test_create_voter_account(db_session, event):
    va, code = voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "Votante 1", "notes": None}
    )
    assert va.id is not None
    assert va.display_name == "Votante 1"
    assert len(code) == 8
    assert va.access_token is not None
    assert va.access_code_hash != code  # hash stored, not plaintext


def test_list_voter_accounts(db_session, event):
    voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "A", "notes": None}
    )
    voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "B", "notes": None}
    )
    accounts = voter_account_service.list_voter_accounts(db_session, event.id)
    assert len(accounts) == 2


def test_regenerate_voter_code(db_session, event):
    va, old_code = voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "V", "notes": None}
    )
    va2, new_code = voter_account_service.regenerate_voter_code(db_session, va.id)
    assert new_code != old_code
    assert len(new_code) == 8


def test_link_participant(db_session, event, participant):
    va, _ = voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "V", "notes": None}
    )
    updated = voter_account_service.link_participant(db_session, va.id, participant.id)
    assert updated.voter_account_id == va.id


def test_link_participant_wrong_event(db_session, event, participant):
    other_event = Event(name="Other", description=None)
    db_session.add(other_event)
    db_session.commit()
    db_session.refresh(other_event)
    va, _ = voter_account_service.create_voter_account(
        db_session, other_event.id, {"display_name": "V", "notes": None}
    )
    with pytest.raises(AdminStateError):
        voter_account_service.link_participant(db_session, va.id, participant.id)


def test_unlink_participant(db_session, event, participant):
    va, _ = voter_account_service.create_voter_account(
        db_session, event.id, {"display_name": "V", "notes": None}
    )
    voter_account_service.link_participant(db_session, va.id, participant.id)
    voter_account_service.unlink_participant(db_session, va.id, participant.id)
    db_session.refresh(participant)
    assert participant.voter_account_id is None
