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

Un link diretto usa `http://localhost:5173/vote?competitionId=<id>`; senza ID la pagina
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

## Deploy live con Cloudflare Tunnel

Cloudflare Tunnel serve solo per rendere l'app accessibile da internet senza aprire
porte sul router/server. Cloudflared e opzionale: l'app funziona anche senza
Cloudflare in locale o LAN, e webapp, backend e database non dipendono dal tunnel.

Avvio normale, senza Cloudflare:

```bash
docker compose up -d
```

Avvio con Cloudflare:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

Verifica configurazione:

```bash
docker compose config
```

Log del tunnel:

```bash
docker compose logs -f cloudflared
```

Stop del solo tunnel:

```bash
docker compose stop cloudflared
```

Se il tunnel cade, i voti continuano a essere salvati finche frontend, backend e
database sono attivi. Se Cloudflare o internet non funzionano, usare il fallback
locale/LAN.

## Configurazione Cloudflare

1. Creare o usare un account Cloudflare.
2. Avere un dominio gestito da Cloudflare.
3. Aprire Cloudflare Dashboard / Zero Trust.
4. Andare in Tunnels / Cloudflare Tunnels.
5. Creare un nuovo tunnel.
6. Scegliere `cloudflared` come connector.
7. Copiare il token generato da Cloudflare.
8. Inserire il token nel file `.env` locale, senza committarlo:

```env
CLOUDFLARE_TUNNEL_TOKEN=...
```

9. Configurare un Public Hostname / Published Application.

Per questo progetto il servizio web Docker e il frontend:

```text
Hostname pubblico:
vota.example.com

Service interno:
http://frontend:5173
```

Non usare `localhost` nel pannello Cloudflare quando il tunnel gira in Docker.
Usare il nome del servizio Docker interno, per esempio `http://frontend:5173`.
Non puntare Cloudflare al database.

Se il frontend pubblico deve chiamare il backend da internet, configurare anche una
URL pubblica per il backend, per esempio `https://api-vota.example.com`, verso:

```text
http://backend:8000
```

Poi impostare nel `.env` locale:

```env
VITE_API_BASE_URL=https://api-vota.example.com
BACKEND_CORS_ORIGINS=https://vota.example.com
```

## Fallback locale/LAN

1. Se Cloudflare non funziona, verificare che app e database siano attivi:

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

- `docker compose config` non da errori.
- `docker compose up -d` avvia frontend, backend e database.
- L'app funziona da localhost.
- L'app funziona da IP locale LAN.
- Il file `.env` contiene `CLOUDFLARE_TUNNEL_TOKEN` solo in locale.
- Il repository non contiene token reali.
- Cloudflared parte correttamente.
- Il dominio pubblico apre l'app.
- Fermando cloudflared, l'app continua a funzionare da localhost/LAN.
- Il database non espone porte pubbliche inutili.
- Il servizio cloudflared punta al servizio web, non al database.
