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
    public_vote_method: str = "single_choice",
    public_weight: float = 50,
    judge_weight: float = 50,
    max_votes_per_user: int = 1,
    judge_voting_enabled: bool = False,
    auto_live: bool = True,
) -> tuple[str, str, list[str]]:
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
    if auto_live:
        live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
        assert live_response.status_code == 200
        client.post(
            f"/api/competitions/{competition_id}/voting-sessions",
            json={"label": "Round 1"},
        )
    return event_id, competition_id, participant_ids


def test_results_combine_single_choice_public_votes_and_judge_votes(
    client: TestClient,
) -> None:
    event_id, competition_id, participant_ids = _create_competition(
        client,
        judge_voting_enabled=True,
        auto_live=False,
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

    for token, participant_id in [
        ("voter-1", participant_ids[0]),
        ("voter-2", participant_ids[0]),
        ("voter-3", participant_ids[1]),
    ]:
        client.post(
            f"/api/competitions/{competition_id}/public-votes",
            json={
                "voter_token": token,
                "method": "single_choice",
                "participant_id": participant_id,
            },
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
    _, competition_id, participant_ids = _create_competition(
        client,
        public_vote_method="ranked_choice",
        public_weight=100,
        judge_weight=0,
        max_votes_per_user=3,
    )
    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "ranked-1",
            "method": "ranked_choice",
            "ranked_participant_ids": participant_ids,
        },
    )

    response = client.get(f"/api/competitions/{competition_id}/results")

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["participant_id"] for item in results] == participant_ids
    assert [item["public_score"]["raw_score"] for item in results] == [3, 2, 1]
    assert [item["final_score"] for item in results] == [100, 66.6667, 33.3333]


def test_results_score_public_criteria_rating(client: TestClient) -> None:
    _, competition_id, participant_ids = _create_competition(
        client,
        public_vote_method="criteria_rating",
        public_weight=100,
        judge_weight=0,
    )
    criterion_id = client.get(
        f"/api/competitions/{competition_id}/public-criteria"
    ).json()[0]["id"]
    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "criteria-1",
            "method": "criteria_rating",
            "ratings": [
                {
                    "participant_id": participant_ids[0],
                    "criteria": [{"criterion_id": criterion_id, "score": 7}],
                }
            ],
        },
    )

    response = client.get(f"/api/competitions/{competition_id}/results")

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["participant_id"] == participant_ids[0]
    assert result["public_score"]["normalized_score"] == 70
    assert result["final_score"] == 70


def test_freeze_results_persists_final_snapshot(client: TestClient) -> None:
    _, competition_id, participant_ids = _create_competition(
        client,
        public_weight=100,
        judge_weight=0,
    )
    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "voter-1",
            "method": "single_choice",
            "participant_id": participant_ids[0],
        },
    )

    frozen = client.post(
        f"/api/competitions/{competition_id}/results/freeze",
        json={"snapshot_name": "Finale", "created_by_admin_id": "admin-1"},
    )

    assert frozen.status_code == 200
    frozen_results = frozen.json()["results_json"]["results"]
    assert frozen_results[0]["participant_id"] == participant_ids[0]
    assert frozen_results[0]["final_score"] == 100

    client.post(
        f"/api/competitions/{competition_id}/public-votes",
        json={
            "voter_token": "voter-2",
            "method": "single_choice",
            "participant_id": participant_ids[1],
        },
    )

    results = client.get(f"/api/competitions/{competition_id}/results")
    final = client.get(f"/api/competitions/{competition_id}/results/final")
    duplicate_freeze = client.post(
        f"/api/competitions/{competition_id}/results/freeze",
        json={"snapshot_name": "Finale 2"},
    )

    assert results.status_code == 200
    assert final.status_code == 200
    assert duplicate_freeze.status_code == 409
    assert results.json()["results"] == frozen.json()["results_json"]["results"]
    assert final.json()["results_json"]["results"] == frozen.json()["results_json"]["results"]
