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
- Voto pubblico: http://localhost:5173/vote
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432

Un link diretto usa `http://localhost:5173/vote?eventId=<id>`; senza ID la pagina
mostra il form di accesso.

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

## Workflow admin MVP

Il setup operativo e:

1. crea evento, che parte in `draft`;
2. crea competizione, che resta `draft`;
3. configura partecipanti, criteri, giudici, pesi, metodo pubblico e accesso;
4. controlla `GET /api/competitions/{competition_id}/setup-status`;
5. porta l'evento a `live` solo quando tutte le competizioni sono complete;
6. apri/chiudi votazioni e controlla lo schermo;
7. calcola risultati e congela snapshot finale.

`ready` non e uno stato scelto liberamente dall'admin: il backend lo deriva da un setup
valido. Quando un evento diventa `live`, la configurazione viene bloccata; restano
abilitate gestione votazioni, schermo e risultati.

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

## Deploy VPS con Caddy

Il traffico arriva direttamente alla VPS:

```text
DNS A record -> VPS porte 80/443 -> Caddy -> frontend/backend
```

Prerequisiti VPS:

- Docker e Docker Compose installati.
- Record DNS `qsr.it.eu.org` e `api.qsr.it.eu.org` puntati all'IP pubblico della VPS.
- Porte `80` e `443` aperte sul firewall della VPS.

Preparare `.env` sul server:

```env
POSTGRES_DB=contest_voting
POSTGRES_USER=contest
POSTGRES_PASSWORD=usa_una_password_forte
DATABASE_URL=postgresql+psycopg://contest:usa_una_password_forte@postgres:5432/contest_voting
FRONTEND_DOMAIN=qsr.it.eu.org
BACKEND_DOMAIN=api.qsr.it.eu.org
VITE_API_BASE_URL=https://api.qsr.it.eu.org
BACKEND_CORS_ORIGINS=https://qsr.it.eu.org
```

Avvio VPS:

```bash
docker compose -f docker-compose.vps.yml up -d --build
```

Log:

```bash
docker compose -f docker-compose.vps.yml logs -f caddy backend frontend
```

Stop:

```bash
docker compose -f docker-compose.vps.yml down
```

Caddy richiede e rinnova automaticamente i certificati HTTPS Let's Encrypt per i due domini.
## Fallback locale/LAN

1. Verificare che app e database siano attivi:

```bash
docker compose ps
```

2. Dal server aprire:

```text
http://localhost:5173
```

3. Da un altro dispositivo nella stessa rete Wi-Fi, trovare l'IP locale del server.
   Su Windows:

```bash
ipconfig
```

Cercare `IPv4 Address`, per esempio:

```text
192.168.1.50
```

4. Aprire da smartphone/tablet/PC nella stessa rete:

```text
http://192.168.1.50:5173
```

La porta puo essere diversa se il progetto viene configurato con una porta diversa
da `5173`. Il backend resta disponibile dal server su `http://localhost:8000`.

## Checklist pre-evento

- I record DNS `qsr.it.eu.org` e `api.qsr.it.eu.org` puntano alla VPS.
- Le porte `80` e `443` sono aperte sul firewall della VPS.
- `.env` contiene password Postgres forte e URL HTTPS corretti.
- `docker compose -f docker-compose.vps.yml ps` mostra `caddy`, `frontend`, `backend` e `postgres` attivi.
- `https://qsr.it.eu.org` apre il frontend.
- `https://api.qsr.it.eu.org/health` risponde dal backend.
- I log Caddy non mostrano errori di emissione certificati.
- I codici voto/giudici usati per test non sono committati nel repository.
