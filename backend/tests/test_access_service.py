import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Event, VoterAccount
from app.services.access_service import (
    VoterAccessError,
    generate_voter_code,
    get_voter_account_by_code,
    get_voter_account_by_token,
    hash_secret,
    verify_voter_account,
)


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
def event_and_voter(db_session):
    event = Event(name="E", description=None)
    db_session.add(event)
    db_session.flush()
    code = "ABCD1234"
    va = VoterAccount(
        event_id=event.id,
        display_name="Tester",
        access_code_hash=hash_secret(code),
        access_token="test-token-uuid",
        active=True,
    )
    db_session.add(va)
    db_session.flush()
    return event, va, code


def test_generate_voter_code():
    code = generate_voter_code()
    assert len(code) == 8
    assert all(c in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" for c in code)


def test_verify_voter_account_ok(db_session, event_and_voter):
    event, va, _ = event_and_voter
    result = verify_voter_account(db_session, va.id, "test-token-uuid")
    assert result.id == va.id


def test_verify_voter_account_wrong_token(db_session, event_and_voter):
    event, va, _ = event_and_voter
    with pytest.raises(VoterAccessError) as exc:
        verify_voter_account(db_session, va.id, "wrong-token")
    assert exc.value.status_code == 403


def test_verify_voter_account_inactive(db_session, event_and_voter):
    event, va, _ = event_and_voter
    va.active = False
    db_session.flush()
    with pytest.raises(VoterAccessError):
        verify_voter_account(db_session, va.id, "test-token-uuid")


def test_get_voter_account_by_token(db_session, event_and_voter):
    event, va, _ = event_and_voter
    result = get_voter_account_by_token(db_session, "test-token-uuid")
    assert result.id == va.id


def test_get_voter_account_by_code(db_session, event_and_voter):
    event, va, code = event_and_voter
    result = get_voter_account_by_code(db_session, event.id, code)
    assert result.id == va.id


def test_get_voter_account_by_code_wrong(db_session, event_and_voter):
    event, va, _ = event_and_voter
    with pytest.raises(VoterAccessError):
        get_voter_account_by_code(db_session, event.id, "WRONGCOD")
