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


def _create_competition(
    client: TestClient,
    method: str = "single_choice",
    allow_vote_update: bool = False,
    max_votes_per_user: int = 1,
    max_votes_per_competition: int = 1,
) -> tuple[str, str, list[str]]:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest",
            "public_vote_method": method,
            "allow_vote_update": allow_vote_update,
            "max_votes_per_user": max_votes_per_user,
            "max_votes_per_competition": max_votes_per_competition,
            "judge_voting_enabled": False,  # Disabilitato per i test pubblici standard
        },
    ).json()["id"]

    # Se il metodo è criteria_rating, aggiungi criteri pubblici
    if method == "criteria_rating":
        client.post(
            f"/api/competitions/{competition_id}/public-criteria",
            json={"name": "Criterio 1", "weight": 1.0, "order_index": 1},
        )

    participant_ids = [
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name},
        ).json()["id"]
        for name in ["Anna", "Marco", "Luca"]
    ]
    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    return event_id, competition_id, participant_ids


def _open_voting(client: TestClient, competition_id: str) -> str:
    return client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1"},
    ).json()["id"]


def test_public_vote_requires_open_session_and_blocks_duplicates(client: TestClient) -> None:
    event_id, competition_id, participant_ids = _create_competition(client)
    payload = {
        "voter_token": "anon-1",
        "method": "single_choice",
        "participant_id": participant_ids[0],
    }

    closed_response = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload)
    assert closed_response.status_code == 409

    voting_session_id = _open_voting(client, competition_id)
    created = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload)
    assert created.status_code == 201
    assert created.json()["voting_session_id"] == voting_session_id
    assert created.json()["votes"][0]["participant_id"] == participant_ids[0]

    logs = client.get(f"/api/events/{event_id}/audit-logs")
    assert logs.status_code == 200
    assert "public_vote_submitted" in [item["action"] for item in logs.json()]

    duplicate = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload)
    assert duplicate.status_code == 409


def test_public_access_validates_qr_pin(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    public_link_competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Link pubblico"},
    ).json()["id"]
    pin_competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "QR PIN",
            "access_method": "qr_pin",
            "access_pin": "1234",
        },
    ).json()["id"]

    public_link = client.post(
        f"/api/competitions/{public_link_competition_id}/public-access",
        json={},
    )
    missing_pin = client.post(
        f"/api/competitions/{pin_competition_id}/public-access",
        json={},
    )
    wrong_pin = client.post(
        f"/api/competitions/{pin_competition_id}/public-access",
        json={"pin": "0000"},
    )
    valid_pin = client.post(
        f"/api/competitions/{pin_competition_id}/public-access",
        json={"pin": "1234"},
    )

    assert public_link.status_code == 200
    assert public_link.json()["access_granted"] is True
    assert missing_pin.status_code == 403
    assert wrong_pin.status_code == 403
    assert valid_pin.status_code == 200
    assert valid_pin.json()["access_method"] == "qr_pin"


def test_public_vote_update_replaces_previous_vote_when_allowed(client: TestClient) -> None:
    event_id, competition_id, participant_ids = _create_competition(client, allow_vote_update=True)
    _open_voting(client, competition_id)

    first = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "anon-1",
            "method": "single_choice",
            "participant_id": participant_ids[0],
        },
    )
    assert first.status_code == 201

    updated = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "anon-1",
            "method": "single_choice",
            "participant_id": participant_ids[1],
        },
    )
    assert updated.status_code == 201

    summary = client.get(f"/api/competitions/{competition_id}/public-votes/summary")
    counts = {item["participant_id"]: item["vote_count"] for item in summary.json()["participants"]}
    assert summary.json()["total_votes"] == 1
    assert counts[participant_ids[0]] == 0
    assert counts[participant_ids[1]] == 1

    logs = client.get(f"/api/events/{event_id}/audit-logs")
    assert logs.status_code == 200
    assert [item["action"] for item in logs.json()].count("public_vote_submitted") == 2


