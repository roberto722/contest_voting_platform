from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
from app.models import Competition, Judge
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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


def test_admin_can_configure_complete_competition(client: TestClient, db_session: Session) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    assert event_response.status_code == 201
    event_id = event_response.json()["id"]

    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest generico",
            "public_vote_method": "single_choice",
            "access_method": "qr_pin",
            "access_pin": "1234",
            "public_weight": 60,
            "judge_weight": 40,
        },
    )
    assert competition_response.status_code == 201
    competition = competition_response.json()
    competition_id = competition["id"]
    assert "access_pin" not in competition
    assert "access_pin_hash" not in competition

    for name in ["Anna", "Marco"]:
        response = client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name},
        )
        assert response.status_code == 201

    public_criterion_response = client.post(
        f"/api/competitions/{competition_id}/public-criteria",
        json={"name": "Impatto", "min_score": 1, "max_score": 10, "weight": 1},
    )
    assert public_criterion_response.status_code == 201

    judge_criterion_response = client.post(
        f"/api/competitions/{competition_id}/judge-criteria",
        json={"name": "Tecnica", "min_score": 1, "max_score": 10, "weight": 2},
    )
    assert judge_criterion_response.status_code == 201

    judge_response = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    )
    assert judge_response.status_code == 201
    judge_id = judge_response.json()["id"]
    assert "access_code" not in judge_response.json()
    assert "access_code_hash" not in judge_response.json()

    assignment_response = client.post(f"/api/competitions/{competition_id}/judges/{judge_id}")
    assert assignment_response.status_code == 201

    participants_response = client.get(f"/api/competitions/{competition_id}/participants")
    judges_response = client.get(f"/api/events/{event_id}/judges")
    competitions_response = client.get(f"/api/events/{event_id}/competitions")

    assert len(participants_response.json()) == 2
    assert len(judges_response.json()) == 1
    assert len(competitions_response.json()) == 1

    saved_competition = db_session.scalar(
        select(Competition).where(Competition.id == competition_id)
    )
    saved_judge = db_session.scalar(select(Judge).where(Judge.id == judge_id))

    assert saved_competition is not None
    assert saved_competition.access_pin_hash != "1234"
    assert saved_judge is not None
    assert saved_judge.access_code_hash != "secret"


def test_admin_can_patch_delete_and_get_404(client: TestClient) -> None:
    created = client.post("/api/events", json={"name": "Bozza"})
    event_id = created.json()["id"]

    patched = client.patch(f"/api/events/{event_id}", json={"name": "Evento aggiornato"})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Evento aggiornato"

    deleted = client.delete(f"/api/events/{event_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/events/{event_id}")
    assert missing.status_code == 404
