from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    Competition,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVote,
    PublicVoteCriterion,
    ScreenState,
    VoterAccount,
    VotingSession,
)
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
            "public_weight": 60,
            "judge_weight": 40,
        },
    )
    assert competition_response.status_code == 201
    competition = competition_response.json()
    competition_id = competition["id"]

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

    logs_response = client.get(f"/api/events/{event_id}/audit-logs")
    assert logs_response.status_code == 200
    actions = [item["action"] for item in logs_response.json()]
    assert "admin_event_created" in actions
    assert "admin_competition_created" in actions
    assert "admin_judge_created" in actions
    assert "admin_judge_assigned" in actions

    participants_response = client.get(f"/api/competitions/{competition_id}/participants")
    judges_response = client.get(f"/api/events/{event_id}/judges")
    competitions_response = client.get(f"/api/events/{event_id}/competitions")

    assert len(participants_response.json()) == 2
    assert len(judges_response.json()) == 1
    assert judges_response.json()[0]["assigned_competition_ids"] == [competition_id]
    assert len(competitions_response.json()) == 1

    saved_competition = db_session.scalar(
        select(Competition).where(Competition.id == competition_id)
    )
    saved_judge = db_session.scalar(select(Judge).where(Judge.id == judge_id))

    assert saved_competition is not None
    assert saved_judge is not None
    assert saved_judge.access_code_hash != "secret"


def test_admin_can_regenerate_judge_access_code(client: TestClient, db_session: Session) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]
    judge_response = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "old-secret"},
    )
    judge_id = judge_response.json()["id"]

    old_access = client.post(
        "/api/judge-access",
        json={"judge_id": judge_id, "access_code": "old-secret"},
    )
    assert old_access.status_code == 200

    reset_response = client.post(f"/api/judges/{judge_id}/access-code/regenerate")
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    new_access_code = reset_payload["access_code"]
    assert new_access_code
    assert new_access_code != "old-secret"
    assert reset_payload["judge"]["id"] == judge_id
    assert "access_code_hash" not in reset_payload["judge"]

    old_access_after_reset = client.post(
        "/api/judge-access",
        json={"judge_id": judge_id, "access_code": "old-secret"},
    )
    assert old_access_after_reset.status_code == 403

    new_access = client.post(
        "/api/judge-access",
        json={"judge_id": judge_id, "access_code": new_access_code},
    )
    assert new_access.status_code == 200

    judges_response = client.get(f"/api/events/{event_id}/judges")
    assert judges_response.status_code == 200
    assert "access_code" not in judges_response.json()[0]
    assert "access_code_hash" not in judges_response.json()[0]

    saved_judge = db_session.scalar(select(Judge).where(Judge.id == judge_id))
    assert saved_judge is not None
    assert saved_judge.access_code_hash != "old-secret"
    assert saved_judge.access_code_hash != new_access_code

    logs_response = client.get(f"/api/events/{event_id}/audit-logs")
    actions = [item["action"] for item in logs_response.json()]
    assert "admin_judge_access_code_regenerated" in actions


def test_admin_can_assign_judge_to_multiple_competitions(client: TestClient) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]
    first_competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Prima competizione", "public_vote_method": "single_choice"},
    )
    second_competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Seconda competizione", "public_vote_method": "single_choice"},
    )
    first_competition_id = first_competition_response.json()["id"]
    second_competition_id = second_competition_response.json()["id"]
    judge_response = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    )
    judge_id = judge_response.json()["id"]

    first_assignment = client.post(f"/api/competitions/{first_competition_id}/judges/{judge_id}")
    second_assignment = client.post(f"/api/competitions/{second_competition_id}/judges/{judge_id}")

    assert first_assignment.status_code == 201
    assert second_assignment.status_code == 201

    judges_response = client.get(f"/api/events/{event_id}/judges")
    assigned_competition_ids = judges_response.json()[0]["assigned_competition_ids"]
    assert set(assigned_competition_ids) == {first_competition_id, second_competition_id}

    judge_access_response = client.post(
        "/api/judge-access",
        json={"judge_id": judge_id, "access_code": "secret"},
    )
    accessible_competition_ids = {
        competition["id"] for competition in judge_access_response.json()["competitions"]
    }
    assert accessible_competition_ids == {first_competition_id, second_competition_id}


def test_live_event_locks_configuration_changes(client: TestClient) -> None:
    event_id = client.post("/api/events", json={"name": "Serata Live"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Contest", "judge_voting_enabled": False},
    ).json()["id"]
    for index, name in enumerate(["Anna", "Marco"], start=1):
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name, "order_index": index},
        )

    live = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    participant = client.post(
        f"/api/competitions/{competition_id}/participants",
        json={"name": "luca", "display_name": "Luca"},
    )
    criterion = client.post(
        f"/api/competitions/{competition_id}/public-criteria",
        json={"name": "Impatto"},
    )
    judge = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    )

    assert live.status_code == 200
    assert participant.status_code == 409
    assert criterion.status_code == 409
    assert judge.status_code == 409


