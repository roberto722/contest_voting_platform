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


def _create_voter_account(client: TestClient, event_id: str, name: str = "Votante Test") -> tuple[str, str]:
    resp = client.post(
        f"/api/events/{event_id}/voter-accounts",
        json={"display_name": name},
    )
    assert resp.status_code == 201
    va = resp.json()["voter_account"]
    return va["id"], va["access_token"]


def _create_competition(
    client: TestClient,
    method: str = "single_choice",
    allow_vote_update: bool = False,
    max_votes_per_user: int = 1,
    max_votes_per_competition: int = 1,
    voters_to_create: list[str] = None,
) -> tuple[str, str, list[str], list[tuple[str, str]]]:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest",
            "public_vote_method": method,
            "allow_vote_update": allow_vote_update,
            "max_votes_per_user": max_votes_per_user,
            "max_votes_per_competition": max_votes_per_competition,
            "judge_voting_enabled": False,
        },
    ).json()["id"]

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

    voters = []
    if voters_to_create:
        for voter_name in voters_to_create:
            voters.append(_create_voter_account(client, event_id, name=voter_name))
    else:
        voters.append(_create_voter_account(client, event_id))

    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    return event_id, competition_id, participant_ids, voters


def _open_voting(client: TestClient, competition_id: str) -> str:
    return client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1"},
    ).json()["id"]


def test_public_vote_requires_open_session_and_blocks_duplicates(client: TestClient) -> None:
    event_id, competition_id, participant_ids, voters = _create_competition(client)
    voter_id, token = voters[0]
    payload = {
        "method": "single_choice",
        "participant_id": participant_ids[0],
    }
    headers = {
        "X-Voter-Account-Id": voter_id,
        "X-Voter-Access-Token": token,
    }

    closed_response = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers=headers,
    )
    assert closed_response.status_code == 409

    voting_session_id = _open_voting(client, competition_id)
    created = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["voting_session_id"] == voting_session_id
    assert created.json()["votes"][0]["participant_id"] == participant_ids[0]

    logs = client.get(f"/api/events/{event_id}/audit-logs")
    assert logs.status_code == 200
    assert "public_vote_submitted" in [item["action"] for item in logs.json()]

    duplicate = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers=headers,
    )
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
    event_id, competition_id, participant_ids, voters = _create_competition(client, allow_vote_update=True)
    voter_id, token = voters[0]
    _open_voting(client, competition_id)
    headers = {
        "X-Voter-Account-Id": voter_id,
        "X-Voter-Access-Token": token,
    }

    first = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "method": "single_choice",
            "participant_id": participant_ids[0],
        },
        headers=headers,
    )
    assert first.status_code == 201

    updated = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "method": "single_choice",
            "participant_id": participant_ids[1],
        },
        headers=headers,
    )
    assert updated.status_code == 201

    summary = client.get(f"/api/competitions/{competition_id}/public-votes/summary")
    counts = {item["participant_id"]: item["vote_count"] for item in summary.json()["participants"]}
    assert summary.json()["total_votes"] == 1
    assert counts[participant_ids[0]] == 0
    assert counts[participant_ids[1]] == 1


def test_public_vote_supports_ranked_choice_and_criteria_rating(client: TestClient) -> None:
    ranked_event_id, ranked_competition_id, ranked_participant_ids, voters = _create_competition(
        client,
        method="ranked_choice",
        max_votes_per_user=3,
    )
    voter_id, token = voters[0]
    _open_voting(client, ranked_competition_id)
    headers = {
        "X-Voter-Account-Id": voter_id,
        "X-Voter-Access-Token": token,
    }

    ranked = client.post(
        f"/api/competitions/{ranked_competition_id}/public-votes",
        json={
            "method": "ranked_choice",
            "ranked_participant_ids": ranked_participant_ids,
        },
        headers=headers,
    )
    assert ranked.status_code == 201
    assert [vote["rank_position"] for vote in ranked.json()["votes"]] == [1, 2, 3]

    criteria_event_id, criteria_competition_id, criteria_participant_ids, voters_crit = _create_competition(
        client,
        method="criteria_rating",
        max_votes_per_user=2,
    )
    voter_id_crit, token_crit = voters_crit[0]
    headers_crit = {
        "X-Voter-Account-Id": voter_id_crit,
        "X-Voter-Access-Token": token_crit,
    }
    criterion_id = client.get(
        f"/api/competitions/{criteria_competition_id}/public-criteria"
    ).json()[0]["id"]
    _open_voting(client, criteria_competition_id)

    criteria = client.post(
        f"/api/competitions/{criteria_competition_id}/public-votes",
        json={
            "method": "criteria_rating",
            "ratings": [
                {
                    "participant_id": criteria_participant_ids[0],
                    "criteria": [{"criterion_id": criterion_id, "score": 8}],
                }
            ],
        },
        headers=headers_crit,
    )
    assert criteria.status_code == 201
    assert criteria.json()["votes"][0]["vote_method"] == "criteria_rating"


