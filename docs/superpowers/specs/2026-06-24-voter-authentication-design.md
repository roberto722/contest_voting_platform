# Voter Authentication & Self-Vote Prevention — Design Spec

**Data:** 2026-06-24  
**Status:** Approvato

---

## Obiettivo

Introdurre un sistema di autenticazione univoca per tutti i votanti pubblici, sostituendo il meccanismo anonimo (VoterSession + token localStorage). Ogni votante riceve un codice personale e/o un link personale dall'admin. I partecipanti alle competizioni vengono collegati al loro account votante; il sistema impedisce il voto su se stessi all'interno di ogni competizione.

---

## Requisiti

- Tutti i votanti pubblici devono essere autenticati: nessun accesso anonimo.
- Ogni votante ha un `VoterAccount` a livello di evento, con codice alfanumerico e link personale.
- Un partecipante può essere collegato a un `VoterAccount` tramite FK opzionale `voter_account_id` su `Participant`.
- Un `VoterAccount` può essere collegato a più partecipanti in competizioni diverse dello stesso evento.
- Un partecipante-votante non può votare per se stesso in nessuna competizione.
- Il frontend disabilita/nasconde il partecipante dal proprio ballot; il backend lo blocca a livello di servizio.
- I codici non vengono mai esposti dopo la creazione/rigenerazione (solo hash nel DB).
- I link personali usano un `access_token` UUID (non hashato) nell'URL.
- Il pattern di autenticazione segue quello dei giudici: token opaco verificato sul DB ad ogni request.

---

## Entità di dominio

### `VoterAccount` (nuova)

Tabella: `voter_accounts`

| Campo | Tipo | Note |
|---|---|---|
| `id` | UUID (string) | PK |
| `event_id` | FK → events | CASCADE DELETE |
| `display_name` | String(255) | Nome/etichetta per l'admin |
| `notes` | String(1000) | Note opzionali |
| `access_code_hash` | String(255) | Hash SHA-256 del codice alfanumerico |
| `access_token` | String(36) | UUID non hashato per link personale |
| `active` | Boolean | Default true |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | |

Relazioni:
- `event` → `Event`
- `participants` → `list[Participant]` (backref)
- `public_votes` → `list[PublicVote]` (backref)

### Modifiche a `Participant`

Aggiungere campo:

| Campo | Tipo | Note |
|---|---|---|
| `voter_account_id` | FK → voter_accounts, nullable | Se None, il partecipante non vota |

Relazione: `voter_account` → `VoterAccount`

### Modifiche a `PublicVote`

- Rimuovere `voter_session_id`
- Aggiungere `voter_account_id` (FK → voter_accounts, CASCADE DELETE)

### Rimozione di `VoterSession`

`VoterSession` viene eliminata. I dati demo vengono riseedati. Non ci sono dati di produzione da migrare.

---

## Flusso di accesso votante

### Via codice alfanumerico

```
POST /api/vote/access
Body: { "event_id": "...", "access_code": "ABCD1234" }
Response: { "voter_account_id": "...", "display_name": "...", "access_token": "..." }
```

Il frontend salva `voter_account_id` e `access_token` in localStorage.

### Via link personale

```
GET /api/vote/access?token=<access_token>
Response: { "voter_account_id": "...", "display_name": "...", "access_token": "..." }
```

Il link è nella forma: `/vote?token=<access_token>`

### Autenticazione su ogni richiesta di voto

Ogni request di voto pubblico invia:
```
Header: X-Voter-Account-Id: <voter_account_id>
Header: X-Voter-Access-Token: <access_token>
```

Il backend verifica che `access_token` corrisponda al `VoterAccount` indicato e che sia `active`.

---

## Blocco self-vote

In `public_vote_service.py`, dopo aver autenticato il votante, si esegue:

```python
def get_self_participant_id(
    db: Session,
    voter_account_id: str,
    competition_id: str,
) -> str | None:
    participant = db.scalar(
        select(Participant).where(
            Participant.voter_account_id == voter_account_id,
            Participant.competition_id == competition_id,
        )
    )
    return participant.id if participant else None
```

- **single_choice**: se `payload.participant_id == self_participant_id` → errore 409
- **ranked_choice**: se `self_participant_id in payload.ranked_participant_ids` → errore 409
- **criteria_rating**: se `self_participant_id in [r.participant_id for r in payload.ratings]` → errore 409

### Lato frontend

Quando si carica il ballot, il frontend chiede al backend:
```
GET /api/vote/competitions/{competition_id}/self-exclusion
Header: X-Voter-Account-Id / X-Voter-Access-Token
Response: { "excluded_participant_id": "..." | null }
```

Il frontend disabilita/nasconde la card del partecipante con quell'ID.

---

## API admin per VoterAccount

| Metodo | Path | Descrizione |
|---|---|---|
| `POST` | `/api/events/{event_id}/voter-accounts` | Crea VoterAccount (restituisce codice in chiaro) |
| `GET` | `/api/events/{event_id}/voter-accounts` | Lista VoterAccount |
| `GET` | `/api/events/{event_id}/voter-accounts/{id}` | Dettaglio |
| `PATCH` | `/api/events/{event_id}/voter-accounts/{id}` | Modifica nome/note/active |
| `DELETE` | `/api/events/{event_id}/voter-accounts/{id}` | Eliminazione |
| `POST` | `/api/events/{event_id}/voter-accounts/{id}/regenerate-code` | Rigenera codice (one-time) |
| `POST` | `/api/events/{event_id}/voter-accounts/{id}/link-participant` | Collega a Participant |
| `DELETE` | `/api/events/{event_id}/voter-accounts/{id}/unlink-participant/{participant_id}` | Scollega |

### Modifica Participant (admin)

Alternativa agli endpoint link/unlink: `PATCH /api/competitions/{competition_id}/participants/{id}` con campo `voter_account_id` opzionale nel payload.
Gli endpoint dedicati link/unlink sono preferiti per chiarezza semantica.

---

## Generazione codice

- Codice alfanumerico: 8 caratteri, charset `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (no ambigui)
- `access_token`: `uuid4()` generato lato backend
- Solo l'hash SHA-256 del codice viene salvato nel DB
- `access_token` viene salvato in chiaro nel DB (è già pseudonimo, non segreto critico)
- Il codice viene restituito solo nella risposta di creazione o rigenerazione

---

## Unicità e constraint

- La coppia `(voter_account_id, competition_id)` deve essere unica nella tabella `participants` (un VoterAccount non può essere collegato a due partecipanti della stessa competizione).
- Implementare come `UniqueConstraint("voter_account_id", "competition_id")` su `participants` (solo sulle righe dove `voter_account_id IS NOT NULL`; PostgreSQL gestisce NULL come non-uguale, quindi non serve filtrare esplicitamente).
- Se l'evento non è `draft`, non è possibile collegare/scollegare VoterAccount da Participant.

---

## Seed demo

Aggiungere al seed:
- 6 VoterAccount per l'evento demo
- I primi 4 corrispondono ai partecipanti (Anna, Marco, Luca, Giulia) — collegati alle rispettive entry nelle competizioni
- Gli altri 2 sono spettatori senza partecipazione (Votante Demo 1, Votante Demo 2)

---

## Out of scope (futuro)

- Import CSV di VoterAccount
- JWT per autenticazione votante
- QR code personale per ogni VoterAccount
- Verifica email
