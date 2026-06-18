# Contest Voting Platform Roadmap

Questa roadmap guida lo sviluppo incrementale della webapp. Le regole di dominio e i
vincoli tecnici restano in `AGENTS.md`; questo documento definisce ordine, dipendenze e
criteri di completamento.

## Strategia

- Procedere milestone per milestone.
- Ogni milestone deve lasciare il progetto avviabile o testabile.
- Le route API non devono contenere logica business: usare service dedicati.
- Prima di aggiungere frontend complessi, stabilizzare dominio, API e scoring.
- Aggiornare questa roadmap quando cambiano priorita, scope o criteri di accettazione.

## Milestone 1 - Setup progetto

**Status:** completata il 2026-06-18. Test backend, build frontend e smoke test
Docker Compose passano.

**Obiettivo:** creare una base full-stack avviabile localmente.

**Include:**

- struttura `backend/` FastAPI;
- struttura `frontend/` React o Next.js;
- PostgreSQL in Docker Compose;
- Alembic configurato;
- health check backend;
- pagina frontend minima;
- README con istruzioni di avvio.

**Criterio di completamento:** `docker compose up` avvia database, backend e frontend;
backend espone `/health`; frontend mostra una pagina iniziale.

**Dipendenze:** nessuna.

## Milestone 2 - Database e modelli

**Status:** completata il 2026-06-18. Modelli SQLAlchemy, migrazione Alembic,
seed demo e test base passano.

**Obiettivo:** modellare il dominio principale.

**Include:**

- modelli per eventi, competizioni, partecipanti, giudici, criteri, votanti, sessioni,
  voti, snapshot risultati e screen state;
- migrazioni Alembic;
- seed demo;
- test base su vincoli e relazioni.

**Criterio di completamento:** da codice/test si possono creare evento, competizione,
partecipanti, giudici e criteri.

**Dipendenze:** Milestone 1.

## Milestone 3 - API admin base

**Status:** completata il 2026-06-18. API admin CRUD per eventi, competizioni,
partecipanti, criteri pubblici, criteri giudici, giudici e associazioni
giudici/competizioni verificate.

**Obiettivo:** permettere la configurazione completa di un contest via API.

**Include:**

- CRUD eventi;
- CRUD competizioni;
- CRUD partecipanti;
- CRUD criteri pubblici;
- CRUD criteri giudici;
- CRUD giudici;
- associazione giudici/competizioni.

**Criterio di completamento:** tramite API si configura una competizione completa.

**Dipendenze:** Milestone 2.

## Milestone 4 - Voting sessions

**Status:** completata il 2026-06-18. API e service per apertura, chiusura,
riapertura e storico `VotingSession` verificati da test backend.

**Obiettivo:** gestire apertura, chiusura e riapertura delle votazioni.

**Include:**

- apertura votazione;
- chiusura votazione;
- riapertura come nuova `VotingSession`;
- storico sessioni;
- blocco voti senza sessione aperta.

**Criterio di completamento:** una competizione puo essere aperta e chiusa piu volte; i
voti sono sempre associati alla sessione corretta.

**Dipendenze:** Milestone 3.

## Milestone 5 - Voto pubblico

**Status:** completata il 2026-06-18. API e service per voto pubblico
`single_choice`, `ranked_choice`, `criteria_rating`, token anonimo hashato,
duplicati e aggiornamento voto verificati da test backend mirati.

**Obiettivo:** permettere al pubblico di votare secondo il metodo configurato.

**Include:**

- `single_choice`;
- `ranked_choice`;
- `criteria_rating`;
- token votante anonimo;
- blocco duplicati quando `allow_vote_update` e false;
- aggiornamento voto quando `allow_vote_update` e true.

**Criterio di completamento:** il pubblico puo votare solo con votazione aperta e nel
rispetto della configurazione competizione.

**Dipendenze:** Milestone 4.

## Milestone 6 - Voto giudici

**Status:** completata il 2026-06-18. Accesso giudici, lista competizioni
assegnate, voto criteri, update finche la votazione e aperta e stato
completamento verificati da test backend mirati.

**Obiettivo:** permettere ai giudici assegnati di votare sui criteri configurati.

**Include:**

