# Milestone 2 Database E Modelli Design

## Obiettivo

Implementare il primo schema dati del dominio Contest Voting Platform con SQLAlchemy 2.0,
una migrazione Alembic iniziale, seed demo e test automatici sulle relazioni principali.

## Scelte tecniche

- ORM: SQLAlchemy 2.0 puro con `Mapped[...]` e `mapped_column`.
- ID: stringhe UUID generate lato applicazione, compatibili con SQLite nei test e
  PostgreSQL in produzione.
- Timestamp: `created_at` e `updated_at` con default UTC lato Python.
- Enum: `StrEnum` Python salvati come `VARCHAR` tramite SQLAlchemy `Enum`.
- JSON: tipo SQLAlchemy `JSON` per snapshot risultati e payload schermo.
- Test: SQLite in memoria per test rapidi di modelli, relazioni e seed.
- Postgres: verificato tramite Docker Compose e migrazioni Alembic.

## Struttura modelli

I modelli vivono in file piccoli sotto `backend/app/models/`:

- `enums.py`: stati e metodi configurabili.
- `mixins.py`: ID UUID e timestamp.
- `event.py`: `Event`.
- `competition.py`: `Competition`.
- `participant.py`: `Participant`.
- `criteria.py`: `PublicVoteCriterion`, `JudgeCriterion`.
- `judge.py`: `Judge`, `CompetitionJudge`.
- `voting.py`: `VoterSession`, `VotingSession`.
- `vote.py`: `PublicVote`, `PublicCriterionVote`, `JudgeVote`, `JudgeCriterionVote`.
- `result.py`: `ResultSnapshot`.
- `screen.py`: `ScreenState`.

`backend/app/models/__init__.py` importa tutti i modelli, cosi Alembic vede
`Base.metadata` completo.

## Relazioni principali

- `Event` contiene molte `Competition`, molti `Judge`, molte `VoterSession` e uno o piu
  `ScreenState`.
- `Competition` appartiene a un `Event` e contiene partecipanti, criteri pubblici,
  criteri giudici, voting session, voti, snapshot e associazioni giudici.
- `Participant` appartiene a una `Competition`.
- `Judge` appartiene a un `Event` e viene assegnato a competizioni tramite
  `CompetitionJudge`.
- `VotingSession` appartiene a una `Competition`; ogni riapertura futura creera una nuova
  riga.
- I voti pubblici e giudici sono legati alla `VotingSession` per mantenere storico.
- `ResultSnapshot` conserva risultati JSON congelati.
- `ScreenState` conserva modalita e payload JSON dello schermo pubblico.

## Seed demo

`backend/app/seed.py` espone `create_demo_data(session)`. La funzione crea:

- evento `Serata Contest Demo`;
- competizione `Miglior Performance Musicale`;
- competizione `Miglior Costume`;
- partecipanti `Anna`, `Marco`, `Luca`, `Giulia` per entrambe;
- tre giudici demo;
- criteri giudici coerenti con le due competizioni.

I nomi demo possono essere specifici; i modelli restano generici.

## Migrazione

La migrazione Alembic iniziale crea tutte le tabelle della Milestone 2. Deve includere
chiavi esterne, indici minimi e vincoli unici essenziali:

- slug/codici non introdotti in questa milestone;
- associazione giudice/competizione unica per coppia;
- una `ScreenState` per coppia evento/competizione quando `competition_id` e valorizzato;
- voti criterio unici per voto/criterio.

## Test

I test devono verificare:

- creazione di evento, competizione, partecipante, giudice e criteri;
- navigazione delle relazioni principali;
- persistenza di voting session, voter session e voti;
- persistenza JSON per snapshot risultati e screen state;
- seed demo con conteggi attesi.

## Fuori scope

- API CRUD.
- servizi di voto/scoring.
- autenticazione.
- validazione Pydantic dettagliata.
- regole di apertura/chiusura votazione oltre alla struttura dati.

## Criterio di completamento

La milestone e completata quando:

- i test backend passano;
- Alembic genera/applica lo schema su Postgres via Docker Compose;
- il seed demo popola dati coerenti;
- la roadmap indica Milestone 2 completata.

