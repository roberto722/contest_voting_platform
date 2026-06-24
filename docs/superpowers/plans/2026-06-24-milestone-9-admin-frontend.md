# Milestone 9 — Frontend Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completare il frontend admin aggiungendo la gestione dei VoterAccount (mancante) e suddividere il monolite `App.tsx` (3052 righe) in componenti focalizzati.

**Architecture:** L'attuale `App.tsx` gestisce già tutto l'admin (eventi, competizioni, partecipanti, criteri, giudici, sessioni di voto, risultati, schermo) ma manca completamente la sezione VoterAccount. La strategia è: (1) estrarre i tipi e le chiamate API in file dedicati, (2) aggiungere un tab `voterAccounts` nel workflow a step admin, (3) estrarre ogni tab admin in un componente separato, (4) verificare che tutto funzioni.

**Tech Stack:** React 18, TypeScript, Vite, Vanilla CSS, fetch nativo, no librerie di routing esterne.

## Global Constraints

- Nessuna dipendenza nuova senza approvazione esplicita.
- Il CSS del voto pubblico (`public-vote.css`) non deve mai modificare admin, giudici o schermo.
- La logica business non va nel frontend: zero calcoli di scoring, zero regole di voto.
- I form devono essere disabilitati quando `configurationLocked` (evento non `draft`).
- Tutti gli endpoint VoterAccount usano prefisso `/api/events/{event_id}/voter-accounts`.
- L'access code di un giudice non va mai mostrato recuperandolo dal DB — vale anche per i VoterAccount.
- Il tab `voterAccounts` deve essere disabilitato se non c'è un evento selezionato.

---

## Task 1: Tipi e API layer centralizzati

**Files:**
- Create: `frontend/src/admin/types.ts`
- Create: `frontend/src/admin/api.ts`

**Interfaces:**
- Produce: tutti i tipi `*Read` e la funzione `api<T>()` riusabili dai task successivi.

- [ ] **Step 1: Crea `frontend/src/admin/types.ts`**