- accesso giudice tramite codice o link;
- lista competizioni assegnate;
- voto criteri per partecipante;
- aggiornamento voto finche la votazione e aperta;
- stato completamento.

**Criterio di completamento:** ogni giudice puo votare tutti i partecipanti di una
competizione sui criteri configurati.

**Dipendenze:** Milestone 4.

## Milestone 7 - Scoring service

**Status:** completata il 2026-06-18. Service ed endpoint risultati per scoring
pubblico, scoring giudici, combinazione pesata, normalizzazione 0-100,
ordinamento e dettaglio verificati da test backend mirati.

**Obiettivo:** calcolare classifiche e dettagli punteggio.

**Include:**

- punteggio pubblico `single_choice`;
- punteggio pubblico `ranked_choice`;
- punteggio pubblico `criteria_rating`;
- punteggio giudici;
- combinazione pesata pubblico/giudici;
- normalizzazione 0-100;
- ordinamento classifica e dettaglio.

**Criterio di completamento:** endpoint risultati restituisce una classifica corretta e
dettagliata per i metodi supportati.

**Dipendenze:** Milestone 5 e Milestone 6.

## Milestone 8 - Freeze risultati

**Obiettivo:** rendere immutabile il risultato finale.

**Include:**

- snapshot risultati;
- freeze finale;
- lettura risultati finali da snapshot.

**Criterio di completamento:** dopo il freeze, il risultato finale non cambia anche se
vengono modificati voti o dati collegati.

**Dipendenze:** Milestone 7.

## Milestone 9 - Frontend admin

**Obiettivo:** gestire una serata senza chiamare manualmente le API.

**Include:**

- dashboard eventi;
- dettaglio evento;
- configurazione competizioni;
- gestione partecipanti, criteri e giudici;
- apertura/chiusura votazione;
- risultati;
- freeze;
- controllo schermata pubblica.

**Criterio di completamento:** un admin puo configurare e condurre una serata dal browser.

**Dipendenze:** Milestone 3, 4, 7 e 8.

## Milestone 10 - Frontend pubblico

**Obiettivo:** permettere voto pubblico semplice da smartphone.

**Include:**

- accesso competizione;
- schermate voto per ogni metodo pubblico;
- conferma voto;
- stato votazione chiusa.

**Criterio di completamento:** un utente pubblico vota da mobile in pochi passaggi.

**Dipendenze:** Milestone 5.

## Milestone 11 - Frontend giudici

**Obiettivo:** fornire interfaccia voto dedicata ai giudici.

**Include:**

- accesso giudice;
- competizioni assegnate;
- voto criteri;
- salvataggio e aggiornamento;
- completamento.

**Criterio di completamento:** un giudice completa il voto per una competizione dal
browser.

**Dipendenze:** Milestone 6.

## Milestone 12 - Schermo pubblico e realtime

**Obiettivo:** controllare una vista proiettore aggiornata in tempo reale.

**Include:**

- `ScreenState`;
- WebSocket;
- vista schermo;
- controllo da admin;
- QR code;
- countdown;
- numero voti;
- classifica, podio e reveal.

**Criterio di completamento:** l'admin cambia modalita e lo schermo si aggiorna senza
refresh.

**Dipendenze:** Milestone 7, 8, 9 e 10.

## Milestone 13 - Rifinitura UI

**Obiettivo:** rendere l'app usabile e presentabile in evento reale.

**Include:**

- responsive mobile;
- admin chiaro e operativo;
- voto pubblico rapido;
- schermate giudici ordinate;
- schermo pubblico leggibile da lontano;
- animazioni classifica/podio;
- feedback errori e successo.

**Criterio di completamento:** i flussi principali sono comprensibili senza spiegazioni
esterne.

**Dipendenze:** Milestone 9, 10, 11 e 12.

## Milestone 14 - Test e robustezza

**Obiettivo:** consolidare comportamento e regressioni.

**Include:**

- test apertura/chiusura votazioni;
- voto duplicato;
- aggiornamento voto;
- voto giudici;
- calcolo risultati;
- freeze risultati;
- accesso con PIN;
- accesso giudici;
- gestione errori.

**Criterio di completamento:** i flussi critici hanno copertura automatizzata e messaggi
errore chiari.

**Dipendenze:** tutte le milestone funzionali precedenti.
