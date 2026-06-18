# Milestone 1 Setup Progetto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the initial full-stack project skeleton so `docker compose up` starts PostgreSQL, FastAPI and a frontend app.

**Architecture:** Keep backend and frontend separated under `backend/` and `frontend/`. The backend exposes a minimal FastAPI app with `/health` and Alembic wired to the same settings module. The frontend starts as a minimal Vite React app that can later grow into admin, public voting, judge and screen areas.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic Settings, pytest, PostgreSQL, Docker Compose, Node 22, Vite, React, TypeScript.

---

## Current State

The project currently contains:

- `main.py`: PyCharm sample script, not part of the target app.
- `pyproject.toml`: minimal root Python project metadata.
- `AGENTS.md`: product and engineering instructions.
- `docs/ROADMAP.md`: milestone roadmap.

The workspace may not be a Git repository yet. If `git status` fails with "not a git repository", initialize Git before following commit steps.

## File Structure

Create or modify these files:

- Modify: `pyproject.toml` for backend dev tooling from the root workspace.
- Modify: `main.py` into a compatibility launcher that points to `backend.app.main:app`.
- Create: `.gitignore` for Python, Node, env files and local databases.
- Create: `.env.example` with local development defaults.
- Create: `docker-compose.yml` with `postgres`, `backend`, and `frontend`.
- Create: `README.md` with local setup and verification commands.
- Create: `backend/Dockerfile`.
- Create: `backend/pyproject.toml`.
- Create: `backend/alembic.ini`.
- Create: `backend/app/__init__.py`.
- Create: `backend/app/main.py`.
- Create: `backend/app/config.py`.
- Create: `backend/app/db.py`.
- Create: `backend/app/api/__init__.py`.
- Create: `backend/app/api/routes/__init__.py`.
- Create: `backend/app/api/routes/health.py`.
- Create: `backend/app/models/__init__.py`.
- Create: `backend/app/schemas/__init__.py`.
- Create: `backend/app/services/__init__.py`.
- Create: `backend/app/websocket/__init__.py`.
- Create: `backend/alembic/env.py`.
- Create: `backend/alembic/script.py.mako`.
- Create: `backend/alembic/versions/.gitkeep`.
- Create: `backend/tests/test_health.py`.
- Create: `frontend/Dockerfile`.
- Create: `frontend/package.json`.
- Create: `frontend/package-lock.json` by running `npm install`.
- Create: `frontend/index.html`.
- Create: `frontend/tsconfig.json`.
- Create: `frontend/tsconfig.node.json`.
- Create: `frontend/vite.config.ts`.
- Create: `frontend/src/main.tsx`.
- Create: `frontend/src/App.tsx`.
- Create: `frontend/src/styles.css`.

## Task 0: Repository Baseline

**Files:**

- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Check whether Git is initialized**

Run:

```bash
git status --short
```

Expected if Git already exists: command succeeds.

Expected if Git is missing: command fails with `fatal: not a git repository`.

- [ ] **Step 2: Initialize Git if needed**

Run only if the previous step failed:

```bash
git init
```

Expected: repository initialized in the current project directory.

- [ ] **Step 3: Create `.gitignore`**

Create `.gitignore` with:

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
venv/

# Node
node_modules/
dist/
coverage/

# Environment
.env
.env.*
!.env.example

# Local data
*.sqlite3
*.db
postgres-data/

# IDE
.idea/
.vscode/
```

- [ ] **Step 4: Create `.env.example`**

Create `.env.example` with:

```dotenv
POSTGRES_DB=contest_voting
POSTGRES_USER=contest
POSTGRES_PASSWORD=contest
DATABASE_URL=postgresql+psycopg://contest:contest@postgres:5432/contest_voting
BACKEND_CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 5: Commit baseline**

Run:

```bash
git add .gitignore .env.example AGENTS.md docs/ROADMAP.md docs/superpowers/plans/2026-06-18-milestone-1-setup-progetto.md
git commit -m "docs: add project roadmap and milestone 1 plan"
```

Expected: commit succeeds.

## Task 1: Backend Project Skeleton

**Files:**

- Modify: `pyproject.toml`
- Modify: `main.py`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/websocket/__init__.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Replace root `pyproject.toml`**

Set `pyproject.toml` to:

```toml
[project]
name = "contest-voting-platform"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
pythonpath = ["backend"]
testpaths = ["backend/tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Replace root `main.py`**

Set `main.py` to:

```python
"""Compatibility launcher for local FastAPI development.

The production application lives in backend/app/main.py.
"""

from pathlib import Path
import sys

backend_path = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app

__all__ = ["app"]
```

- [ ] **Step 3: Create backend package directories**

Create the backend directories:

```bash
mkdir -p backend/app/api/routes backend/app/models backend/app/schemas backend/app/services backend/app/websocket backend/tests
```

On PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path backend/app/api/routes,backend/app/models,backend/app/schemas,backend/app/services,backend/app/websocket,backend/tests
```

- [ ] **Step 4: Create backend marker files**

Create these files with empty content:

