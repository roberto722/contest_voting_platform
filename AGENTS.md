# Contest Voting Platform - Istruzioni progetto

Questo file e la fonte operativa aggiornata per gli agenti che lavorano sul progetto.
Deriva dal documento iniziale `Piano di sviluppo webapp contest live.pdf` e va mantenuto
allineato quando cambiano requisiti, scelte architetturali o milestone.

## Come aggiornare queste istruzioni

- Aggiorna questo file prima o insieme a modifiche che cambiano requisiti, architettura,
  dominio o ordine di sviluppo.
- Se una richiesta utente contraddice questo file, segui la richiesta utente e poi proponi
  o applica l'aggiornamento di questo file.
- Mantieni le regole come vincoli verificabili, non come note generiche.
- Quando implementi una milestone, aggiungi test coerenti con il rischio introdotto.

## Obiettivo prodotto

Costruire una webapp full-stack per gestire contest live durante eventi o serate.
Il sistema deve essere generico e configurabile: non deve essere hardcoded per contest
musicali, costumi o altri casi specifici.

La webapp deve permettere di:

- creare eventi;
- creare piu competizioni dentro un evento;
- configurare partecipanti, giudici, criteri, pesi e metodi di voto;
- aprire, chiudere e riaprire votazioni durante la serata;
- raccogliere voti pubblici tramite link/QR code e voti dei giudici;
- calcolare risultati provvisori e finali;
- congelare risultati finali;
- controllare una schermata pubblica per proiettore o schermo grande.

## Stack richiesto

- Backend: FastAPI.
- Database principale: PostgreSQL.
- ORM: SQLAlchemy oppure SQLModel.
- Migrazioni: Alembic.
- Validazione API: Pydantic.
- Realtime: WebSocket FastAPI.
- Frontend: React oppure Next.js.
- Ambiente locale: Docker Compose con backend, frontend e Postgres.

Lo spreadsheet non deve essere usato come database principale. Eventuali import/export
CSV o Excel sono funzionalita future.

## Architettura attesa

Mantieni separata la logica business dalle route API. Le route devono orchestrare input,
validazione e risposta; le decisioni di dominio devono stare nei service.

Struttura consigliata:

- `backend/app/api/routes/`
  - `events.py`
  - `competitions.py`
  - `participants.py`
  - `public_votes.py`
  - `judge_votes.py`
  - `results.py`
  - `screen.py`
  - `auth.py`
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
  - `scoring_service.py`
  - `voting_service.py`
  - `access_service.py`
  - `screen_service.py`
  - `auth_service.py`
- `backend/app/websocket/`
- `backend/app/db.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/alembic/`
- `backend/tests/`
- `frontend/src/pages/` o `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/services/`
- `frontend/src/hooks/`
- `frontend/src/styles/`
- `docker-compose.yml`
- `README.md`

## Entita di dominio

Implementa il dominio intorno a queste entita principali:

- `Event`: evento contenitore con stato `draft`, `live`, `closed`, `archived`.
- `Competition`: competizione dentro un evento, con metodi di voto, accesso, pesi,
  stato e flag di configurazione.
- `Participant`: partecipante ordinabile e attivabile.
- `PublicVoteCriterion`: criteri per voto pubblico a punteggio, quando usati.
- `JudgeCriterion`: criteri configurabili per i giudici.
- `Judge`: giudice con accesso personale tramite codice o link.
- `CompetitionJudge`: associazione tra giudici e competizioni.
- `VoterSession`: votante pubblico anonimo identificato tramite token/hash.
- `VotingSession`: singola apertura di voto per una competizione.
- `PublicVote`: voto pubblico collegato a competition, participant, voting session e
  voter session.
- `PublicCriterionVote`: dettaglio criterio per voto pubblico criteria rating.
- `JudgeVote`: voto di un giudice per un partecipante.
- `JudgeCriterionVote`: dettaglio criterio del voto giudice.
- `ResultSnapshot`: snapshot dei risultati congelati.
- `ScreenState`: stato della schermata pubblica.

