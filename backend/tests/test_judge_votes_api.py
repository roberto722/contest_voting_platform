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


def _create_judge_competition(client: TestClient) -> tuple[str, str, str, list[str], list[str]]:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest giudici",
            "judge_voting_enabled": True,
        },
    ).json()["id"]
    judge = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    ).json()
    client.post(f"/api/competitions/{competition_id}/judges/{judge['id']}")
    participant_ids = [
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name},
        ).json()["id"]
        for name in ["Anna", "Marco"]
    ]
    criterion_ids = [
        client.post(
            f"/api/competitions/{competition_id}/judge-criteria",
            json={"name": name, "min_score": 1, "max_score": 10, "weight": 1},
        ).json()["id"]
        for name in ["Tecnica", "Presenza"]
    ]
    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1"},
    )
    return event_id, competition_id, judge["id"], participant_ids, criterion_ids


def test_judge_can_access_assigned_competitions_and_update_vote(client: TestClient) -> None:
    event_id, competition_id, judge_id, participant_ids, criterion_ids = (
        _create_judge_competition(client)
    )

    access = client.post(
        "/api/judge-access",
        json={"judge_id": judge_id, "access_code": "secret"},
    )
    assert access.status_code == 200
    assert len(access.json()["competitions"]) == 1

    first_vote = client.post(
        f"/api/competitions/{competition_id}/judge-votes",
        json={
            "judge_id": judge_id,
            "access_code": "secret",
            "participant_id": participant_ids[0],
            "criteria": [
                {"criterion_id": criterion_ids[0], "score": 8},
                {"criterion_id": criterion_ids[1], "score": 7},
            ],
        },
    )
    assert first_vote.status_code == 200

    logs = client.get(f"/api/events/{event_id}/audit-logs")
    assert logs.status_code == 200
    actions = [item["action"] for item in logs.json()]
    assert "judge_access_granted" in actions
    assert "judge_vote_submitted" in actions

    updated_vote = client.post(
        f"/api/competitions/{competition_id}/judge-votes",
        json={
            "judge_id": judge_id,
            "access_code": "secret",
            "participant_id": participant_ids[0],
            "criteria": [
                {"criterion_id": criterion_ids[0], "score": 9},
                {"criterion_id": criterion_ids[1], "score": 9},
            ],
        },
    )
    assert updated_vote.status_code == 200

    status = client.get(
        f"/api/competitions/{competition_id}/judge-votes/status",
        params={"judge_id": judge_id, "access_code": "secret"},
    )
    assert status.status_code == 200
    assert status.json()["total_participants"] == 2
    assert status.json()["voted_participants"] == 1
    assert status.json()["completed"] is False

    saved_votes = client.get(
        f"/api/competitions/{competition_id}/judge-votes",
        params={"judge_id": judge_id, "access_code": "secret"},
    )
    assert saved_votes.status_code == 200
    saved_payload = saved_votes.json()
    assert len(saved_payload) == 1
    assert saved_payload[0]["participant_id"] == participant_ids[0]
    assert {
        item["criterion_id"]: item["score"]
        for item in saved_payload[0]["criterion_votes"]
    } == {
        criterion_ids[0]: 9,
        criterion_ids[1]: 9,
    }


def test_judge_vote_blocks_after_session_closes(client: TestClient) -> None:
    _, competition_id, judge_id, participant_ids, criterion_ids = _create_judge_competition(client)

    closed = client.post(
        f"/api/competitions/{competition_id}/voting-sessions/close",
        json={},
    )
    assert closed.status_code == 200

    response = client.post(
        f"/api/competitions/{competition_id}/judge-votes",
        json={
            "judge_id": judge_id,
            "access_code": "secret",
            "participant_id": participant_ids[0],
            "criteria": [
                {"criterion_id": criterion_ids[0], "score": 8},
                {"criterion_id": criterion_ids[1], "score": 7},
            ],
        },
    )
    assert response.status_code == 409

    saved_votes = client.get(
        f"/api/competitions/{competition_id}/judge-votes",
        params={"judge_id": judge_id, "access_code": "secret"},
    )
    assert saved_votes.status_code == 200