```text
backend/app/__init__.py
backend/app/api/__init__.py
backend/app/api/routes/__init__.py
backend/app/models/__init__.py
backend/app/schemas/__init__.py
backend/app/services/__init__.py
backend/app/websocket/__init__.py
```

- [ ] **Step 5: Create `backend/pyproject.toml`**

Create `backend/pyproject.toml` with:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "contest-voting-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.13.0",
  "fastapi[standard]>=0.115.0",
  "psycopg[binary]>=3.2.0",
  "pydantic-settings>=2.6.0",
  "sqlalchemy>=2.0.0",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27.0",
  "pytest>=8.3.0",
  "ruff>=0.7.0",
]

[tool.setuptools.packages.find]
include = ["app*"]
```

- [ ] **Step 6: Create backend settings**

Create `backend/app/config.py` with:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Contest Voting Platform"
    database_url: str = Field(
        default="postgresql+psycopg://contest:contest@localhost:5432/contest_voting",
        validation_alias="DATABASE_URL",
    )
    backend_cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 7: Create database module**

Create `backend/app/db.py` with:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 8: Create health route**

Create `backend/app/api/routes/health.py` with:

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 9: Create FastAPI app**

Create `backend/app/main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    origins = [origin.strip() for origin in settings.backend_cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 10: Write health test**

Create `backend/tests/test_health.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 11: Install backend dependencies**

Run from the repository root:

```bash
python -m pip install -e "backend[dev]"
```

Expected: dependencies install successfully.

- [ ] **Step 12: Run backend test**

Run:

```bash
pytest backend/tests/test_health.py -v
```

Expected: `1 passed`.

- [ ] **Step 13: Commit backend skeleton**

Run:

```bash
git add pyproject.toml main.py backend
git commit -m "feat: add FastAPI backend skeleton"
```

Expected: commit succeeds.

## Task 2: Alembic Setup

**Files:**

- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

- [ ] **Step 1: Create Alembic directories**

Run:

```bash
mkdir -p backend/alembic/versions
```

On PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path backend/alembic/versions
```

- [ ] **Step 2: Create `backend/alembic.ini`**

Create `backend/alembic.ini` with:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+psycopg://contest:contest@localhost:5432/contest_voting

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create Alembic env**

Create `backend/alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create Alembic template**

Create `backend/alembic/script.py.mako` with:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Create versions marker**

Create `backend/alembic/versions/.gitkeep` with empty content.

- [ ] **Step 6: Verify Alembic sees metadata**

Run from `backend/`:

```bash
alembic current
```

Expected with no database running: either connects if Postgres is available, or fails only with a connection error. It must not fail with Python import errors.

- [ ] **Step 7: Commit Alembic setup**

Run:

```bash
git add backend/alembic.ini backend/alembic
git commit -m "feat: configure Alembic"
```

Expected: commit succeeds.

## Task 3: Docker Compose and Backend Container

**Files:**

- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create backend Dockerfile**

Create `backend/Dockerfile` with:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e ".[dev]"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create Docker Compose**

Create `docker-compose.yml` with:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: contest_voting
      POSTGRES_USER: contest
      POSTGRES_PASSWORD: contest
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U contest -d contest_voting"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg://contest:contest@postgres:5432/contest_voting
      BACKEND_CORS_ORIGINS: http://localhost:5173
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app
      - ./backend/alembic:/app/alembic
      - ./backend/alembic.ini:/app/alembic.ini
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/index.html:/app/index.html
      - ./frontend/vite.config.ts:/app/vite.config.ts
    depends_on:
      - backend

volumes:
  postgres-data:
```

- [ ] **Step 3: Build backend image after frontend files exist**

Do not run this task yet if Task 4 is incomplete, because `docker-compose.yml` also references `frontend/`.

Run after Task 4:

```bash
docker compose build backend
```

Expected: backend image builds successfully.

- [ ] **Step 4: Commit Docker backend setup**

Run after Task 4 verification:

```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat: add Docker Compose backend services"
```

Expected: commit succeeds.

## Task 4: Frontend Skeleton

**Files:**

- Create: `frontend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`

- [ ] **Step 1: Create frontend directories**

Run:

```bash
mkdir -p frontend/src
```

On PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path frontend/src
```

- [ ] **Step 2: Create `frontend/package.json`**

Create `frontend/package.json` with:

```json
{
  "name": "contest-voting-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc && vite build",
    "preview": "vite preview --host 0.0.0.0"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.1",
    "typescript": "^5.6.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1"
  }
}
```

- [ ] **Step 3: Install frontend dependencies**

Run from `frontend/`:

```bash
npm install
```

Expected: `package-lock.json` is created and dependencies install successfully.

- [ ] **Step 4: Create `frontend/index.html`**

Create `frontend/index.html` with:

```html
<!doctype html>
<html lang="it">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Contest Voting Platform</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create TypeScript configs**

Create `frontend/tsconfig.json` with:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `frontend/tsconfig.node.json` with:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Create Vite config**