## Stati e metodi supportati

Metodi voto pubblico minimi:

- `single_choice`
- `ranked_choice`
- `criteria_rating`

Predisporre estensione futura per:

- `multiple_choice`
- `rating`

Metodi accesso minimi:

- `public_link`
- `qr_pin`
- `private_link`

Predisporre estensione futura per:

- `one_time_code`
- `invite_list`

Stati competizione:

- `draft`
- `ready`
- `voting_open`
- `voting_closed`
- `results_frozen`
- `revealed`

Stati voting session:

- `open`
- `closed`
- `cancelled`

Ogni riapertura della votazione deve creare una nuova `VotingSession`.

## Regole business non negoziabili

- Non hardcodare contest musicali, costumi o altri tipi specifici nella logica.
- Le competizioni devono restare generiche e configurabili.
- Non mettere scoring, accesso o regole di voto direttamente nelle route.
- Non permettere voti se non esiste una `VotingSession` aperta.
- Non permettere voti quando la votazione e chiusa.
- Se `allow_vote_update` e false, impedire il voto duplicato dello stesso votante nella
  stessa sessione.
- Se `allow_vote_update` e true, permettere aggiornamento voto secondo metodo configurato.
- Non modificare i risultati finali dopo il freeze.
- Dopo il freeze, leggere i risultati finali da `ResultSnapshot`.
- Non mostrare automaticamente la classifica live durante la votazione, salvo comando
  esplicito dell'admin.
- Hashare PIN, access code, token, IP e user agent quando vengono salvati per accesso o
  identificazione votante.
- Il pubblico non richiede login; usa token anonimo lato client salvato in localStorage o
  cookie e hash lato database.

## Service principali

`VotingService` deve gestire:

- apertura votazione;
- chiusura votazione;
- creazione nuove voting session;
- verifica votabilita competizione;
- verifica se un utente puo votare;
- modifica voto quando consentita;
- blocco voti a votazione chiusa.

`AccessService` deve gestire:

- accesso pubblico;
- validazione PIN competizione;
- generazione e verifica token votante anonimo;
- accesso giudici tramite codice o link;
- hashing dei dati sensibili.

`ScoringService` deve gestire:

- punteggio pubblico;
- punteggio giudici;
- normalizzazione su scala 0-100;
- peso pubblico/giudici;
- classifica finale;
- dettaglio punteggi;
- snapshot finale.

Formula generale:

```text
final_score =
  public_score * public_weight_normalized +
  judge_score * judge_weight_normalized

public_weight_normalized = public_weight / (public_weight + judge_weight)
judge_weight_normalized = judge_weight / (public_weight + judge_weight)
```

Se una componente e disabilitata o ha peso zero, ignorarla nel calcolo.

`ScreenService` deve gestire:

- stato schermo pubblico;
- lettura stato corrente;
- notifica via WebSocket;
- cambio modalita da pannello admin.

## Scoring

Single choice:

- Conta i voti ricevuti da ogni partecipante.
- Normalizza rispetto al massimo.

Ranked choice:

- Usa una mappa punti configurabile in futuro.
- Default iniziale ammesso: primo posto 3 punti, secondo 2, terzo 1.
- Somma i punti per partecipante e normalizza.

Criteria rating pubblico:

- Per ogni partecipante calcola la media pesata dei criteri.
- Poi calcola la media tra i votanti.

Voto giudici:

- Per ogni giudice e partecipante calcola la media pesata dei criteri.
- Poi calcola la media tra i giudici.

## API minime

Implementa endpoint per:

- CRUD eventi.
- CRUD competizioni dentro eventi.
- CRUD partecipanti.
- CRUD criteri pubblici.
- CRUD criteri giudici.
- CRUD giudici.
- associazione giudici/competizioni.
- apertura, chiusura e lista voting session.
- voto pubblico e summary voti pubblici.
- voto giudici e stato completamento.
- risultati, freeze risultati, risultati finali.
- stato schermo pubblico.
- WebSocket schermo pubblico.
- WebSocket admin/evento.

