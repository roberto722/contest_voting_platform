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
    public_vote_method: str = "single_choice",
    public_weight: float = 50,
    judge_weight: float = 50,
    max_votes_per_user: int = 1,
    judge_voting_enabled: bool = False,
    auto_live: bool = True,
    num_voters: int = 1,
) -> tuple[str, str, list[str], list[tuple[str, str]]]:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest",
            "public_vote_method": public_vote_method,
            "public_weight": public_weight,
            "judge_weight": judge_weight,
            "max_votes_per_user": max_votes_per_user,
            "judge_voting_enabled": judge_voting_enabled,
        },
    ).json()["id"]
    participant_ids = [
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name, "order_index": index},
        ).json()["id"]
        for index, name in enumerate(["Anna", "Marco", "Luca"], start=1)
    ]
    if public_vote_method == "criteria_rating":
        client.post(
            f"/api/competitions/{competition_id}/public-criteria",
            json={"name": "Impatto", "min_score": 0, "max_score": 10},
        )

    voters = []
    for idx in range(num_voters):
        voters.append(_create_voter_account(client, event_id, name=f"Voter {idx + 1}"))

    if auto_live:
        live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
        assert live_response.status_code == 200
        client.post(
            f"/api/competitions/{competition_id}/voting-sessions",
            json={"label": "Round 1"},
        )
    return event_id, competition_id, participant_ids, voters


def test_results_combine_single_choice_public_votes_and_judge_votes(
    client: TestClient,
) -> None:
    event_id, competition_id, participant_ids, voters = _create_competition(
        client,
        judge_voting_enabled=True,
        auto_live=False,
        num_voters=3,
    )
    judge_id = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    ).json()["id"]
    client.post(f"/api/competitions/{competition_id}/judges/{judge_id}")
    criterion_id = client.post(
        f"/api/competitions/{competition_id}/judge-criteria",
        json={"name": "Tecnica", "min_score": 0, "max_score": 10},
    ).json()["id"]
    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    client.post(f"/api/competitions/{competition_id}/voting-sessions", json={"label": "Round 1"})

    vote_data = [
        (voters[0], participant_ids[0]),
        (voters[1], participant_ids[0]),
        (voters[2], participant_ids[1]),
    ]
    for (v_id, token), participant_id in vote_data:
        client.post(
            f"/api/competitions/{competition_id}/public-votes",
            json={
                "method": "single_choice",
                "participant_id": participant_id,
            },
            headers={
                "X-Voter-Account-Id": v_id,
                "X-Voter-Access-Token": token,
            }
        )

    for participant_id, score in [(participant_ids[0], 10), (participant_ids[1], 0)]:
        client.post(
            f"/api/competitions/{competition_id}/judge-votes",
            json={
                "judge_id": judge_id,
                "access_code": "secret",
                "participant_id": participant_id,
                "criteria": [{"criterion_id": criterion_id, "score": score}],
            },
        )

    response = client.get(f"/api/competitions/{competition_id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["participant_id"] == participant_ids[0]
    assert results[0]["final_score"] == 100
    assert results[1]["participant_id"] == participant_ids[1]
    assert results[1]["final_score"] == 25


def test_results_score_ranked_choice(client: TestClient) -> None:
    _, competition_id, participant_ids, voters = _create_competition(
        client,
        public_vote_method="ranked_choice",
        public_weight=100,
        judge_weight=0,
        max_votes_per_user=3,
        num_voters=1,
    )
    voter_id, token = voters[0]
    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "method": "ranked_choice",
            "ranked_participant_ids": participant_ids,
        },
        headers={
            "X-Voter-Account-Id": voter_id,
            "X-Voter-Access-Token": token,
        }
    )

    response = client.get(f"/api/competitions/{competition_id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["participant_id"] for item in results] == participant_ids
    assert [item["public_score"]["raw_score"] for item in results] == [3, 2, 1]
    assert [item["final_score"] for item in results] == [100, 66.6667, 33.3333]


def test_results_score_public_criteria_rating(client: TestClient) -> None:
    _, competition_id, participant_ids, voters = _create_competition(
        client,
        public_vote_method="criteria_rating",
        public_weight=100,
        judge_weight=0,
        num_voters=1,
    )
    voter_id, token = voters[0]
    criterion_id = client.get(
        f"/api/competitions/{competition_id}/public-criteria"
    ).json()[0]["id"]
    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "method": "criteria_rating",
            "ratings": [
                {
                    "participant_id": participant_ids[0],
                    "criteria": [{"criterion_id": criterion_id, "score": 7}],
                }
            ],
        },
        headers={
            "X-Voter-Account-Id": voter_id,
            "X-Voter-Access-Token": token,
        }
    )

    response = client.get(f"/api/competitions/{competition_id}/results")

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["participant_id"] == participant_ids[0]
    assert result["public_score"]["normalized_score"] == 70
    assert result["final_score"] == 70

