# Public Vote Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separare il voto pubblico su `/vote` e applicare il layout Quasanremo mobile-first approvato senza modificare backend o regole di voto.

**Architecture:** Il bootstrap Vite carica dinamicamente `App` oppure `PublicVotePage` in base al pathname, così le due aree non condividono markup o CSS. La logica pubblica non visuale resta in un piccolo modulo TypeScript testabile con `node:test`; il componente usa le API esistenti e asset statici locali.

**Tech Stack:** React 18, TypeScript, Vite 6, Node 24 `node:test`, CSS nativo, Docker Compose.

---

## File structure

- Create `frontend/src/public-vote/publicVote.ts`: routing, link, stato sessione e costruzione payload.
- Create `frontend/tests/publicVote.test.ts`: test Node senza nuove dipendenze.
- Create `frontend/src/public-vote/PublicVotePage.tsx`: accesso, caricamento, tre metodi di voto e stati finali.
- Create `frontend/src/public-vote/public-vote.css`: tema Quasanremo isolato.
- Create `frontend/public/quasanremo/**`: copie degli asset approvati.
- Modify `frontend/src/main.tsx`: bootstrap dinamico per `/vote`.
- Modify `frontend/src/App.tsx`: rimuovere la vista pubblica incorporata e aggiornare i link.
- Modify `frontend/package.json`: comando test nativo.
- Modify `frontend/Dockerfile`: includere gli asset statici.
- Modify `README.md` e `AGENTS.md`: documentare il nuovo entry point.

### Task 1: Logica pubblica testabile

**Files:**
- Create: `frontend/tests/publicVote.test.ts`
- Create: `frontend/src/public-vote/publicVote.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: aggiungere il comando test e il test fallente**

In `frontend/package.json` aggiungere:

```json
"test": "node --test tests/*.test.ts"
```

Creare `frontend/tests/publicVote.test.ts`:

```ts
import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPublicVotePayload,
  getVotingState,
  isPublicVotePath,
  participantBackdrop,
  publicVoteHref,
} from "../src/public-vote/publicVote.ts";

test("riconosce soltanto la route pubblica", () => {
  assert.equal(isPublicVotePath("/vote"), true);
  assert.equal(isPublicVotePath("/vote/"), true);
  assert.equal(isPublicVotePath("/"), false);
  assert.equal(isPublicVotePath("/voter"), false);
});

test("costruisce link pubblici codificando l'id", () => {
  assert.equal(publicVoteHref("competition 1"), "/vote?competitionId=competition%201");
});

test("distingue sessione aperta, attesa e chiusa", () => {
  assert.equal(getVotingState([]), "waiting");
  assert.equal(getVotingState([{ status: "closed" }]), "closed");
  assert.equal(getVotingState([{ status: "closed" }, { status: "open" }]), "open");
});

test("costruisce i tre payload di voto", () => {
  assert.deepEqual(
    buildPublicVotePayload("token", "single_choice", {
      participantId: "p1",
      rankedParticipantIds: [],
      ratings: [],
    }),
    { voter_token: "token", method: "single_choice", participant_id: "p1" },
  );
  assert.deepEqual(
    buildPublicVotePayload("token", "ranked_choice", {
      participantId: "",
      rankedParticipantIds: ["p2", "", "p1"],
      ratings: [],
    }),
    { voter_token: "token", method: "ranked_choice", ranked_participant_ids: ["p2", "p1"] },
  );
  assert.deepEqual(
    buildPublicVotePayload("token", "criteria_rating", {
      participantId: "p1",
      rankedParticipantIds: [],
      ratings: [{ criterion_id: "c1", score: 8 }],
    }),
    {
      voter_token: "token",
      method: "criteria_rating",
      ratings: [{ participant_id: "p1", criteria: [{ criterion_id: "c1", score: 8 }] }],
    },
  );
});

