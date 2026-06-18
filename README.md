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
