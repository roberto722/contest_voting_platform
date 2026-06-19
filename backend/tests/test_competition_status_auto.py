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

def test_competition_status_auto_updates(client: TestClient) -> None:
    # 1. Crea evento
    event_response = client.post("/api/events", json={"name": "Event"})
    event_id = event_response.json()["id"]
    assert event_response.json()["status"] == "draft"

    # 2. Crea competizione (giudici disabilitati per semplicità)
    comp_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Comp", "judge_voting_enabled": False}
    )
    comp_id = comp_response.json()["id"]
    assert comp_response.json()["status"] == "draft"

    # 3. Un solo partecipante non basta per READY
    client.post(
        f"/api/competitions/{comp_id}/participants",
        json={"name": "p1", "display_name": "P1"}
    )
    comp_response = client.get(f"/api/events/{event_id}/competitions")
    assert comp_response.json()[0]["status"] == "draft"

    # 4. Due partecipanti attivi completano il setup pubblico
    client.post(
        f"/api/competitions/{comp_id}/participants",
        json={"name": "p2", "display_name": "P2"}
    )
    comp_response = client.get(f"/api/events/{event_id}/competitions")
    assert comp_response.json()[0]["status"] == "ready"

    # 5. Apertura sessione richiede evento live
    draft_open = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Round 1"},
    )
    assert draft_open.status_code == 409
    assert "event_not_live" in draft_open.json()["issues"]

    client.patch(f"/api/events/{event_id}", json={"status": "live"})
    client.post(f"/api/competitions/{comp_id}/voting-sessions", json={"label": "Round 1"})
    comp_response = client.get(f"/api/events/{event_id}/competitions")
    assert comp_response.json()[0]["status"] == "voting_open"

    # 6. Chiudi sessione -> torna a VOTING_CLOSED
    client.post(f"/api/competitions/{comp_id}/voting-sessions/close", json={})
    comp_response = client.get(f"/api/events/{event_id}/competitions")
    assert comp_response.json()[0]["status"] == "voting_closed"

def test_competition_status_with_judges(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Event"}).json()["id"]
    
    # Competizione con giudici abilitati
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Comp", "judge_voting_enabled": True}
    ).json()["id"]
    
    # 1. Aggiungi partecipanti (ancora DRAFT perché mancano giudici e criteri)
    client.post(
        f"/api/competitions/{comp_id}/participants",
        json={"name": "p1", "display_name": "P1"},
    )
    client.post(
        f"/api/competitions/{comp_id}/participants",
        json={"name": "p2", "display_name": "P2"},
    )
    assert client.get(f"/api/events/{event_id}/competitions").json()[0]["status"] == "draft"
    
    # 2. Aggiungi criterio giudice
    client.post(f"/api/competitions/{comp_id}/judge-criteria", json={"name": "C1"})
    assert client.get(f"/api/events/{event_id}/competitions").json()[0]["status"] == "draft"
    
    # 3. Crea e assegna giudice -> READY
    judge_id = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "j1", "display_name": "J1", "access_code": "123"},
    ).json()["id"]
    client.post(f"/api/competitions/{comp_id}/judges/{judge_id}")
    assert client.get(f"/api/events/{event_id}/competitions").json()[0]["status"] == "ready"

    # 4. Rimuovi assegnazione giudice -> DRAFT
    client.delete(f"/api/competitions/{comp_id}/judges/{judge_id}")
    assert client.get(f"/api/events/{event_id}/competitions").json()[0]["status"] == "draft"

def test_competition_cannot_go_live_if_not_ready(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Event"}).json()["id"]
    comp_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Comp", "judge_voting_enabled": False}
    ).json()["id"]
    
    # 1. Nessun partecipante -> DRAFT
    assert client.get(f"/api/events/{event_id}/competitions").json()[0]["status"] == "draft"
    
    # 2. Tenta apertura sessione -> 409 Conflict
    response = client.post(
        f"/api/competitions/{comp_id}/voting-sessions",
        json={"label": "Round 1"},
    )
    assert response.status_code == 409
    assert "missing_active_participants" in response.json()["issues"]
