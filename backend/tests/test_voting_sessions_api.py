from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
from app.models import Competition, CompetitionStatus, VotingSession, VotingSessionStatus
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


def _create_competition(client: TestClient) -> str:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]
    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Contest generico", "judge_voting_enabled": False},
    )
    competition_id = competition_response.json()["id"]

    for index in range(1, 3):
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": f"P{index}", "display_name": f"Partecipante {index}"},
        )
    live_response = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_response.status_code == 200
    return competition_id


def test_admin_can_open_close_and_reopen_voting_sessions(
    client: TestClient,
    db_session: Session,
) -> None:
    competition_id = _create_competition(client)

    first_open = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1", "opened_by_admin_id": "admin-1"},
    )
    assert first_open.status_code == 201
    first_session = first_open.json()
    assert first_session["status"] == "open"
    assert first_session["closed_at"] is None

    duplicate_open = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round duplicate"},
    )
    assert duplicate_open.status_code == 409

    closed = client.post(
        f"/api/competitions/{competition_id}/voting-sessions/close",
        json={"closed_by_admin_id": "admin-1"},
    )
    assert closed.status_code == 200
    assert closed.json()["id"] == first_session["id"]
    assert closed.json()["status"] == "closed"
    assert closed.json()["closed_at"] is not None

    reopened = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 2"},
    )
    assert reopened.status_code == 201
    assert reopened.json()["id"] != first_session["id"]
    assert reopened.json()["status"] == "open"

    sessions = client.get(f"/api/competitions/{competition_id}/voting-sessions")
    assert sessions.status_code == 200
    assert [session["label"] for session in sessions.json()] == ["Round 2", "Round 1"]

    competition = db_session.get(Competition, competition_id)
    saved_sessions = db_session.scalars(
        select(VotingSession).where(VotingSession.competition_id == competition_id)
    ).all()

    assert competition is not None
    assert competition.status is CompetitionStatus.VOTING_OPEN
    assert len(saved_sessions) == 2
    assert {session.status for session in saved_sessions} == {
        VotingSessionStatus.OPEN,
        VotingSessionStatus.CLOSED,
    }


def test_close_requires_an_open_voting_session(client: TestClient) -> None:
    competition_id = _create_competition(client)

    response = client.post(
        f"/api/competitions/{competition_id}/voting-sessions/close",
        json={},
    )

    assert response.status_code == 409


def test_admin_can_open_and_close_public_and_judge_channels_separately(
    client: TestClient,
) -> None:
    event_id = client.post("/api/events", json={"name": "Channel event"}).json()["id"]
    comp = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Channel competition",
            "public_voting_enabled": True,
            "judge_voting_enabled": True,
        },
    ).json()
    competition_id = comp["id"]

    for index in range(1, 3):
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": f"P{index}", "display_name": f"P{index}"},
        )
    client.post(
        f"/api/competitions/{competition_id}/judge-criteria",
        json={"name": "Tecnica"},
    )
    judge = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge", "display_name": "Judge", "access_code": "secret"},
    ).json()
    client.post(f"/api/competitions/{competition_id}/judges/{judge['id']}")
    assert client.patch(f"/api/events/{event_id}", json={"status": "live"}).status_code == 200

    public_open = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Round 1", "channels": ["public"]},
    )
    assert public_open.status_code == 201
    session = public_open.json()
    assert session["status"] == "open"
    assert session["public_voting_open"] is True
    assert session["judge_voting_open"] is False

    judge_open = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"channels": ["judge"]},
    )
    assert judge_open.status_code == 201
    assert judge_open.json()["id"] == session["id"]
    assert judge_open.json()["public_voting_open"] is True
    assert judge_open.json()["judge_voting_open"] is True

    public_closed = client.post(
        f"/api/competitions/{competition_id}/voting-sessions/close",
        json={"channels": ["public"]},
    )
    assert public_closed.status_code == 200
    assert public_closed.json()["status"] == "open"
    assert public_closed.json()["public_voting_open"] is False
    assert public_closed.json()["judge_voting_open"] is True

    judge_closed = client.post(
        f"/api/competitions/{competition_id}/voting-sessions/close",
        json={"channels": ["judge"]},
    )
    assert judge_closed.status_code == 200
    assert judge_closed.json()["status"] == "closed"
    assert judge_closed.json()["public_voting_open"] is False
    assert judge_closed.json()["judge_voting_open"] is False


def test_final_competition_cannot_be_reopened(client: TestClient, db_session: Session) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]
    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Finale"},
    )
    competition_id = competition_response.json()["id"]
    
    # Impostiamo manualmente lo stato nel database
    from app.models import Competition, CompetitionStatus
    comp = db_session.get(Competition, competition_id)
    comp.status = CompetitionStatus.REVEALED
    db_session.commit()

    response = client.post(
        f"/api/competitions/{competition_id}/voting-sessions",
        json={"label": "Riapertura"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "competition results are final"


def test_competition_cannot_open_if_not_ready(client: TestClient) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]

    # 1. Senza partecipanti
    comp_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "No participants", "judge_voting_enabled": False},
    )
    comp_id = comp_response.json()["id"]

    response = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Fail"},
    )
    assert response.status_code == 409
    assert "missing_active_participants" in response.json()["issues"]

    # 2. Con partecipanti ma senza giudici (quando richiesti)
    comp_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "No judges", "judge_voting_enabled": True},
    )
    comp_id = comp_response.json()["id"]
    for index in range(1, 3):
        client.post(
            f"/api/competitions/{comp_id}/participants",
            json={"name": f"P{index}", "display_name": f"P{index}"},
        )

    response = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Fail"},
    )
    assert response.status_code == 409
    assert "missing_assigned_judges" in response.json()["issues"]
    assert "missing_judge_criteria" in response.json()["issues"]

    # 3. Con partecipanti, giudici e criteri, ma senza criteri pubblici (se criteria_rating)
    comp_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "No public criteria",
            "judge_voting_enabled": False,
            "public_voting_enabled": True,
            "public_vote_method": "criteria_rating",
        },
    )
    comp_id = comp_response.json()["id"]
    for index in range(1, 3):
        client.post(
            f"/api/competitions/{comp_id}/participants",
            json={"name": f"P{index}", "display_name": f"P{index}"},
        )

    response = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Fail"},
    )
    assert response.status_code == 409
    assert "missing_public_criteria" in response.json()["issues"]


def test_competition_opens_only_after_complete_setup_and_live_event(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Completa", "judge_voting_enabled": False},
    ).json()["id"]
    for index in range(1, 3):
        client.post(
            f"/api/competitions/{comp_id}/participants",
            json={"name": f"p{index}", "display_name": f"P{index}"},
        )

    draft_open = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Round draft"},
    )
    assert draft_open.status_code == 409
    assert "event_not_live" in draft_open.json()["issues"]

    live = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    opened = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Round live"},
    )

    assert live.status_code == 200
    assert opened.status_code == 201