```typescript
// frontend/src/admin/types.ts

export type EventStatus = "draft" | "live" | "closed" | "archived";
export type CompetitionStatus =
  | "draft"
  | "ready"
  | "voting_open"
  | "voting_closed"
  | "results_frozen"
  | "revealed";
export type PublicVoteMethod = "single_choice" | "ranked_choice" | "criteria_rating";
export type AccessMethod = "public_link" | "qr_pin" | "private_link";
export type VotingSessionStatus = "open" | "closed" | "cancelled";
export type ScreenMode =
  | "idle"
  | "show_qr"
  | "voting_open"
  | "countdown"
  | "show_results"
  | "reveal_ranking"
  | "show_podium"
  | "show_final_winners";

export type EventRead = {
  id: string;
  name: string;
  description: string | null;
  status: EventStatus;
};

export type CompetitionRead = {
  id: string;
  event_id: string;
  name: string;
  description: string | null;
  type: string | null;
  public_voting_enabled: boolean;
  judge_voting_enabled: boolean;
  public_vote_method: PublicVoteMethod;
  public_weight: number;
  judge_weight: number;
  access_method: AccessMethod;
  max_votes_per_user: number;
  max_votes_per_competition: number;
  allow_vote_update: boolean;
  status: CompetitionStatus;
};

export type ParticipantRead = {
  id: string;
  display_name: string;
  order_index: number;
  active: boolean;
  voter_account_id: string | null;
};

export type CriterionRead = {
  id: string;
  name: string;
  min_score: number;
  max_score: number;
  weight: number;
  active: boolean;
};

export type JudgeRead = {
  id: string;
  event_id: string;
  name: string;
  display_name: string;
  active: boolean;
  assigned_competition_ids: string[];
};

export type JudgeAccessCodeResetRead = {
  judge: JudgeRead;
  access_code: string;
};

export type VotingSessionRead = {
  id: string;
  label: string | null;
  status: VotingSessionStatus;
  opened_at: string | null;
  closed_at: string | null;
};

export type ResultEntry = {
  participant_id: string;
  display_name: string;
  rank: number;
  final_score: number;
  public_score: { normalized_score: number; raw_score: number };
  judge_score: { normalized_score: number; raw_score: number };
};

export type ResultsRead = {
  results: ResultEntry[];
};

export type SetupStepStatus = {
  step: string;
  completed: boolean;
  message: string;
};

export type CompetitionSetupStatus = {
  competition_id: string;
  event_id: string;
  is_ready: boolean;
  can_open_voting: boolean;
  completed_steps: string[];
  missing_steps: string[];
  issues: string[];
  open_issues: string[];
  messages: string[];
  checks: SetupStepStatus[];
};

export type PublicVoteSummaryRead = {
  competition_id: string;
  voting_session_id: string | null;
  total_votes: number;
  participants: { participant_id: string; display_name: string; vote_count: number }[];
};

export type ScreenStateRead = {
  id: string;
  event_id: string;
  competition_id: string | null;
  mode: ScreenMode;
  payload_json: Record<string, unknown>;
};

export type AuditLogRead = {
  id: string;
  event_id: string;
  competition_id: string | null;
  actor_type: string;
  actor_id: string | null;
  actor_label: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details_json: Record<string, unknown>;
  created_at: string;
};

export type VoterAccountRead = {
  id: string;
  event_id: string;
  display_name: string;
  notes: string | null;
  access_token: string;
  active: boolean;
};

export type VoterAccountCreatedRead = {
  voter_account: VoterAccountRead;
  access_code: string; // one-time, non memorizzare
};

export type VoterAccountCodeResetRead = {
  voter_account: VoterAccountRead;
  access_code: string; // one-time, non memorizzare
};

export type AdminTab =
  | "event"
  | "competition"
  | "participants"
  | "publicCriteria"
  | "judgeCriteria"
  | "judges"
  | "voterAccounts"
  | "review"
  | "live"
  | "screen"
  | "results"
  | "logs";

export type AdminStep = {
  id: AdminTab;
  label: string;
  disabled: boolean;
  reason?: string;
};

export type AdminState = {
  events: EventRead[];
  competitions: CompetitionRead[];
  participants: ParticipantRead[];
  publicCriteria: CriterionRead[];
  judgeCriteria: CriterionRead[];
  judges: JudgeRead[];
  voterAccounts: VoterAccountRead[];
  sessions: VotingSessionRead[];
  results: ResultsRead | null;
  setupStatus: CompetitionSetupStatus | null;
  screenState: ScreenStateRead | null;
  auditLogs: AuditLogRead[];
};

export type JudgeCredentialNotice = {
  judgeId: string;
  displayName: string;
  accessCode: string;
};

export type VoterCredentialNotice = {
  voterAccountId: string;
  displayName: string;
  accessCode: string;
};

export type AuditFilters = {
  query: string;
  actorType: string;
  entityType: string;
  action: string;
  pageSize: number;
  page: number;
};
```

- [ ] **Step 2: Crea `frontend/src/admin/api.ts`**

```typescript
// frontend/src/admin/api.ts

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const websocketBaseUrl = apiBaseUrl.replace(/^http/, "ws");

const setupIssueMap: Record<string, string> = {
  missing_active_participants: "Servono almeno 2 partecipanti attivi",
  missing_voting_mode: "Abilita voto pubblico o voto giudici",
  missing_public_vote_method: "Configura il metodo di voto pubblico",
  invalid_public_weight: "Peso pubblico non valido",
  invalid_judge_weight: "Peso giudici non valido",
  missing_assigned_judges: "Mancano giudici attivi assegnati",
  missing_judge_criteria: "Mancano i criteri di voto per i giudici",
  missing_public_criteria: "Mancano i criteri di voto per il pubblico",
  missing_access_pin: "Manca il PIN per accesso QR/PIN",
  event_not_live: "Evento non ancora live",
  competition_results_final: "Risultati già finali",
  missing_competitions: "Crea almeno una competizione",
};

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const issueMessages = Array.isArray(payload.issues)
      ? payload.issues.map((issue: string) => setupIssueMap[issue] ?? issue)
      : [];
    const backendMessages = Array.isArray(payload.messages) ? payload.messages : [];
    const details = [...issueMessages, ...backendMessages].filter(Boolean);
    throw new Error(
      details.length
        ? `${payload.detail ?? response.statusText}: ${details.join("; ")}`
        : payload.detail ?? response.statusText
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 3: Verifica che i file compilino senza errori TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: zero errori (solo warning tollerabili).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/admin/types.ts frontend/src/admin/api.ts
git commit -m "feat(frontend): extract shared types and api() helper to admin/"
```