def test_delete_event_removes_all_associated_data(
    client: TestClient,
    db_session: Session,
) -> None:
    event_id = client.post("/api/events", json={"name": "Evento da eliminare"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest",
            "judge_voting_enabled": False,
            "public_weight": 100,
            "judge_weight": 0,
        },
    ).json()["id"]
    participant_ids = [
        client.post(
            f"/api/competitions/{competition_id}/participants",
            json={"name": name.lower(), "display_name": name, "order_index": index},
        ).json()["id"]
        for index, name in enumerate(["Anna", "Marco"], start=1)
    ]
    judge_id = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-1", "display_name": "Giudice 1", "access_code": "secret"},
    ).json()["id"]
    criterion_id = client.post(
        f"/api/competitions/{competition_id}/judge-criteria",
        json={"name": "Tecnica"},
    ).json()["id"]

    voter_account_resp = client.post(
        f"/api/events/{event_id}/voter-accounts",
        json={"display_name": "Votante da eliminare"}
    )
    assert voter_account_resp.status_code == 201
    va_data = voter_account_resp.json()
    va_id = va_data["voter_account"]["id"]
    va_token = va_data["voter_account"]["access_token"]

    assert client.patch(f"/api/events/{event_id}", json={"status": "live"}).status_code == 200
    assert (
        client.post(
            f"/api/competitions/{competition_id}/voting-sessions",
            json={"label": "Round 1"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/competitions/{competition_id}/public-votes",
            json={
                "method": "single_choice",
                "participant_id": participant_ids[0],
            },
            headers={
                "X-Voter-Account-Id": va_id,
                "X-Voter-Access-Token": va_token,
            }
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"/api/events/{event_id}/screen-state",
            json={
                "competition_id": competition_id,
                "mode": "show_podium",
                "payload_json": {"title": "Podio"},
            },
        ).status_code
        == 200
    )

    deleted = client.delete(f"/api/events/{event_id}")

    assert deleted.status_code == 204
    assert client.get(f"/api/events/{event_id}").status_code == 404
    assert db_session.scalar(select(Competition).where(Competition.id == competition_id)) is None
    assert db_session.scalar(select(Judge).where(Judge.id == judge_id)) is None
    assert (
        db_session.scalar(select(JudgeCriterion).where(JudgeCriterion.id == criterion_id))
        is None
    )
    assert db_session.scalars(select(Participant)).all() == []
    assert db_session.scalars(select(PublicVote)).all() == []
    assert db_session.scalars(select(VoterAccount)).all() == []
    assert db_session.scalars(select(VotingSession)).all() == []
    assert db_session.scalars(select(ScreenState)).all() == []
    assert db_session.scalars(select(AuditLog).where(AuditLog.event_id == event_id)).all() == []


def test_delete_competition_removes_only_competition_associated_data(
    client: TestClient,
    db_session: Session,
) -> None:
    event_id = client.post("/api/events", json={"name": "Evento"}).json()["id"]
    competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest da eliminare",
            "judge_voting_enabled": False,
            "public_weight": 100,
            "judge_weight": 0,
        },
    ).json()["id"]
    survivor_competition_id = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest che resta",
            "judge_voting_enabled": False,
            "public_weight": 100,
            "judge_weight": 0,
        },
    ).json()["id"]
    participant_id = client.post(
        f"/api/competitions/{competition_id}/participants",
        json={"name": "anna", "display_name": "Anna", "order_index": 1},
    ).json()["id"]
    criterion_id = client.post(
        f"/api/competitions/{competition_id}/public-criteria",
        json={"name": "Gradimento"},
    ).json()["id"]
    deleted = client.delete(f"/api/competitions/{competition_id}")

    assert deleted.status_code == 204
    assert db_session.scalar(select(Competition).where(Competition.id == competition_id)) is None
    assert (
        db_session.scalar(select(Competition).where(Competition.id == survivor_competition_id))
        is not None
    )
    assert db_session.scalar(select(Participant).where(Participant.id == participant_id)) is None
    assert (
        db_session.scalar(select(PublicVoteCriterion).where(PublicVoteCriterion.id == criterion_id))
        is None
    )
    assert db_session.scalars(select(PublicVote)).all() == []
    assert db_session.scalars(select(VoterAccount)).all() == []
    assert db_session.scalars(select(VotingSession)).all() == []
    assert (
        db_session.scalars(select(AuditLog).where(AuditLog.competition_id == competition_id)).all()
        == []
    )
    assert client.get(f"/api/events/{event_id}").status_code == 200


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