## Frontend

Implementa quattro aree principali.

Area admin:

- dashboard eventi;
- dettaglio evento;
- lista e configurazione competizioni;
- gestione partecipanti;
- gestione criteri pubblici e giudici;
- gestione giudici;
- apertura, chiusura e riapertura votazioni;
- vista risultati;
- freeze risultati;
- controllo schermata pubblica.

Area pubblico:

- accesso competizione;
- voto `single_choice`;
- voto `ranked_choice`;
- voto `criteria_rating`;
- pagina conferma;
- messaggio chiaro quando la votazione e chiusa.

Area giudici:

- accesso giudice;
- lista competizioni assegnate;
- voto criteri per partecipante;
- salvataggio e aggiornamento voti finche la votazione e aperta;
- stato completamento.

Area schermo pubblico:

- vista per proiettore/schermo grande;
- QR code grande;
- stato votazione;
- countdown;
- numero voti;
- classifica con barre animate;
- reveal progressivo;
- podio finale.

La schermata pubblica deve essere leggibile da lontano e controllata dall'admin.

## Realtime

Usa WebSocket per:

- aggiornare schermata pubblica;
- aggiornare numero voti ricevuti;
- notificare apertura e chiusura votazione;
- aggiornare stato giudici;
- cambiare modalita schermo da pannello admin.

Quando l'admin modifica `ScreenState`, il backend deve notificare i client collegati allo
schermo.

## Autenticazione MVP

Admin:

- login semplice email/password;
- anche un solo admin iniziale va bene per MVP.

Giudici:

- accesso tramite codice personale o link personale.

Pubblico:

- accesso secondo metodo configurato nella competizione;
- nessun login pubblico.

## Milestone

Procedi in modo incrementale.

1. Setup progetto: backend, frontend, Docker Compose, Postgres, FastAPI, Alembic,
   frontend, README con avvio. Completato quando `docker compose up` avvia backend,
   frontend e database.
2. Database e modelli: modelli principali, migrazioni, seed demo, test base.
3. API admin base: CRUD eventi, competizioni, partecipanti, criteri, giudici e
   associazioni.
4. Voting sessions: apertura, chiusura, riapertura come nuova sessione, storico e blocco
   voti senza sessione aperta.
5. Voto pubblico: `single_choice`, `ranked_choice`, `criteria_rating`, duplicati e
   aggiornamento voto.
6. Voto giudici: accesso giudici, competizioni assegnate, voto criteri e completamento.
7. Scoring service: calcoli pubblici, giudici, combinazione pesata, normalizzazione,
   classifica e dettagli.
8. Freeze risultati: snapshot finale immutabile.
9. Frontend admin: gestione completa serata senza usare direttamente le API.
10. Frontend pubblico: voto da smartphone semplice.
11. Frontend giudici: voto completo dei partecipanti.
12. Schermo pubblico e realtime: screen state, WebSocket, QR, countdown, risultati,
    podio e reveal.
13. Rifinitura UI: responsive, admin semplice, voto veloce, giudici ordinati, schermo
    scenografico, feedback errori/successo.
14. Test e robustezza: coprire votazioni, duplicati, aggiornamenti, voto giudici,
    scoring, freeze, accessi e gestione errori.

## Seed demo

Prepara seed data con:

- evento `Serata Contest Demo`;
- competizione `Miglior Performance Musicale`;
- competizione `Miglior Costume`;
- partecipanti `Anna`, `Marco`, `Luca`, `Giulia`;
- tre giudici demo;
- criteri giudici demo coerenti con le competizioni.

I dati demo possono essere specifici; la logica applicativa no.

## Output finale atteso

La webapp deve essere avviabile localmente con:

```bash
docker compose up
```

Deve permettere end-to-end:

- login admin;
- creazione/configurazione evento e competizioni;
- apertura votazione;
- voto pubblico;
- voto giudice;
- chiusura votazione;
- calcolo risultati;
- freeze risultati;
- classifica e podio su schermo pubblico;
- controllo schermo da pannello admin.