---

## Task 2: VoterAccount tab — backend API check

**Files:**
- Read: `backend/app/api/routes/voter_accounts.py`

**Interfaces:**
- Consumes: `api<T>()` da `frontend/src/admin/api.ts`
- Produce: comprensione degli endpoint `/api/events/{event_id}/voter-accounts` e `/api/voter-accounts/{id}/...`

- [ ] **Step 1: Leggi `backend/app/api/routes/voter_accounts.py` per mappare gli endpoint**

Endpoint attesi (da verificare):
- `GET /api/events/{event_id}/voter-accounts` → lista VoterAccount
- `POST /api/events/{event_id}/voter-accounts` → crea VoterAccount, risposta `VoterAccountCreatedRead`
- `DELETE /api/voter-accounts/{id}` → elimina VoterAccount
- `POST /api/voter-accounts/{id}/regenerate-code` → rigenera codice, risposta `VoterAccountCodeResetRead`
- `POST /api/voter-accounts/{id}/link-participant/{participant_id}` → collega partecipante
- `DELETE /api/voter-accounts/{id}/link-participant/{participant_id}` → scollega partecipante

- [ ] **Step 2: Annota le discrepanze (se i path reali differiscono da quelli attesi, usa i path reali nei task successivi)**

---

## Task 3: VoterAccountsTab component

**Files:**
- Create: `frontend/src/admin/VoterAccountsTab.tsx`

**Interfaces:**
- Consumes: `VoterAccountRead`, `VoterAccountCreatedRead`, `VoterAccountCodeResetRead`, `ParticipantRead`, `CompetitionRead` da `types.ts`; `api<T>()` da `api.ts`
- Produce: `VoterAccountsTab` component con props `{ eventId, competitions, participants, voterAccounts, configurationLocked, onChanged, onCredential }`

- [ ] **Step 1: Crea `frontend/src/admin/VoterAccountsTab.tsx`**