def test_public_vote_limits_per_competition(client: TestClient) -> None:
    event_id, competition_id, participant_ids, voters = _create_competition(
        client,
        allow_vote_update=True,
        max_votes_per_competition=2,
        voters_to_create=["Voter 1", "Voter 2"],
    )
    voter1_id, token1 = voters[0]
    voter2_id, token2 = voters[1]

    payload = {
        "method": "single_choice",
        "participant_id": participant_ids[0],
    }

    # Round 1
    session_1_id = _open_voting(client, competition_id)
    r1 = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers={"X-Voter-Account-Id": voter1_id, "X-Voter-Access-Token": token1},
    )
    assert r1.status_code == 201
    client.post(f"/api/competitions/{competition_id}/voting-sessions/close", json={})

    # Round 2
    session_2_id = _open_voting(client, competition_id)
    r2 = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers={"X-Voter-Account-Id": voter1_id, "X-Voter-Access-Token": token1},
    )
    assert r2.status_code == 201

    # voter-1 updates their vote in Round 2 (allowed since allow_vote_update is True and it's the same session)
    r2_update = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "method": "single_choice",
            "participant_id": participant_ids[1],
        },
        headers={"X-Voter-Account-Id": voter1_id, "X-Voter-Access-Token": token1},
    )
    assert r2_update.status_code == 201
    client.post(f"/api/competitions/{competition_id}/voting-sessions/close", json={})

    # Round 3
    _open_voting(client, competition_id)
    # voter-1 tries to vote in Round 3 (rejected because they already voted in session 1 and 2, exceeding limit of 2)
    r3_fail = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers={"X-Voter-Account-Id": voter1_id, "X-Voter-Access-Token": token1},
    )
    assert r3_fail.status_code == 409
    assert "voter has reached the maximum number of votes" in r3_fail.json()["detail"]

    # voter-2 votes in Round 3 (allowed since they only voted in 0 sessions so far)
    r3_success = client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json=payload,
        headers={"X-Voter-Account-Id": voter2_id, "X-Voter-Access-Token": token2},
    )
    assert r3_success.status_code == 201


def test_self_vote_blocked_single_choice(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "E2"}).json()["id"]
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "C2", "judge_voting_enabled": False},
    ).json()["id"]
    p_ids = [
        client.post(
            f"/api/competitions/{comp_id}/participants",
            json={"name": n.lower(), "display_name": n},
        ).json()["id"]
        for n in ["Anna", "Marco"]
    ]
    va_id, token = _create_voter_account(client, event_id)
    # Link va to Anna
    link_resp = client.post(
        f"/api/voter-accounts/{va_id}/link-participant",
        json={"participant_id": p_ids[0]},
    )
    assert link_resp.status_code == 200

    # Go live
    client.patch(f"/api/events/{event_id}", json={"status": "live"})
    _open_voting(client, comp_id)

    # Anna trying to vote for herself
    resp = client.post(
        f"/api/competitions/{comp_id}/public-votes",
        json={"method": "single_choice", "participant_id": p_ids[0]},
        headers={"X-Voter-Account-Id": va_id, "X-Voter-Access-Token": token},
    )
    assert resp.status_code == 409
    assert "self" in resp.json()["detail"].lower() or "themselves" in resp.json()["detail"].lower()


def test_non_self_vote_allowed(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "E3"}).json()["id"]
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "C3", "judge_voting_enabled": False},
    ).json()["id"]
    p_ids = [
        client.post(
            f"/api/competitions/{comp_id}/participants",
            json={"name": n.lower(), "display_name": n},
        ).json()["id"]
        for n in ["Anna", "Marco"]
    ]
    va_id, token = _create_voter_account(client, event_id)
    # Link to Anna
    client.post(
        f"/api/voter-accounts/{va_id}/link-participant",
        json={"participant_id": p_ids[0]},
    )
    client.patch(f"/api/events/{event_id}", json={"status": "live"})
    _open_voting(client, comp_id)

    # Anna voting for Marco — should succeed
    resp = client.post(
        f"/api/competitions/{comp_id}/public-votes",
        json={"method": "single_choice", "participant_id": p_ids[1]},
        headers={"X-Voter-Account-Id": va_id, "X-Voter-Access-Token": token},
    )
    assert resp.status_code == 201