Create `frontend/vite.config.ts` with:

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
```

- [ ] **Step 7: Create React entrypoint**

Create `frontend/src/main.tsx` with:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 8: Create initial app**

Create `frontend/src/App.tsx` with:

```typescript
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Contest Voting Platform</p>
        <h1>Console eventi live</h1>
        <p>
          Base frontend pronta. Le prossime milestone aggiungeranno admin, voto pubblico,
          giudici e schermo pubblico.
        </p>
        <a href={`${apiBaseUrl}/health`}>Verifica backend</a>
      </section>
    </main>
  );
}
```

- [ ] **Step 9: Create initial styles**

Create `frontend/src/styles.css` with:

```css
:root {
  color: #18212f;
  background: #f6f7fb;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
}

a {
  color: #0d6efd;
  font-weight: 700;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
}

.intro {
  width: min(720px, 100%);
}

.eyebrow {
  margin: 0 0 12px;
  color: #58667a;
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 16px;
  font-size: clamp(2rem, 7vw, 4rem);
  line-height: 1;
}

p {
  max-width: 58ch;
  font-size: 1.1rem;
  line-height: 1.6;
}
```

- [ ] **Step 10: Create frontend Dockerfile**

Create `frontend/Dockerfile` with:

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY index.html ./index.html
COPY tsconfig.json ./tsconfig.json
COPY tsconfig.node.json ./tsconfig.node.json
COPY vite.config.ts ./vite.config.ts
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev"]
```

- [ ] **Step 11: Verify frontend build**

Run from `frontend/`:

```bash
npm run build
```

Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 12: Commit frontend skeleton**

Run:

```bash
git add frontend
git commit -m "feat: add Vite frontend skeleton"
```

Expected: commit succeeds.

## Task 5: Full Docker Verification

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Build all containers**

Run:

```bash
docker compose build
```

Expected: `postgres`, `backend`, and `frontend` services build or pull successfully.

- [ ] **Step 2: Start services**

Run:

```bash
docker compose up
```

Expected:

- Postgres becomes healthy.
- Backend listens on `http://localhost:8000`.
- Frontend listens on `http://localhost:5173`.

- [ ] **Step 3: Verify backend health**

In another terminal, run:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

- [ ] **Step 4: Verify frontend**

Open:

```text
http://localhost:5173
```

Expected: page shows "Console eventi live" and a link to verify backend.

- [ ] **Step 5: Stop services**

Run:

```bash
docker compose down
```

Expected: containers stop cleanly and named volume remains.

## Task 6: README

**Files:**

- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md` with:

````markdown
# Contest Voting Platform

Webapp full-stack per gestire contest live con votazione pubblica, voto giudici,
risultati, freeze finale e schermata pubblica controllata dall'admin.

## Stack

- Backend: FastAPI
- Database: PostgreSQL
- ORM/migrazioni: SQLAlchemy + Alembic
- Frontend: React + Vite
- Ambiente locale: Docker Compose

## Avvio locale

```bash
docker compose up
```

Servizi:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432

## Sviluppo backend

```bash
python -m pip install -e "backend[dev]"
pytest
```

Avvio diretto:

```bash
cd backend
fastapi dev app/main.py
```

## Sviluppo frontend

```bash
cd frontend
npm install
npm run dev
```

## Migrazioni

```bash
cd backend
alembic current
```

Le migrazioni applicative verranno aggiunte dalla milestone database e modelli.

## Documentazione progetto

- `AGENTS.md`: regole operative e vincoli di dominio.
- `docs/ROADMAP.md`: milestone e criteri di completamento.
- `docs/superpowers/plans/`: piani di implementazione.
````

- [ ] **Step 2: Commit README and compose verification**

Run:

```bash
git add README.md docker-compose.yml backend/Dockerfile frontend/Dockerfile
git commit -m "docs: add local development instructions"
```

Expected: commit succeeds.

## Task 7: Final Milestone 1 Verification

**Files:**

- No new files.

- [ ] **Step 1: Run backend tests**

Run:

```bash
pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes.

- [ ] **Step 3: Run Docker Compose smoke test**

Run:

```bash
docker compose up --build
```

Expected:

- Postgres healthy.
- Backend available at `http://localhost:8000/health`.
- Frontend available at `http://localhost:5173`.

- [ ] **Step 4: Stop Docker Compose**

Run:

```bash
docker compose down
```

Expected: containers stop cleanly.

- [ ] **Step 5: Record completion**

Update `docs/ROADMAP.md` by appending this line under "Milestone 1 - Setup progetto":

```markdown
**Status:** completata quando test backend, build frontend e smoke test Docker Compose passano.
```

- [ ] **Step 6: Commit final verification note**

Run:

```bash
git add docs/ROADMAP.md
git commit -m "docs: record milestone 1 completion criteria"
```

Expected: commit succeeds.

## Self-Review

- Spec coverage: Milestone 1 setup, Docker Compose, backend, frontend, Postgres, Alembic
  and README are covered.
- No implementation of domain models, auth, voting, scoring or realtime is included; those
  belong to later milestones.
- No placeholders remain in executable tasks.
- Type names are consistent: `Settings`, `Base`, `create_app`, `app`, and `/health`.
- The plan assumes network access for Python, Node and Docker dependency downloads during
  execution.