```tsx
// frontend/src/admin/VoterAccountsTab.tsx
import { FormEvent, useState } from "react";
import type {
  CompetitionRead,
  ParticipantRead,
  VoterAccountCreatedRead,
  VoterAccountRead,
  VoterCredentialNotice,
} from "./types";
import { api } from "./api";

type Props = {
  eventId: string;
  competitions: CompetitionRead[];
  participants: ParticipantRead[]; // tutti i partecipanti dell'evento, di tutte le competizioni
  voterAccounts: VoterAccountRead[];
  configurationLocked: boolean;
  onChanged: () => Promise<void>;
  onCredential: (notice: VoterCredentialNotice) => void;
};

export function VoterAccountsTab({
  eventId,
  competitions,
  participants,
  voterAccounts,
  configurationLocked,
  onChanged,
  onCredential,
}: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore inatteso");
    } finally {
      setBusy(false);
    }
  }

  async function createVoterAccount(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const display_name = (data.get("display_name") as string).trim();
    const notes = (data.get("notes") as string).trim() || null;
    const access_code = (data.get("access_code") as string).trim();
    if (!display_name || !access_code) return;
    await run(async () => {
      const result = await api<VoterAccountCreatedRead>(
        `/api/events/${eventId}/voter-accounts`,
        {
          method: "POST",
          body: JSON.stringify({ display_name, notes, access_code }),
        }
      );
      onCredential({
        voterAccountId: result.voter_account.id,
        displayName: result.voter_account.display_name,
        accessCode: result.access_code,
      });
      form.reset();
      await onChanged();
    });
  }

  async function deleteVoterAccount(id: string) {
    await run(async () => {
      await api(`/api/voter-accounts/${id}`, { method: "DELETE" });
      await onChanged();
    });
  }

  async function regenerateCode(id: string, displayName: string) {
    await run(async () => {
      const result = await api<{ voter_account: VoterAccountRead; access_code: string }>(
        `/api/voter-accounts/${id}/regenerate-code`,
        { method: "POST" }
      );
      onCredential({
        voterAccountId: id,
        displayName,
        accessCode: result.access_code,
      });
      await onChanged();
    });
  }

  async function linkParticipant(voterAccountId: string, participantId: string) {
    await run(async () => {
      await api(
        `/api/voter-accounts/${voterAccountId}/link-participant/${participantId}`,
        { method: "POST" }
      );
      await onChanged();
    });
  }

  async function unlinkParticipant(voterAccountId: string, participantId: string) {
    await run(async () => {
      await api(
        `/api/voter-accounts/${voterAccountId}/link-participant/${participantId}`,
        { method: "DELETE" }
      );
      await onChanged();
    });
  }

  // Costruisce una mappa participantId -> competition name per visualizzazione
  const competitionMap = Object.fromEntries(competitions.map((c) => [c.id, c.name]));

  return (
    <div className="voter-accounts-tab">
      <h2>Account votanti</h2>
      <p className="form-hint">
        Ogni account votante ha un codice di accesso personale. Se un votante è anche
        partecipante a una competizione, collegalo qui: il sistema bloccherà il voto su
        se stesso automaticamente.
      </p>

      {error && <p className="error-banner">{error}</p>}

      {!configurationLocked && (
        <form className="voter-create-form" onSubmit={createVoterAccount}>
          <fieldset disabled={busy}>
            <legend>Nuovo account votante</legend>
            <div className="inline-grid">
              <label className="field-stack">
                <span>Nome visualizzato</span>
                <input name="display_name" placeholder="Es. Mario Rossi" required />
              </label>
              <label className="field-stack">
                <span>Codice di accesso</span>
                <input
                  name="access_code"
                  placeholder="Es. ABCD1234"
                  autoComplete="off"
                  required
                />
              </label>
              <label className="field-stack">
                <span>Note (opzionale)</span>
                <input name="notes" placeholder="Note interne" />
              </label>
            </div>
            <button type="submit">Crea account</button>
          </fieldset>
        </form>
      )}

      {configurationLocked && (
        <p className="lock-note">Evento live: creazione nuovi account bloccata.</p>
      )}

      <div className="voter-list">
        {voterAccounts.length === 0 && (
          <p className="form-hint">Nessun account votante creato.</p>
        )}
        {voterAccounts.map((va) => {
          const linked = participants.filter((p) => p.voter_account_id === va.id);
          return (
            <div key={va.id} className="voter-row">
              <div className="voter-row-header">
                <strong>{va.display_name}</strong>
                {va.notes && <span className="voter-notes">{va.notes}</span>}
                <span className={`badge ${va.active ? "badge-success" : "badge-muted"}`}>
                  {va.active ? "Attivo" : "Disattivato"}
                </span>
              </div>
              <div className="voter-row-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => regenerateCode(va.id, va.display_name)}
                >
                  Rigenera codice
                </button>
                {!configurationLocked && (
                  <button
                    type="button"
                    className="danger-button"
                    disabled={busy}
                    onClick={() => deleteVoterAccount(va.id)}
                  >
                    Elimina
                  </button>
                )}
              </div>

              {/* Partecipanti collegati */}
              <div className="voter-links">
                <span className="voter-links-label">Collegato a:</span>
                {linked.length === 0 ? (
                  <span className="form-hint">nessun partecipante</span>
                ) : (
                  linked.map((p) => {
                    // trova la competizione del partecipante
                    const comp = participants.find((pp) => pp.id === p.id);
                    return (
                      <span key={p.id} className="voter-link-chip">
                        {p.display_name}
                        {!configurationLocked && (
                          <button
                            type="button"
                            className="chip-remove"
                            disabled={busy}
                            onClick={() => unlinkParticipant(va.id, p.id)}
                          >
                            ✕
                          </button>
                        )}
                      </span>
                    );
                  })
                )}
              </div>

              {/* Selezione partecipante da collegare */}
              {!configurationLocked && (
                <div className="voter-link-add">
                  <select
                    id={`link-select-${va.id}`}
                    defaultValue=""
                    onChange={(e) => {
                      const participantId = e.target.value;
                      if (participantId) {
                        void linkParticipant(va.id, participantId);
                        e.target.value = "";
                      }
                    }}
                    disabled={busy}
                  >
                    <option value="">— Collega partecipante —</option>
                    {competitions.map((comp) => {
                      const compParticipants = participants.filter(
                        (p) =>
                          // filtra i partecipanti già collegati a questo account
                          p.voter_account_id !== va.id
                      );
                      if (compParticipants.length === 0) return null;
                      return (
                        <optgroup key={comp.id} label={comp.name}>
                          {compParticipants.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.display_name}
                            </option>
                          ))}
                        </optgroup>
                      );
                    })}
                  </select>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

> **Nota:** I `participants` passati come prop devono contenere **tutti** i partecipanti di tutte le competizioni dell'evento, non solo quelli della competizione corrente.

- [ ] **Step 2: Verifica compilazione TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: zero errori.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/admin/VoterAccountsTab.tsx
git commit -m "feat(frontend): add VoterAccountsTab component"
```