def test_cannot_assign_judge_when_judge_voting_disabled(
    client: TestClient,
    db_session: Session,
) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]

    # Create competition with judge_voting_enabled=False
    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Contest senza giudici",
            "judge_voting_enabled": False,
        },
    )
    competition_id = competition_response.json()["id"]

    # Create judge
    judge_response = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "judge-no-vote", "display_name": "Giudice 1", "access_code": "secret"},
    )
    judge_id = judge_response.json()["id"]

    # Attempt assignment -> should return 409
    assignment_response = client.post(f"/api/competitions/{competition_id}/judges/{judge_id}")
    assert assignment_response.status_code == 409
    assert "judge voting is disabled" in assignment_response.json()["detail"]


def test_judge_actions_during_live_and_draft(
    client: TestClient,
    db_session: Session,
) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live"})
    event_id = event_response.json()["id"]

    # Create competition with default setup (so it is ready)
    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={"name": "Contest", "judge_voting_enabled": False},
    )
    competition_id = competition_response.json()["id"]
    client.post(
        f"/api/competitions/{competition_id}/participants",
        json={"name": "anna", "display_name": "Anna"},
    )
    client.post(
        f"/api/competitions/{competition_id}/participants",
        json={"name": "marco", "display_name": "Marco"},
    )

    # Create judges
    j1 = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "j-1", "display_name": "Giudice 1", "access_code": "secret-1"},
    ).json()
    j2 = client.post(
        f"/api/events/{event_id}/judges",
        json={"name": "j-2", "display_name": "Giudice 2", "access_code": "secret-2"},
    ).json()

    # Before live (draft): both deleting and regenerating are allowed
    # Delete judge 2
    del_res = client.delete(f"/api/judges/{j2['id']}")
    assert del_res.status_code == 204

    # Go live
    live_res = client.patch(f"/api/events/{event_id}", json={"status": "live"})
    assert live_res.status_code == 200

    # During live: deleting judge 1 is NOT allowed (returns 409)
    del_live_res = client.delete(f"/api/judges/{j1['id']}")
    assert del_live_res.status_code == 409
    assert "event configuration is locked" in del_live_res.json()["detail"]

    # During live: regenerating access code for judge 1 IS allowed (returns 200)
    regen_res = client.post(f"/api/judges/{j1['id']}/access-code/regenerate")
    assert regen_res.status_code == 200
    assert regen_res.json()["access_code"] is not None


def test_seed_competition_fake_data(client: TestClient, db_session: Session) -> None:
    event_response = client.post("/api/events", json={"name": "Serata Live Demo"})
    assert event_response.status_code == 201
    event_id = event_response.json()["id"]

    competition_response = client.post(
        f"/api/events/{event_id}/competitions",
        json={
            "name": "Miglior Performance Musicale",
            "public_voting_enabled": True,
            "judge_voting_enabled": True,
            "public_vote_method": "criteria_rating",
            "public_weight": 50,
            "judge_weight": 50,
        },
    )
    assert competition_response.status_code == 201
    competition_id = competition_response.json()["id"]

    # Seed fake data with custom quantities
    seed_res = client.post(
        f"/api/competitions/{competition_id}/seed-fake-data",
        json={"num_participants": 6, "num_judges": 4, "num_criteria": 2},
    )
    assert seed_res.status_code == 204

    # Verify participants (should be 6 and contain first and last name)
    parts_res = client.get(f"/api/competitions/{competition_id}/participants")
    assert parts_res.status_code == 200
    participants = parts_res.json()
    assert len(participants) == 6
    # Let's verify they have both first and last name
    for part in participants:
        assert " " in part["display_name"]

    # Verify judge criteria (should be 2)
    jc_res = client.get(f"/api/competitions/{competition_id}/judge-criteria")
    assert jc_res.status_code == 200
    assert len(jc_res.json()) == 2

    # Verify public criteria (should be 2)
    pc_res = client.get(f"/api/competitions/{competition_id}/public-criteria")
    assert pc_res.status_code == 200
    assert len(pc_res.json()) == 2

    # Verify judges (should be 4)
    judges_res = client.get(f"/api/events/{event_id}/judges")
    assert judges_res.status_code == 200
    assert len(judges_res.json()) == 4

    # Verify seeding again fails (409 Conflict)
    seed_again_res = client.post(
        f"/api/competitions/{competition_id}/seed-fake-data",
        json={},
    )
    assert seed_again_res.status_code == 409
    assert "già dati" in seed_again_res.json()["detail"]

