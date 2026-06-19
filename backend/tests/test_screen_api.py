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


def _create_ready_public_competition(client: TestClient, event_id: str) -> str:
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Contest", "judge_voting_enabled": False},
    ).json()["id"]
    for index, name in enumerate(["Anna", "Marco"], start=1):
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name, "order_index": index},
        )
    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    return competition_id


def test_admin_can_update_screen_state(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = _create_ready_public_competition(client, event_id)

    default_state = client.get(f"/api/events/{event_id}/screen-state")
    updated = client.put(
        f"/api/events/{event_id}/screen-state",
        json={
            "competition_id": competition_id,
            "mode": "show_results",
            "payload_json": {"title": "Classifica"},
        },
    )

    assert default_state.status_code == 200
    assert default_state.json()["mode"] == "idle"
    assert updated.status_code == 200
    assert updated.json()["competition_id"] == competition_id
    assert updated.json()["mode"] == "show_results"
    assert updated.json()["payload_json"]["title"] == "Classifica"


def test_screen_websocket_receives_screen_state_updates(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = _create_ready_public_competition(client, event_id)

    with client.websocket_connect(f"/ws/events/{event_id}/screen") as websocket:
        initial_message = websocket.receive_json()
        client.put(
            f"/api/events/{event_id}/screen-state",
            json={
                "competition_id": competition_id,
                "mode": "show_qr",
                "payload_json": {"title": "Vota ora"},
            },
        )
        update_message = websocket.receive_json()

    assert initial_message["type"] == "screen_state"
    assert initial_message["screen_state"]["mode"] == "idle"
    assert update_message["type"] == "screen_state"
    assert update_message["screen_state"]["competition_id"] == competition_id
    assert update_message["screen_state"]["mode"] == "show_qr"


def test_screen_supporting_endpoints_work_for_fresh_competition(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = _create_ready_public_competition(client, event_id)
    client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1"},
    )
    client.put(
        f"/api/events/{event_id}/screen-state",
        json={
            "competition_id": competition_id,
            "mode": "show_results",
            "payload_json": {"title": "Classifica"},
        },
    )

    competition = client.get(f"/api/competitions/{competition_id}")
    sessions = client.get(f"/api/competitions/{competition_id}/voting-sessions")
    summary = client.get(f"/api/competitions/{competition_id}/public-votes/summary")
    results = client.get(f"/api/competitions/{competition_id}/results")

    assert competition.status_code == 200
    assert sessions.status_code == 200
    assert summary.status_code == 200
    assert results.status_code == 200
    assert results.json()["competition_id"] == competition_id