---

## Task 4: CSS per il tab VoterAccount

**Files:**
- Modify: `frontend/src/styles.css` (aggiungere regole per `.voter-accounts-tab`, `.voter-row`, `.voter-link-chip`, ecc.)

**Interfaces:**
- Consumes: design system esistente in `styles.css` (colori: `#162638`, `#eef2f5`, `#c7d0d9`)

- [ ] **Step 1: Aggiungi le regole CSS in fondo a `frontend/src/styles.css`**

```css
/* ===== VoterAccounts tab ===== */
.voter-accounts-tab h2 {
  margin-bottom: 8px;
}

.voter-create-form fieldset {
  border: 1px solid #c7d0d9;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.voter-create-form legend {
  font-weight: 700;
  padding: 0 6px;
}

.voter-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.voter-row {
  background: #fff;
  border: 1px solid #c7d0d9;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.voter-row-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.voter-notes {
  color: #6b7a8d;
  font-size: 0.875rem;
}

.voter-row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.voter-links {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.voter-links-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #6b7a8d;
}

.voter-link-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #e8f0fe;
  color: #1a3c6e;
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 0.8125rem;
  font-weight: 600;
}

.chip-remove {
  background: none;
  border: none;
  color: #9d2f1a;
  min-height: unset;
  padding: 0 2px;
  font-size: 0.75rem;
  cursor: pointer;
  font-weight: 700;
}

.voter-link-add select {
  width: auto;
  min-width: 200px;
}

.error-banner {
  background: #ffeaea;
  border: 1px solid #e57373;
  border-radius: 6px;
  color: #9d2f1a;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 0.875rem;
}

.badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}

.badge-success {
  background: #e6f4ea;
  color: #1e6b3a;
}

.badge-muted {
  background: #f0f0f0;
  color: #6b7a8d;
}
```

- [ ] **Step 2: Verifica visivamente che il tab si veda bene nel browser**

Apri `http://localhost:5173`, naviga al tab "Account votanti".

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles.css
git commit -m "style(frontend): add VoterAccountsTab CSS"
```

---

## Task 5: Integrazione VoterAccountsTab in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `VoterAccountsTab` da `./admin/VoterAccountsTab`, tipi da `./admin/types`, `api` da `./admin/api`
- Produce: tab "Account votanti" visibile nel workflow admin, integrazione caricamento dati e state

> **Nota:** In questo task si modifica `App.tsx` senza ancora smontarlo. Il refactoring completo è nel Task 6.

- [ ] **Step 1: Aggiungi `voterAccounts: VoterAccountRead[]` all'`AdminState` in `App.tsx` e al `emptyState`**

Cambia:
```typescript
// PRIMA (App.tsx ~riga 226-238)
type AdminState = {
  ...
  judges: JudgeRead[];
  sessions: VotingSessionRead[];
  ...
};