test("riusa ciclicamente i cinque fondali generici", () => {
  assert.equal(participantBackdrop(0), "/quasanremo/artists/artist-bg-01.webp");
  assert.equal(participantBackdrop(5), "/quasanremo/artists/artist-bg-01.webp");
});
```

- [ ] **Step 2: eseguire il test e verificare RED**

Run:

```powershell
cd frontend
npm test
```

Expected: FAIL con `ERR_MODULE_NOT_FOUND` per `src/public-vote/publicVote.ts`.

- [ ] **Step 3: implementare il minimo modulo di dominio UI**

Creare `frontend/src/public-vote/publicVote.ts`:

```ts
export type PublicVoteMethod = "single_choice" | "ranked_choice" | "criteria_rating";
export type VotingState = "open" | "waiting" | "closed";

export type Rating = {
  criterion_id: string;
  score: number;
};

export type VoteSelection = {
  participantId: string;
  rankedParticipantIds: string[];
  ratings: Rating[];
};

export function isPublicVotePath(pathname: string): boolean {
  return pathname === "/vote" || pathname === "/vote/";
}

export function publicVoteHref(competitionId: string): string {
  return `/vote?competitionId=${encodeURIComponent(competitionId)}`;
}

export function getVotingState(sessions: Array<{ status: string }>): VotingState {
  if (sessions.some((session) => session.status === "open")) return "open";
  return sessions.length ? "closed" : "waiting";
}

export function participantBackdrop(index: number): string {
  const assetNumber = String((index % 5) + 1).padStart(2, "0");
  return `/quasanremo/artists/artist-bg-${assetNumber}.webp`;
}

