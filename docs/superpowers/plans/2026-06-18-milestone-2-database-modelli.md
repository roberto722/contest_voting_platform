# Milestone 2 Database Modelli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the initial database domain model, Alembic migration and demo seed data.

**Architecture:** SQLAlchemy 2.0 models live in small files under `backend/app/models/`, all imported by `backend/app/models/__init__.py` for Alembic metadata discovery. Tests use SQLite in memory for model behavior and Docker/Postgres verifies migration execution.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, pytest, SQLite test engine, PostgreSQL Docker service.

---

## Tasks

### Task 1: Model Tests First

**Files:**

- Create: `backend/tests/test_models.py`
- Create: `backend/tests/test_seed.py`

Steps:

1. Write tests for core model relationships using an in-memory SQLite session.
2. Run `.\.venv\Scripts\pytest.exe backend/tests/test_models.py -v` and confirm import/model failures.
3. Write tests for `create_demo_data(session)`.
4. Run `.\.venv\Scripts\pytest.exe backend/tests/test_seed.py -v` and confirm seed import failure.

### Task 2: SQLAlchemy Models

**Files:**

- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/mixins.py`
- Create: `backend/app/models/event.py`
- Create: `backend/app/models/competition.py`
- Create: `backend/app/models/participant.py`
- Create: `backend/app/models/criteria.py`
- Create: `backend/app/models/judge.py`
- Create: `backend/app/models/voting.py`
- Create: `backend/app/models/vote.py`
- Create: `backend/app/models/result.py`
- Create: `backend/app/models/screen.py`
- Modify: `backend/app/models/__init__.py`

Steps:

1. Add enum definitions.
2. Add UUID/timestamp mixins.
3. Add each model with relationships and foreign keys.
4. Run model tests until green.
5. Commit models and tests.

### Task 3: Seed Demo

**Files:**

- Create: `backend/app/seed.py`

Steps:

1. Implement `create_demo_data(session)`.
2. Run seed tests until green.
3. Commit seed.

### Task 4: Alembic Migration

**Files:**

- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260618_0001_initial_schema.py`

Steps:

1. Import `app.models` in Alembic env.
2. Create the initial schema migration manually.
3. Start Docker Postgres.
4. Run `docker compose exec backend alembic upgrade head`.
5. Run `docker compose exec backend alembic current`.
6. Commit migration.

### Task 5: Final Verification

**Files:**

- Modify: `docs/ROADMAP.md`

Steps:

1. Run `.\.venv\Scripts\pytest.exe -v`.
2. Run `npm run build` in `frontend`.
3. Run Docker migration smoke test.
4. Mark Milestone 2 complete in roadmap.
5. Commit roadmap update.

## Self-Review

- Covers all Milestone 2 scope from `docs/ROADMAP.md`.
- Keeps API, scoring and auth out of scope.
- Uses TDD for model and seed behavior.
- Uses Docker/Postgres for Alembic verification.