const emptyState: AdminState = {
  ...
  judges: [],
  sessions: [],
  ...
};
```

In:
```typescript
type AdminState = {
  ...
  judges: JudgeRead[];
  voterAccounts: VoterAccountRead[];
  sessions: VotingSessionRead[];
  ...
};

const emptyState: AdminState = {
  ...
  judges: [],
  voterAccounts: [],
  sessions: [],
  ...
};
```

- [ ] **Step 2: Aggiungi il caricamento dei voterAccounts in `loadEventData`**

```typescript
// PRIMA
async function loadEventData(eventId: string) {
  const [competitions, judges, screenState, auditLogs] = await Promise.all([
    api<CompetitionRead[]>(`/api/events/${eventId}/competitions`),
    api<JudgeRead[]>(`/api/events/${eventId}/judges`),
    api<ScreenStateRead>(`/api/events/${eventId}/screen-state`),
    api<AuditLogRead[]>(`/api/events/${eventId}/audit-logs?limit=500`),
  ]);
  setState((current) => ({
    ...current,
    competitions,
    judges,
    participants: [],
    ...
  }));
```

```typescript
// DOPO
async function loadEventData(eventId: string) {
  const [competitions, judges, voterAccounts, screenState, auditLogs] = await Promise.all([
    api<CompetitionRead[]>(`/api/events/${eventId}/competitions`),
    api<JudgeRead[]>(`/api/events/${eventId}/judges`),
    api<VoterAccountRead[]>(`/api/events/${eventId}/voter-accounts`),
    api<ScreenStateRead>(`/api/events/${eventId}/screen-state`),
    api<AuditLogRead[]>(`/api/events/${eventId}/audit-logs?limit=500`),
  ]);
  setState((current) => ({
    ...current,
    competitions,
    judges,
    voterAccounts,
    participants: [],
    ...
  }));
```

- [ ] **Step 3: Aggiungi il tipo `VoterCredentialNotice` allo state e il tab `voterAccounts` agli `adminSteps`**

```typescript
// Aggiungi state dopo judgeCredentialNotice
const [voterCredentialNotice, setVoterCredentialNotice] = useState<VoterCredentialNotice | null>(null);
```

```typescript
// Nella definizione adminSteps, aggiungi dopo "judges":
{
  id: "voterAccounts",
  label: "Votanti",
  disabled: !selectedEvent,
  reason: "Seleziona evento",
},
```

- [ ] **Step 4: Aggiungi il tab nel render JSX**

Nella sezione dove sono gestiti i tab (`adminTab === "judges"`, ecc.), aggiungi:

```tsx
{adminTab === "voterAccounts" && selectedEventId && (
  <VoterAccountsTab
    eventId={selectedEventId}
    competitions={state.competitions}
    participants={state.participants}
    voterAccounts={state.voterAccounts}
    configurationLocked={configurationLocked}
    onChanged={() => loadEventData(selectedEventId)}
    onCredential={setVoterCredentialNotice}
  />
)}
```

> **Nota:** `state.participants` contiene solo i partecipanti della competition selezionata. Per il tab VoterAccounts è necessario caricare i partecipanti di **tutte** le competizioni. Aggiungere una funzione `loadAllParticipants(eventId)` che itera sulle competizioni e aggrega i risultati, oppure aggiungere un campo `allParticipants: ParticipantRead[]` all'`AdminState` popolato in `loadEventData`.

- [ ] **Step 5: Aggiungi il modal per `voterCredentialNotice`**

```tsx
{voterCredentialNotice && (
  <dialog open className="modal">
    <div className="modal-body">
      <h2>Codice accesso</h2>
      <p>
        <strong>{voterCredentialNotice.displayName}</strong>
      </p>
      <p className="form-hint">
        Copia questo codice subito: non sarà più recuperabile.
      </p>
      <code className="access-code-display">{voterCredentialNotice.accessCode}</code>
      <button type="button" onClick={() => setVoterCredentialNotice(null)}>
        Ho copiato il codice
      </button>
    </div>
  </dialog>
)}
```

- [ ] **Step 6: Verifica compilazione TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: zero errori.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): integrate VoterAccountsTab into admin workflow"
```

---

## Task 6: Estrazione componenti admin da App.tsx

**Files:**
- Create: `frontend/src/admin/EventTab.tsx`
- Create: `frontend/src/admin/CompetitionTab.tsx`
- Create: `frontend/src/admin/ParticipantsTab.tsx`
- Create: `frontend/src/admin/CriteriaTab.tsx`
- Create: `frontend/src/admin/JudgesTab.tsx`
- Create: `frontend/src/admin/ReviewTab.tsx`
- Create: `frontend/src/admin/LiveTab.tsx`
- Create: `frontend/src/admin/ResultsTab.tsx`
- Create: `frontend/src/admin/LogsTab.tsx`
- Modify: `frontend/src/App.tsx` (ridurre usando i nuovi componenti)

**Interfaces:**
- Ogni componente tab riceve via props lo stato e le callback necessari, senza dipendere dallo state globale direttamente.

> **Nota:** Questo task è il più esteso. Procedi tab per tab. Se `App.tsx` fosse ancora troppo grande dopo l'estrazione, continua con ulteriori split nel Task 7.

- [ ] **Step 1: Estrai `EventTab` — form creazione evento + lista eventi**

Il componente riceve:
```tsx
type EventTabProps = {
  events: EventRead[];
  selectedEventId: string;
  onSelect: (id: string) => void;
  onDelete: (event: EventRead) => void;
  onCreate: (form: HTMLFormElement) => Promise<void>;
  configurationLocked: boolean;
};
```

- [ ] **Step 2: Estrai `CompetitionTab` — form creazione competizione + lista competizioni + dettaglio**

```tsx
type CompetitionTabProps = {
  competitions: CompetitionRead[];
  selectedCompetitionId: string;
  selectedEventId: string;
  configurationLocked: boolean;
  onSelect: (id: string) => void;
  onDelete: (comp: CompetitionRead) => void;
  onCreate: (form: HTMLFormElement) => Promise<void>;
  onSeedFakeData: (participants: number, judges: number, criteria: number) => Promise<void>;
};
```

- [ ] **Step 3: Estrai `ParticipantsTab`**

```tsx
type ParticipantsTabProps = {
  participants: ParticipantRead[];
  competitionId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onToggleActive: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};
```

- [ ] **Step 4: Estrai `CriteriaTab`** (usato sia per criteri pubblici che giudici, con prop `type: "public" | "judge"`)

```tsx
type CriteriaTabProps = {
  criteria: CriterionRead[];
  type: "public" | "judge";
  competitionId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onToggleActive: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};
```

- [ ] **Step 5: Estrai `JudgesTab`**

```tsx
type JudgesTabProps = {
  judges: JudgeRead[];
  competitions: CompetitionRead[];
  eventId: string;
  configurationLocked: boolean;
  onAdd: (form: HTMLFormElement) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onToggleCompetition: (judgeId: string, competitionId: string, isAssigned: boolean) => Promise<void>;
  onRegenerateCode: (judgeId: string) => Promise<void>;
};
```

- [ ] **Step 6: Estrai `ReviewTab`**

```tsx
type ReviewTabProps = {
  setupStatus: CompetitionSetupStatus | null;
  competition: CompetitionRead | null;
};
```

- [ ] **Step 7: Estrai `LiveTab`**

```tsx
type LiveTabProps = {
  competition: CompetitionRead | null;
  event: EventRead | null;
  sessions: VotingSessionRead[];
  setupStatus: CompetitionSetupStatus | null;
  canOpenVoting: boolean;
  onGoLive: () => Promise<void>;
  onOpenVoting: (form: HTMLFormElement) => Promise<void>;
  onCloseVoting: () => Promise<void>;
};
```

- [ ] **Step 8: Estrai `ResultsTab`**

```tsx
type ResultsTabProps = {
  results: ResultsRead | null;
  competition: CompetitionRead | null;
  onFreeze: () => Promise<void>;
};
```

- [ ] **Step 9: Estrai `LogsTab`**

```tsx
type LogsTabProps = {
  auditLogs: AuditLogRead[];
  filters: AuditFilters;
  onFiltersChange: (f: AuditFilters) => void;
};
```

- [ ] **Step 10: Aggiorna `App.tsx` per usare i nuovi componenti**

Ogni sezione `{adminTab === "xxx" && ...}` viene sostituita con il componente estratto.

- [ ] **Step 11: Verifica compilazione TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: zero errori.

- [ ] **Step 12: Verifica funzionamento nel browser**

Apri `http://localhost:5173`, naviga tutti i tab admin, verifica che:
- Creazione evento funziona
- Creazione competizione funziona
- Tab Votanti mostra la lista e permette di creare/eliminare/collegare
- Apertura/chiusura votazione funziona
- Risultati e freeze funzionano

- [ ] **Step 13: Commit**

```bash
git add frontend/src/admin/ frontend/src/App.tsx
git commit -m "refactor(frontend): extract admin tab components from App.tsx monolith"
```

---

## Task 7: VoterAccount nel tab Partecipanti — visualizzazione collegamento

**Files:**
- Modify: `frontend/src/admin/ParticipantsTab.tsx`

**Interfaces:**
- Consumes: `VoterAccountRead` da `types.ts`

- [ ] **Step 1: Aggiungi prop `voterAccounts: VoterAccountRead[]` a `ParticipantsTab`**

Per ogni partecipante, mostra se è collegato a un VoterAccount (solo in lettura nel tab partecipanti — la gestione del collegamento è nel tab VoterAccounts).

```tsx
// In ParticipantsTab, per ogni partecipante mostra:
const linkedAccount = voterAccounts.find(va => va.id === participant.voter_account_id);
// ...
{linkedAccount ? (
  <span className="voter-link-chip">{linkedAccount.display_name}</span>
) : (
  <span className="form-hint">nessun account votante</span>
)}
```

- [ ] **Step 2: Verifica compilazione TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/admin/ParticipantsTab.tsx
git commit -m "feat(frontend): show voter account link in ParticipantsTab"
```

---

## Task 8: Smoke test manuale completo

- [ ] **Step 1: Avvia il backend**

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Avvia il frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Verifica flusso completo admin**

Percorso da verificare (in ordine):
1. Login admin (http://localhost:5173)
2. Crea evento "Test Serata"
3. Crea competizione "Test Competizione" (voto pubblico single_choice)
4. Tab Partecipanti: aggiungi 3 partecipanti
5. Tab Votanti: crea 2 account votanti con codice, collega 1 account a un partecipante
6. Tab Giudici: skip (non richiesto per single_choice senza giudici)
7. Tab Review: verifica checklist verde
8. Tab Live: porta evento live, apri votazione
9. Verifica che nel tab Votanti non sia possibile creare nuovi account (evento live)
10. Chiudi votazione
11. Tab Risultati: verifica classifica, esegui freeze

- [ ] **Step 4: Commit finale**

```bash
git add .
git commit -m "test(frontend): milestone-9 admin frontend complete"
```

---

## Verification Plan

### Automated Tests
Non ci sono test unitari frontend in questo progetto. La verifica è manuale + TypeScript compile.

```bash
cd frontend && npx tsc --noEmit
```

### Manual Verification
- Tutti i tab admin funzionano senza errori in console
- Il tab "Votanti" mostra, crea, elimina account e gestisce i collegamenti partecipante
- Il modal one-time del codice appare alla creazione e rigenerazione
- Con evento live, i form di configurazione sono disabilitati
- Il tab Partecipanti mostra il VoterAccount collegato

## Open Questions

1. **Percorso endpoint `regenerate-code`**: verificare in `voter_accounts.py` se il path è `/regenerate-code` o `/access-code/regenerate` (come per i giudici).
2. **Partecipanti multi-competizione**: decidere se `loadEventData` deve caricare tutti i partecipanti di tutte le competizioni, o se `VoterAccountsTab` li carica autonomamente.
3. **`ParticipantRead.voter_account_id`**: verificare che il backend lo restituisca nel DTO (potrebbe non essere incluso nello schema attuale).