def test_public_vote_supports_ranked_choice_and_criteria_rating(client: TestClient) -> None:
    ranked_event_id, ranked_competition_id, ranked_participant_ids = _create_competition(
        client,
        method="ranked_choice",
        max_votes_per_user=3,
    )
    _open_voting(client, ranked_competition_id)

    ranked = client.post(
        f"/api/competitions/{ranked_competition_id}/public-votes",
        json={
            "voter_token": "ranked-voter",
            "method": "ranked_choice",
            "ranked_participant_ids": ranked_participant_ids,
        },
    )
    assert ranked.status_code == 201
    assert [vote["rank_position"] for vote in ranked.json()["votes"]] == [1, 2, 3]

    ranked_logs = client.get(f"/api/events/{ranked_event_id}/audit-logs")
    assert ranked_logs.status_code == 200
    assert "public_vote_submitted" in [item["action"] for item in ranked_logs.json()]

    criteria_event_id, criteria_competition_id, criteria_participant_ids = _create_competition(
        client,
        method="criteria_rating",
        max_votes_per_user=2,
    )
    criterion_id = client.get(
        f"/api/competitions/{criteria_competition_id}/public-criteria"
    ).json()[0]["id"]
    _open_voting(client, criteria_competition_id)

    criteria = client.post(
        f"/api/competitions/{criteria_competition_id}/public-votes",
        json={
            "voter_token": "criteria-voter",
            "method": "criteria_rating",
            "ratings": [
                {
                    "participant_id": criteria_participant_ids[0],
                    "criteria": [{"criterion_id": criterion_id, "score": 8}],
                }
            ],
        },
    )
    assert criteria.status_code == 201
    assert criteria.json()["votes"][0]["vote_method"] == "criteria_rating"

    criteria_logs = client.get(f"/api/events/{criteria_event_id}/audit-logs")
    assert criteria_logs.status_code == 200
    assert "public_vote_submitted" in [item["action"] for item in criteria_logs.json()]


def test_public_vote_limits_per_competition(client: TestClient) -> None:
    # Create competition with max_votes_per_competition=2
    event_id, competition_id, participant_ids = _create_competition(
        client,
        allow_vote_update=True,
        max_votes_per_competition=2,
    )

    payload_1 = {
        "voter_token": "voter-1",
        "method": "single_choice",
        "participant_id": participant_ids[0],
    }
    payload_2 = {
        "voter_token": "voter-2",
        "method": "single_choice",
        "participant_id": participant_ids[0],
    }

    # Round 1
    session_1_id = _open_voting(client, competition_id)
    # voter-1 votes in Round 1
    r1 = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload_1)
    assert r1.status_code == 201
    # Close Round 1
    client.post(f"/api/competitions/{competition_id}/voting-sessions/close", json={})

    # Round 2
    session_2_id = _open_voting(client, competition_id)
    # voter-1 votes in Round 2 (voted in 2 unique sessions now)
    r2 = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload_1)
    assert r2.status_code == 201

    # voter-1 updates their vote in Round 2 (allowed since allow_vote_update is True and it's the same session)
    r2_update = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "voter-1",
            "method": "single_choice",
            "participant_id": participant_ids[1],
        },
    )
    assert r2_update.status_code == 201

    # Close Round 2
    client.post(f"/api/competitions/{competition_id}/voting-sessions/close", json={})

    # Round 3
    _open_voting(client, competition_id)
    # voter-1 tries to vote in Round 3 (rejected because they already voted in session 1 and 2, exceeding limit of 2)
    r3_fail = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload_1)
    assert r3_fail.status_code == 409
    assert "voter has reached the maximum number of votes" in r3_fail.json()["detail"]

    # voter-2 votes in Round 3 (allowed since they only voted in 0 sessions so far)
    r3_success = client.post(f"/api/competitions/{competition_id}/public-votes", json=payload_2)
    assert r3_success.status_code == 201