export function buildPublicVotePayload(
  voterToken: string,
  method: PublicVoteMethod,
  selection: VoteSelection,
) {
  if (method === "single_choice") {
    return {
      voter_token: voterToken,
      method,
      participant_id: selection.participantId,
    };
  }
  if (method === "ranked_choice") {
    return {
      voter_token: voterToken,
      method,
      ranked_participant_ids: selection.rankedParticipantIds.filter(Boolean),
    };
  }
  return {
    voter_token: voterToken,
    method,
    ratings: [{ participant_id: selection.participantId, criteria: selection.ratings }],
  };
}
```

- [ ] **Step 4: verificare GREEN**

Run:

```powershell
cd frontend
npm test
```

Expected: 5 test PASS, 0 FAIL.

- [ ] **Step 5: commit**

```powershell
git add frontend/package.json frontend/tests/publicVote.test.ts frontend/src/public-vote/publicVote.ts
git commit -m "test: define public vote entry behavior"
```

### Task 2: Asset statici e Docker

**Files:**
- Create: `frontend/public/quasanremo/backgrounds/*`
- Create: `frontend/public/quasanremo/brand/*`
- Create: `frontend/public/quasanremo/artists/*`
- Create: `frontend/public/quasanremo/icons/*`
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: copiare soltanto gli asset usati**

Run dalla root:

```powershell
$source = 'C:\Users\r.scardigno\Desktop\quasanremo_assets'
$target = 'frontend\public\quasanremo'
New-Item -ItemType Directory -Force "$target\backgrounds", "$target\brand", "$target\artists", "$target\icons" | Out-Null
Copy-Item "$source\backgrounds\bg-public-desktop.png", "$source\backgrounds\bg-public-mobile.png", "$source\backgrounds\texture-dark-noise.png" "$target\backgrounds"
Copy-Item "$source\brand\logo-rectangular-transparent.png" "$target\brand"
Copy-Item "$source\artists\artist-bg-*.webp" "$target\artists"
Copy-Item "$source\icons\waiting.svg", "$source\icons\success.svg", "$source\icons\closed.svg", "$source\icons\error.svg", "$source\icons\lock.svg", "$source\icons\vote.svg" "$target\icons"
```

- [ ] **Step 2: verificare il set minimo**

Run:

```powershell
$files = Get-ChildItem 'frontend\public\quasanremo' -File -Recurse
if ($files.Count -ne 15) { throw "Attesi 15 asset, trovati $($files.Count)" }
```

Expected: exit 0.

- [ ] **Step 3: includere `public` nell'immagine frontend**

In `frontend/Dockerfile`, dopo `COPY src ./src`, aggiungere:

```dockerfile
COPY public ./public
```

- [ ] **Step 4: verificare il build Dockerfile senza avviare servizi**

Run:

```powershell
docker compose build frontend
```

Expected: exit 0 e layer `COPY public ./public` completato.

- [ ] **Step 5: commit**

```powershell
git add frontend/public/quasanremo frontend/Dockerfile
git commit -m "assets: add Quasanremo public vote theme"
```

### Task 3: Pagina pubblica dedicata

**Files:**
- Create: `frontend/src/public-vote/PublicVotePage.tsx`
- Create: `frontend/src/public-vote/public-vote.css`

- [ ] **Step 1: creare il componente pubblico**

Creare `frontend/src/public-vote/PublicVotePage.tsx`:

```tsx
import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";

import {
  buildPublicVotePayload,
  getVotingState,
  participantBackdrop,
  type PublicVoteMethod,
} from "./publicVote";
import "./public-vote.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type Competition = {
  id: string;
  name: string;
  public_vote_method: PublicVoteMethod;
  max_votes_per_user: number;
};
type Participant = { id: string; display_name: string; active: boolean };
type Criterion = { id: string; name: string; min_score: number; max_score: number; active: boolean };
type VotingSession = { id: string; status: "open" | "closed" | "cancelled" };
type VoteData = {
  competition: Competition;
  participants: Participant[];
  criteria: Criterion[];
  sessions: VotingSession[];
};
type Phase = "access" | "loading" | "ready" | "submitting" | "success" | "error";

async function publicApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? response.statusText);
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

function getPublicVoterToken(): string {
  const key = "contest-public-voter-token";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const token = typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(key, token);
  return token;
}

function BrandHeader({ title, subtitle }: { title?: string; subtitle?: string }) {
  return (
    <header className="public-brand">
      <img src="/quasanremo/brand/logo-rectangular-transparent.png" alt="Quasanremo International" />
      {title ? <h1>{title}</h1> : null}
      {subtitle ? <p>{subtitle}</p> : null}
    </header>
  );
}

function StatusView({
  icon,
  title,
  text,
  action,
  onAction,
}: {
  icon: "waiting" | "success" | "closed" | "error";
  title: string;
  text: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <section className="public-status" role={icon === "error" ? "alert" : "status"}>
      <img src={`/quasanremo/icons/${icon}.svg`} alt="" />
      <h2>{title}</h2>
      <p>{text}</p>
      {action && onAction ? <button onClick={onAction}>{action}</button> : null}
    </section>
  );
}

export default function PublicVotePage() {
  const queryCompetitionId = new URLSearchParams(window.location.search).get("competitionId") ?? "";
  const [competitionId, setCompetitionId] = useState(queryCompetitionId);
  const [pin, setPin] = useState("");
  const [phase, setPhase] = useState<Phase>("access");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState<"access" | "submit">("access");
  const [data, setData] = useState<VoteData | null>(null);
  const [selectedParticipantId, setSelectedParticipantId] = useState("");
  const [rankedParticipantIds, setRankedParticipantIds] = useState<string[]>([]);
  const [criteriaScores, setCriteriaScores] = useState<Record<string, number>>({});
  const autoLoaded = useRef(false);

  async function loadCompetition() {
    const id = competitionId.trim();
    if (!id) return;
    setPhase("loading");
    setError("");
    try {
      await publicApi(`/api/competitions/${id}/public-access`, {
        method: "POST",
        body: JSON.stringify({ pin: pin || null }),
      });
      const [competition, participants, criteria, sessions] = await Promise.all([
        publicApi<Competition>(`/api/competitions/${id}`),
        publicApi<Participant[]>(`/api/competitions/${id}/participants`),
        publicApi<Criterion[]>(`/api/competitions/${id}/public-criteria`),
        publicApi<VotingSession[]>(`/api/competitions/${id}/voting-sessions`),
      ]);
      const activeParticipants = participants.filter((participant) => participant.active);
      const activeCriteria = criteria.filter((criterion) => criterion.active);
      setData({ competition, participants: activeParticipants, criteria: activeCriteria, sessions });
      setSelectedParticipantId(activeParticipants[0]?.id ?? "");
      setRankedParticipantIds(
        activeParticipants.slice(0, competition.max_votes_per_user).map((participant) => participant.id),
      );
      setCriteriaScores(Object.fromEntries(activeCriteria.map((criterion) => [criterion.id, criterion.min_score])));
      window.history.replaceState(null, "", `/vote?competitionId=${encodeURIComponent(id)}`);
      setPhase("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Errore inatteso");
      setRetry("access");
      setPhase("error");
    }
  }

  async function submitVote() {
    if (!data) return;
    setPhase("submitting");
    try {
      const payload = buildPublicVotePayload(getPublicVoterToken(), data.competition.public_vote_method, {
        participantId: selectedParticipantId,
        rankedParticipantIds,
        ratings: data.criteria.map((criterion) => ({
          criterion_id: criterion.id,
          score: criteriaScores[criterion.id] ?? criterion.min_score,
        })),
      });
      await publicApi(`/api/competitions/${data.competition.id}/public-votes`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setPhase("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Errore inatteso");
      setRetry("submit");
      setPhase("error");
    }
  }

  function reset() {
    window.history.replaceState(null, "", "/vote");
    setCompetitionId("");
    setPin("");
    setData(null);
    setPhase("access");
  }

  useEffect(() => {
    if (!autoLoaded.current && queryCompetitionId) {
      autoLoaded.current = true;
      void loadCompetition();
    }
  }, []);

  const votingState = data ? getVotingState(data.sessions) : "waiting";
  const canSubmit = data?.competition.public_vote_method === "ranked_choice"
    ? rankedParticipantIds.some(Boolean)
    : Boolean(selectedParticipantId);

  return (
    <main className="public-vote-page">
      <div className="public-vote-card">
        {phase === "access" ? (
          <>
            <BrandHeader title="Accedi alla competizione" subtitle="Inserisci i dati ricevuti" />
            <form className="public-access-form" onSubmit={(event: FormEvent) => { event.preventDefault(); void loadCompetition(); }}>
              <label>
                <span>Codice competizione</span>
                <span className="public-field"><img src="/quasanremo/icons/vote.svg" alt="" /><input value={competitionId} onChange={(event) => setCompetitionId(event.target.value)} required /></span>
              </label>
              <label>
                <span>PIN, se richiesto</span>
                <span className="public-field"><img src="/quasanremo/icons/lock.svg" alt="" /><input value={pin} onChange={(event) => setPin(event.target.value)} inputMode="numeric" /></span>
              </label>
              <button className="public-primary" type="submit">Entra</button>
            </form>
          </>
        ) : null}

        {phase === "loading" || phase === "submitting" ? (
          <><BrandHeader /><StatusView icon="waiting" title={phase === "loading" ? "Caricamento competizione" : "Registrazione del voto"} text="Attendi qualche secondo." /></>
        ) : null}

        {phase === "error" ? (
          <><BrandHeader /><StatusView icon="error" title="Si è verificato un errore" text={error} action={retry === "submit" ? "Riprova" : "Modifica i dati"} onAction={() => retry === "submit" ? void submitVote() : setPhase("access")} /></>
        ) : null}

        {phase === "success" ? (
          <><BrandHeader /><StatusView icon="success" title="Voto registrato!" text="Grazie per aver partecipato." action="Torna all'accesso" onAction={reset} /></>
        ) : null}

        {phase === "ready" && data && votingState !== "open" ? (
          <><BrandHeader /><StatusView icon={votingState === "waiting" ? "waiting" : "closed"} title={votingState === "waiting" ? "La votazione non è ancora aperta" : "La votazione è chiusa"} text={votingState === "waiting" ? "Attendi l'annuncio del presentatore." : "Grazie per aver partecipato."} action="Torna all'accesso" onAction={reset} /></>
        ) : null}

        {phase === "ready" && data && votingState === "open" ? (
          <>
            <BrandHeader title="Scegli il tuo artista" subtitle={data.competition.name} />
            <div className="public-context"><span>{data.competition.public_vote_method.replaceAll("_", " ")}</span><strong>● Votazione aperta</strong></div>
            {data.competition.public_vote_method !== "ranked_choice" ? (
              <div className="public-participants">
                {data.participants.map((participant, index) => (
                  <button
                    aria-pressed={participant.id === selectedParticipantId}
                    className={participant.id === selectedParticipantId ? "public-participant selected" : "public-participant"}
                    key={participant.id}
                    onClick={() => setSelectedParticipantId(participant.id)}
                    style={{ "--participant-bg": `url(${participantBackdrop(index)})` } as CSSProperties}
                    type="button"
                  >
                    <span className="public-number">{String(index + 1).padStart(2, "0")}</span>
                    <span>{participant.display_name}</span>
                    {participant.id === selectedParticipantId ? <b aria-hidden="true">✓</b> : null}
                  </button>
                ))}
              </div>
            ) : (
              <div className="public-ranked">
                {rankedParticipantIds.map((participantId, index) => (
                  <label key={index}><span>Posizione {index + 1}</span><select value={participantId} onChange={(event) => { const next = [...rankedParticipantIds]; next[index] = event.target.value; setRankedParticipantIds(next); }}><option value="">Seleziona</option>{data.participants.map((participant) => <option disabled={rankedParticipantIds.includes(participant.id) && participantId !== participant.id} key={participant.id} value={participant.id}>{participant.display_name}</option>)}</select></label>
                ))}
              </div>
            )}
            {data.competition.public_vote_method === "criteria_rating" ? (
              <div className="public-criteria">{data.criteria.map((criterion) => <label key={criterion.id}><span>{criterion.name}<strong>{criteriaScores[criterion.id] ?? criterion.min_score}</strong></span><input type="range" min={criterion.min_score} max={criterion.max_score} value={criteriaScores[criterion.id] ?? criterion.min_score} onChange={(event) => setCriteriaScores((current) => ({ ...current, [criterion.id]: Number(event.target.value) }))} /></label>)}</div>
            ) : null}
            <button className="public-primary public-confirm" disabled={!canSubmit} onClick={() => void submitVote()} type="button">Conferma voto</button>
          </>
        ) : null}
      </div>
    </main>
  );
}
```

- [ ] **Step 2: aggiungere il CSS isolato**

Creare `frontend/src/public-vote/public-vote.css`:

```css
:root { font-family: "Segoe UI", system-ui, sans-serif; color: #f8f1e5; background: #070707; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; }
button, input, select { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .45; }

.public-vote-page {
  min-height: 100vh;
  display: grid;
  justify-items: center;
  padding: 20px 14px;
  background: #070707 url("/quasanremo/backgrounds/bg-public-mobile.png") center top / cover fixed;
}

.public-vote-card {
  width: min(100%, 560px);
  min-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(214, 157, 67, .58);
  border-radius: 20px;
  background: rgba(6, 7, 9, .86) url("/quasanremo/backgrounds/texture-dark-noise.png");
  box-shadow: 0 22px 80px #000, inset 0 0 45px rgba(214, 157, 67, .08);
  padding: 22px 16px 16px;
  overflow: hidden;
}

.public-brand { text-align: center; }
.public-brand img { width: min(66%, 250px); height: 76px; object-fit: contain; }
.public-brand h1 { margin: 8px 0 4px; color: #edc477; font: 700 clamp(1.65rem, 7vw, 2.3rem)/1.05 Georgia, serif; }
.public-brand p { margin: 0 0 18px; color: #ded7cc; font-size: .9rem; }

.public-access-form { flex: 1; display: grid; align-content: center; gap: 14px; }
.public-access-form label, .public-ranked label, .public-criteria label { display: grid; gap: 7px; color: #e5d8c4; font-size: .82rem; font-weight: 700; }
.public-field { display: flex; align-items: center; gap: 9px; min-height: 48px; border: 1px solid #6f604c; border-radius: 10px; background: rgba(6, 7, 9, .9); padding: 0 12px; }
.public-field:focus-within { border-color: #efbd62; box-shadow: 0 0 0 3px rgba(239, 189, 98, .18); }
.public-field img { width: 20px; height: 20px; }
.public-field input { width: 100%; border: 0; outline: 0; background: transparent; color: #fff; }

.public-primary {
  width: 100%; min-height: 50px; border: 1px solid #ffd57c; border-radius: 11px;
  background: linear-gradient(#ffd477, #a9671e); color: #170f06; font-weight: 900; text-transform: uppercase;
  box-shadow: inset 0 0 14px rgba(255,255,255,.24), 0 0 18px rgba(223, 157, 48, .22);
}
.public-primary:hover:not(:disabled) { filter: brightness(1.08); }
.public-primary:focus-visible, .public-participant:focus-visible, .public-status button:focus-visible, select:focus-visible, input:focus-visible { outline: 3px solid #fff; outline-offset: 3px; }

.public-context { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 3px 0 14px; color: #d7c9b5; font-size: .74rem; text-transform: capitalize; }
.public-context strong { border: 1px solid #48bd63; border-radius: 999px; color: #58da75; padding: 6px 9px; font-size: .7rem; white-space: nowrap; }
.public-participants { display: grid; gap: 9px; }
.public-participant {
  --participant-bg: none;
  position: relative; isolation: isolate; width: 100%; min-height: 58px; display: flex; align-items: center; gap: 12px;
  border: 1px solid #9d7134; border-radius: 12px; background: #090909 var(--participant-bg) center / cover;
  color: #fff; padding: 8px 12px; text-align: left; font-weight: 800; overflow: hidden;
}
.public-participant::before { content: ""; position: absolute; z-index: -1; inset: 0; background: linear-gradient(90deg, rgba(5,5,5,.96) 15%, rgba(5,5,5,.55)); }
.public-participant.selected { border-color: #ffd071; box-shadow: inset 0 0 24px rgba(255, 176, 55, .45), 0 0 15px rgba(255, 176, 55, .42); }
.public-participant b { margin-left: auto; display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: #efb755; color: #1a1106; font-size: 1.2rem; }
.public-number { display: grid; place-items: center; flex: 0 0 38px; height: 38px; border: 1px solid #d5a555; border-radius: 50%; color: #efc477; font-family: Georgia, serif; }
.public-confirm { position: sticky; bottom: 8px; margin-top: 16px; }

.public-ranked, .public-criteria { display: grid; gap: 12px; }
.public-ranked select { min-height: 48px; border: 1px solid #96703a; border-radius: 10px; background: #0b0b0d; color: #fff; padding: 0 12px; }
.public-criteria { margin-top: 16px; border-top: 1px solid rgba(213, 165, 85, .35); padding-top: 14px; }
.public-criteria label > span { display: flex; justify-content: space-between; }
.public-criteria label strong { color: #efc477; }
.public-criteria input { width: 100%; accent-color: #dca54b; }

.public-status { flex: 1; display: grid; place-items: center; align-content: center; gap: 16px; text-align: center; padding: 28px 10px; }
.public-status > img { width: 92px; height: 92px; filter: drop-shadow(0 0 20px rgba(218, 157, 54, .68)); }
.public-status h2 { margin: 0; color: #f6efe4; font-size: 1.3rem; }
.public-status p { max-width: 36ch; margin: 0; color: #d4c9ba; line-height: 1.5; overflow-wrap: anywhere; }
.public-status button { width: 100%; min-height: 48px; margin-top: 16px; border: 1px solid #ffd477; border-radius: 10px; background: linear-gradient(#ffd477, #a9671e); color: #170f06; font-weight: 900; text-transform: uppercase; }

@media (min-width: 760px) {
  .public-vote-page { padding: 34px; background-image: url("/quasanremo/backgrounds/bg-public-desktop.png"); }
  .public-vote-card { min-height: calc(100vh - 68px); padding: 28px 24px 20px; }
  .public-brand img { height: 86px; }
  .public-participant { min-height: 64px; }
}

@media (prefers-reduced-motion: no-preference) {
  .public-participant, .public-primary { transition: border-color .18s ease, box-shadow .18s ease, filter .18s ease; }
}
```

- [ ] **Step 3: eseguire il test di logica dopo l'integrazione**

Run:

```powershell
cd frontend
npm test
```

Expected: 5 test PASS.

- [ ] **Step 4: commit**

```powershell
git add frontend/src/public-vote/PublicVotePage.tsx frontend/src/public-vote/public-vote.css
git commit -m "feat: add standalone public vote page"
```

### Task 4: Bootstrap separato e pulizia App

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: collegare la route dedicata nel bootstrap**

Sostituire `frontend/src/main.tsx` con:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

import { isPublicVotePath } from "./public-vote/publicVote";

async function bootstrap() {
  const { default: Root } = isPublicVotePath(window.location.pathname)
    ? await import("./public-vote/PublicVotePage")
    : await import("./App");

  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode><Root /></React.StrictMode>,
  );
}

void bootstrap();
```

- [ ] **Step 2: rendere `App` indipendente dal pubblico**

In `frontend/src/App.tsx`:

1. Aggiungere in cima:

```tsx
import "./styles.css";
import { publicVoteHref } from "./public-vote/publicVote";
```

2. Cambiare il tipo:

```ts
type AppView = "admin" | "judge" | "screen";
```

3. Eliminare `PublicCompetitionAccessRead`, `PublicState`, `emptyPublicState`, `PublicArea`, `RankedChoice` e `getPublicVoterToken`. Conservare `ParticipantChoices` e `CriteriaRating`, usati dall'area giudici.

4. Sostituire entrambi i vecchi link pubblici con:

```ts
`${window.location.origin}${publicVoteHref(selectedCompetitionId)}`
```

5. Rimuovere il pulsante `Pubblico` dal `.mode-switch`.

6. Sostituire il titolo con:

```tsx
{view === "admin" ? "Admin serata" : view === "judge" ? "Giudici" : "Schermo pubblico"}
```

7. Nel ramo principale, rimuovere soltanto l'apertura dedicata a `view === "public"`:

```tsx
{view === "public" ? (
  <PublicArea setMessage={setMessage} />
) : view === "judge" ? (
```

deve diventare:

```tsx
{view === "judge" ? (
  <JudgeArea setMessage={setMessage} />
) : view === "screen" ? (
  <ScreenArea setMessage={setMessage} />
) : (
  <section className="workspace">
```

Lasciare invariati il ramo admin già presente e le parentesi di chiusura esistenti.

8. Sostituire `initialViewFromUrl` con:

```ts
function initialViewFromUrl(): AppView {
  const view = new URLSearchParams(window.location.search).get("view");
  return view === "judge" || view === "screen" ? view : "admin";
}
```

- [ ] **Step 3: verificare test e build**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: 5 test PASS; `tsc && vite build` exit 0 senza errori.

- [ ] **Step 4: verificare che il vecchio pubblico incorporato non esista**

Run dalla root:

```powershell
if (Select-String -Path 'frontend\src\App.tsx' -Pattern 'function PublicArea|view === "public"|view=public') { throw 'Vista pubblica legacy ancora presente' }
```

Expected: exit 0.

- [ ] **Step 5: commit**

```powershell
git add frontend/src/main.tsx frontend/src/App.tsx
git commit -m "refactor: isolate public vote entry point"
```

### Task 5: Documentazione e verifica visiva

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `.tmp/public-vote-mobile.png` (non committente)
- Create: `.tmp/public-vote-desktop.png` (non committente)

- [ ] **Step 1: documentare l'URL pubblico**

In `README.md`, sotto l'elenco servizi, aggiungere:

```markdown
- Voto pubblico: http://localhost:5173/vote

Un link diretto usa `http://localhost:5173/vote?competitionId=<id>`; senza ID la pagina mostra il form di accesso.
```

In `AGENTS.md`, nella sezione frontend aggiungere:

```markdown
- `frontend/src/public-vote/`: entry point pubblico isolato, raggiungibile su `/vote`.
- I link diretti e i QR del voto pubblico devono usare `/vote?competitionId=<id>`.
- Il CSS Quasanremo del voto pubblico non deve modificare admin, giudici o schermo.
```

- [ ] **Step 2: eseguire la verifica automatica completa**

Run:

```powershell
cd frontend
npm test
npm run build
cd ..
docker compose build frontend
```

Expected: tutti i test PASS e entrambi i build exit 0.

- [ ] **Step 3: acquisire screenshot reali mobile e desktop**

Run dalla root:

```powershell
New-Item -ItemType Directory -Force '.tmp' | Out-Null
$npm = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev','--','--host','127.0.0.1' -WorkingDirectory "$PWD\frontend" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
& $edge --headless --disable-gpu --hide-scrollbars --window-size=390,844 --screenshot="$PWD\.tmp\public-vote-mobile.png" http://localhost:5173/vote
& $edge --headless --disable-gpu --hide-scrollbars --window-size=1440,1000 --screenshot="$PWD\.tmp\public-vote-desktop.png" http://localhost:5173/vote
Stop-Process -Id $npm.Id
```

Expected: due PNG non vuoti.

- [ ] **Step 4: confrontare gli screenshot**

Aprire con `view_image`:

- `C:\Users\r.scardigno\Desktop\Personal_Projects\contest_voting_platform\.tmp\public-vote-mobile.png`
- `C:\Users\r.scardigno\Desktop\Personal_Projects\contest_voting_platform\.tmp\public-vote-desktop.png`
- `C:\Users\r.scardigno\Desktop\quasanremo_assets\immagine_reference.png`

Verificare: logo non tagliato, contenuto leggibile a 390 px, CTA visibile, nessuna topbar admin, sfondo corretto per viewport, contrasto sufficiente e fedeltà alla variante B approvata. Correggere soltanto difetti osservati e rieseguire `npm run build` dopo ogni correzione.

- [ ] **Step 5: commit finale**

```powershell
git add README.md AGENTS.md
git commit -m "docs: document standalone public voting"
```

### Task 6: Verifica finale e indice

**Files:** nessuna modifica prevista.

- [ ] **Step 1: verificare il worktree e la suite**

Run:

```powershell
git status --short
cd frontend
npm test
npm run build
```

Expected: worktree pulito prima dei file ignorati; 5 test PASS; build exit 0.

- [ ] **Step 2: aggiornare il knowledge graph**

Eseguire `index_repository` in modalità `full` su:

```text
C:\Users\r.scardigno\Desktop\Personal_Projects\contest_voting_platform
```

Expected: stato `indexed`, poi `index_status` = `ready`.

- [ ] **Step 3: riepilogare il risultato**

Riportare URL `/vote`, test, build, screenshot confrontati e l'eventuale limite residuo: i cinque fondali sono ciclici finché il dominio non avrà immagini partecipante personalizzate.
