from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
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
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def _setup_event_and_participant(client: TestClient) -> tuple[str, str, str]:
    event_id = client.post("/api/events", json={"name": "E"}).json()["id"]
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "C", "judge_voting_enabled": False},
    ).json()["id"]
    p_id = client.post(
        f"/api/competitions/{comp_id}/participants",
        json={"name": "anna", "display_name": "Anna"},
    ).json()["id"]
    return event_id, comp_id, p_id


def test_create_voter_account(client: TestClient) -> None:
    event_id, _, _ = _setup_event_and_participant(client)
    resp = client.post(
        f"/api/events/{event_id}/voter-accounts",
        json={"display_name": "Votante 1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_code" in data
    assert len(data["access_code"]) == 8
    assert data["voter_account"]["display_name"] == "Votante 1"
    assert "access_code_hash" not in data["voter_account"]


def test_list_voter_accounts(client: TestClient) -> None:
    event_id, _, _ = _setup_event_and_participant(client)
    client.post(f"/api/events/{event_id}/voter-accounts", json={"display_name": "A"})
    client.post(f"/api/events/{event_id}/voter-accounts", json={"display_name": "B"})
    resp = client.get(f"/api/events/{event_id}/voter-accounts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_regenerate_code(client: TestClient) -> None:
    event_id, _, _ = _setup_event_and_participant(client)
    va_id = client.post(
        f"/api/events/{event_id}/voter-accounts",
        json={"display_name": "V"},
    ).json()["voter_account"]["id"]
    resp = client.post(f"/api/voter-accounts/{va_id}/regenerate-code")
    assert resp.status_code == 200
    assert "access_code" in resp.json()


def test_link_and_unlink_participant(client: TestClient) -> None:
    event_id, _, p_id = _setup_event_and_participant(client)
    va_id = client.post(
        f"/api/events/{event_id}/voter-accounts",
        json={"display_name": "V"},
    ).json()["voter_account"]["id"]
    link_resp = client.post(
        f"/api/voter-accounts/{va_id}/link-participant",
        json={"participant_id": p_id},
    )
    assert link_resp.status_code == 200
    assert link_resp.json()["voter_account_id"] == va_id

    unlink_resp = client.delete(
        f"/api/voter-accounts/{va_id}/unlink-participant/{p_id}"
    )
    assert unlink_resp.status_code == 204
