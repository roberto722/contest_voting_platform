import { useEffect, useRef, useState, type CSSProperties } from "react";

import {
  buildVotePayload,
  clearVoterSession,
  getVotingState,
  loadVoterSession,
  participantBackdrop,
  saveVoterSession,
  voterAuthHeaders,
  type PublicVoteMethod,
  type VoterSession,
  type VotingState,
} from "./publicVote";
import "./public-vote.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// ---------- types ----------

type Competition = {
  id: string;
  name: string;
  description: string | null;
  public_voting_enabled: boolean;
  public_vote_method: PublicVoteMethod;
  max_votes_per_user: number;
  status: string;
};

type Participant = { id: string; display_name: string; active: boolean };
type Criterion = { id: string; name: string; min_score: number; max_score: number; active: boolean };
type VotingSession = { id: string; status: "open" | "closed" | "cancelled" };

type CompetitionEntry = {
  competition: Competition;
  votingState: VotingState;
  voted: boolean;
};

type Phase =
  | "restoring"    // checking localStorage session on mount
  | "login"        // show login form
  | "logging-in"   // POST /api/vote/access in progress
  | "list"         // show competition list
  | "loading-comp" // loading competition detail before voting
  | "voting"       // voting on a specific competition
  | "submitting";  // submit in progress

// ---------- api ----------

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

// ---------- shared UI ----------

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

function UserBar({ displayName, onLogout }: { displayName: string; onLogout: () => void }) {
  return (
    <div className="public-user-bar">
      <span className="public-user-name">👤 {displayName}</span>
      <button className="public-logout-btn" type="button" onClick={onLogout}>
        Esci
      </button>
    </div>
  );
}

// ---------- main ----------

export default function PublicVotePage() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlEventId = urlParams.get("eventId") ?? "";

  const [phase, setPhase] = useState<Phase>("restoring");
  const [session, setSession] = useState<VoterSession | null>(null);
  const [eventIdInput, setEventIdInput] = useState(urlEventId);
  const [accessCodeInput, setAccessCodeInput] = useState("");
  const [loginError, setLoginError] = useState("");

  const [entries, setEntries] = useState<CompetitionEntry[]>([]);
  const [activeCompetitionId, setActiveCompetitionId] = useState<string | null>(null);

  const [participants, setParticipants] = useState<Participant[]>([]);
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [votingSessions, setVotingSessions] = useState<VotingSession[]>([]);
  const [selfExcludedId, setSelfExcludedId] = useState<string | null>(null);
  const [selectedParticipantId, setSelectedParticipantId] = useState("");
  const [rankedParticipantIds, setRankedParticipantIds] = useState<string[]>([]);
  const [criteriaScores, setCriteriaScores] = useState<Record<string, number>>({});
  const [voteError, setVoteError] = useState("");

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── mount: restore session from localStorage ─────────────────────────────────
  useEffect(() => {
    void restoreSession();
  }, []);

  useEffect(() => () => stopPolling(), []);

  async function restoreSession() {
    const stored = loadVoterSession();
    if (!stored) { setPhase("login"); return; }
    try {
      const data = await publicApi<{ voter_account_id: string; display_name: string; access_token: string }>(
        `/api/vote/access?token=${encodeURIComponent(stored.accessToken)}`
      );
      const restored: VoterSession = {
        voterAccountId: data.voter_account_id,
        displayName: data.display_name,
        accessToken: data.access_token,
        eventId: stored.eventId,
      };
      setSession(restored);
      await loadCompetitions(restored);
    } catch {
      clearVoterSession();
      setPhase("login");
    }
  }

  // ── login ─────────────────────────────────────────────────────────────────────
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    const eventId = eventIdInput.trim();
    const code = accessCodeInput.trim().toUpperCase();
    if (!eventId || !code) return;
    setPhase("logging-in");
    setLoginError("");
    try {
      const data = await publicApi<{ voter_account_id: string; display_name: string; access_token: string }>(
        "/api/vote/access",
        { method: "POST", body: JSON.stringify({ event_id: eventId, access_code: code }) }
      );
      const newSession: VoterSession = {
        voterAccountId: data.voter_account_id,
        displayName: data.display_name,
        accessToken: data.access_token,
        eventId,
      };
      saveVoterSession(newSession);
      setSession(newSession);
      setAccessCodeInput("");
      await loadCompetitions(newSession);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Codice non valido");
      setPhase("login");
    }
  }

  // ── logout ────────────────────────────────────────────────────────────────────
  function handleLogout() {
    stopPolling();
    clearVoterSession();
    setSession(null);
    setEntries([]);
    setActiveCompetitionId(null);
    setVoteError("");
    setPhase("login");
  }

  // ── load competition list ─────────────────────────────────────────────────────
  async function loadCompetitions(sess: VoterSession) {
    setPhase("list");
    const comps = await publicApi<Competition[]>(`/api/events/${sess.eventId}/competitions`);
    const votable = comps.filter((c) => c.public_voting_enabled);
    const sessionLists = await Promise.all(
      votable.map((c) =>
        publicApi<VotingSession[]>(`/api/competitions/${c.id}/voting-sessions`).catch(() => [])
      )
    );
    setEntries(
      votable.map((c, i) => ({
        competition: c,
        votingState: getVotingState(sessionLists[i]),
        voted: false,
      }))
    );
  }

  // ── polling per aggiornare lo stato di una competizione ──────────────────────
  function startPolling(competitionId: string) {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const slist = await publicApi<VotingSession[]>(
          `/api/competitions/${competitionId}/voting-sessions`
        );
        setVotingSessions(slist);
        setEntries((prev) =>
          prev.map((e) =>
            e.competition.id === competitionId ? { ...e, votingState: getVotingState(slist) } : e
          )
        );
      } catch { /* ignore */ }
    }, 5000);
  }

  function stopPolling() {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  // ── avvia voto su una competizione ───────────────────────────────────────────
  async function startVoting(competitionId: string, sess: VoterSession) {
    setPhase("loading-comp");
    setVoteError("");
    setActiveCompetitionId(competitionId);
    try {
      const [parts, crit, slist, selfExcl] = await Promise.all([
        publicApi<Participant[]>(`/api/competitions/${competitionId}/participants`),
        publicApi<Criterion[]>(`/api/competitions/${competitionId}/public-criteria`),
        publicApi<VotingSession[]>(`/api/competitions/${competitionId}/voting-sessions`),
        publicApi<{ excluded_participant_id: string | null }>(
          `/api/competitions/${competitionId}/public-votes/self-exclusion`,
          { headers: voterAuthHeaders(sess) }
        ).catch(() => ({ excluded_participant_id: null })),
      ]);
      const activeParts = parts.filter((p) => p.active && p.id !== selfExcl.excluded_participant_id);
      const activeCrit = crit.filter((c) => c.active);
      const entry = entries.find((e) => e.competition.id === competitionId);
      const maxVotes = entry?.competition.max_votes_per_user ?? 1;

      setParticipants(activeParts);
      setCriteria(activeCrit);
      setVotingSessions(slist);
      setSelfExcludedId(selfExcl.excluded_participant_id);
      setSelectedParticipantId(activeParts[0]?.id ?? "");
      setRankedParticipantIds(activeParts.slice(0, maxVotes).map((p) => p.id));
      setCriteriaScores(Object.fromEntries(activeCrit.map((c) => [c.id, c.min_score])));
      setPhase("voting");
      startPolling(competitionId);
    } catch (err) {
      setVoteError(err instanceof Error ? err.message : "Errore caricamento");
      setPhase("list");
    }
  }

  // ── submit voto ───────────────────────────────────────────────────────────────
  async function submitVote() {
    if (!session || !activeCompetitionId) return;
    const entry = entries.find((e) => e.competition.id === activeCompetitionId);
    if (!entry) return;
    setPhase("submitting");
    setVoteError("");
    try {
      const payload = buildVotePayload(entry.competition.public_vote_method, {
        participantId: selectedParticipantId,
        rankedParticipantIds,
        ratings: criteria.map((c) => ({
          criterion_id: c.id,
          score: criteriaScores[c.id] ?? c.min_score,
        })),
      });
      await publicApi(`/api/competitions/${activeCompetitionId}/public-votes`, {
        method: "POST",
        headers: voterAuthHeaders(session),
        body: JSON.stringify(payload),
      });
      setEntries((prev) =>
        prev.map((e) => (e.competition.id === activeCompetitionId ? { ...e, voted: true } : e))
      );
      stopPolling();
      setActiveCompetitionId(null);
      setPhase("list");
    } catch (err) {
      setVoteError(err instanceof Error ? err.message : "Errore invio voto");
      setPhase("voting");
    }
  }

  function backToList() {
    stopPolling();
    setActiveCompetitionId(null);
    setVoteError("");
    setPhase("list");
  }

  // ── derived ───────────────────────────────────────────────────────────────────
  const activeEntry = entries.find((e) => e.competition.id === activeCompetitionId) ?? null;
  const currentVotingState = getVotingState(votingSessions);
  const canSubmit =
    activeEntry?.competition.public_vote_method === "ranked_choice"
      ? rankedParticipantIds.some(Boolean)
      : Boolean(selectedParticipantId);
  const allVoted =
    entries.length > 0 && entries.every((e) => e.voted || e.votingState !== "open");

  // ── render ────────────────────────────────────────────────────────────────────
  return (
    <main className="public-vote-page">
      <div className="public-vote-card">

        {/* ── RESTORING / LOADING-COMP / SUBMITTING ── */}
        {(phase === "restoring" || phase === "loading-comp" || phase === "submitting") && (
          <>
            <BrandHeader />
            <StatusView
              icon="waiting"
              title={
                phase === "submitting"
                  ? "Registrazione del voto in corso"
                  : "Caricamento in corso…"
              }
              text="Attendi qualche secondo."
            />
          </>
        )}

        {/* ── LOGIN ── */}
        {(phase === "login" || phase === "logging-in") && (
          <>
            <BrandHeader title="Accedi per votare" subtitle="Inserisci il tuo codice personale" />
            <form className="public-access-form" onSubmit={(e) => void handleLogin(e)}>
              <label>
                <span>ID Evento</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/vote.svg" alt="" />
                  <input
                    value={eventIdInput}
                    onChange={(e) => setEventIdInput(e.target.value)}
                    placeholder="ID dell'evento"
                    required
                    readOnly={Boolean(urlEventId)}
                    aria-label="ID Evento"
                  />
                </span>
              </label>
              <label>
                <span>Codice di accesso</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/lock.svg" alt="" />
                  <input
                    value={accessCodeInput}
                    onChange={(e) => setAccessCodeInput(e.target.value.toUpperCase())}
                    placeholder="Es. ABCD1234"
                    autoComplete="off"
                    autoCapitalize="characters"
                    required
                    aria-label="Codice di accesso"
                  />
                </span>
              </label>
              {loginError && (
                <p className="public-error" role="alert">{loginError}</p>
              )}
              <button className="public-primary" type="submit" disabled={phase === "logging-in"}>
                {phase === "logging-in" ? "Accesso in corso…" : "Entra"}
              </button>
            </form>
          </>
        )}

        {/* ── COMPETITION LIST ── */}
        {phase === "list" && session && (
          <>
            <BrandHeader title="Le tue competizioni" />
            <UserBar displayName={session.displayName} onLogout={handleLogout} />

            {voteError && (
              <p className="public-error" role="alert">{voteError}</p>
            )}

            {allVoted && (
              <StatusView
                icon="success"
                title="Hai votato in tutte le competizioni aperte!"
                text="Grazie per la partecipazione."
              />
            )}

            <div className="public-competition-list">
              {entries.length === 0 && (
                <StatusView
                  icon="waiting"
                  title="Nessuna competizione disponibile"
                  text="Le competizioni con voto pubblico appariranno qui."
                />
              )}
              {entries.map((entry) => (
                <div
                  key={entry.competition.id}
                  className={[
                    "public-comp-card",
                    entry.voted ? "comp-voted" : "",
                    entry.votingState === "open" ? "comp-open" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <div className="comp-card-header">
                    <span className="comp-card-name">{entry.competition.name}</span>
                    <span className={`comp-card-badge badge-${entry.votingState}`}>
                      {entry.votingState === "open"
                        ? "🟢 Aperta"
                        : entry.votingState === "closed"
                        ? "🔴 Chiusa"
                        : "⏳ In attesa"}
                    </span>
                  </div>
                  {entry.competition.description && (
                    <p className="comp-card-desc">{entry.competition.description}</p>
                  )}
                  <div className="comp-card-footer">
                    {entry.voted ? (
                      <span className="comp-voted-badge">✓ Voto registrato</span>
                    ) : entry.votingState === "open" ? (
                      <button
                        className="public-primary"
                        type="button"
                        onClick={() => void startVoting(entry.competition.id, session)}
                      >
                        Vota ora →
                      </button>
                    ) : (
                      <span className="comp-unavailable">Non disponibile</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── VOTING ── */}
        {phase === "voting" && activeEntry && session && (
          <>
            <BrandHeader title="Esprimi il tuo voto" subtitle={activeEntry.competition.name} />
            <UserBar displayName={session.displayName} onLogout={handleLogout} />

            {voteError && <p className="public-error" role="alert">{voteError}</p>}

            {currentVotingState !== "open" ? (
              <StatusView
                icon={currentVotingState === "waiting" ? "waiting" : "closed"}
                title={
                  currentVotingState === "waiting"
                    ? "La votazione non è ancora aperta"
                    : "La votazione è chiusa"
                }
                text={
                  currentVotingState === "waiting"
                    ? "Attendi l'annuncio del presentatore."
                    : "Grazie per aver partecipato."
                }
                action="Torna alle competizioni"
                onAction={backToList}
              />
            ) : (
              <>
                {selfExcludedId && (
                  <p className="public-self-note">
                    ℹ️ Sei un partecipante — non puoi votare te stesso.
                  </p>
                )}

                {activeEntry.competition.public_vote_method !== "ranked_choice" ? (
                  <div className="public-participants">
                    {participants.map((p, index) => (
                      <button
                        aria-pressed={p.id === selectedParticipantId}
                        className={
                          p.id === selectedParticipantId
                            ? "public-participant selected"
                            : "public-participant"
                        }
                        key={p.id}
                        onClick={() => setSelectedParticipantId(p.id)}
                        style={
                          {
                            "--participant-bg": `url(${participantBackdrop(index)})`,
                          } as CSSProperties
                        }
                        type="button"
                      >
                        <span className="public-number">{String(index + 1).padStart(2, "0")}</span>
                        <span>{p.display_name}</span>
                        {p.id === selectedParticipantId ? <b aria-hidden="true">✓</b> : null}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="public-ranked">
                    {rankedParticipantIds.map((pid, index) => (
                      <label key={index}>
                        <span>Posizione {index + 1}</span>
                        <select
                          value={pid}
                          onChange={(e) => {
                            const next = [...rankedParticipantIds];
                            next[index] = e.target.value;
                            setRankedParticipantIds(next);
                          }}
                        >
                          <option value="">Seleziona</option>
                          {participants.map((p) => (
                            <option
                              disabled={
                                rankedParticipantIds.includes(p.id) && pid !== p.id
                              }
                              key={p.id}
                              value={p.id}
                            >
                              {p.display_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                )}

                {activeEntry.competition.public_vote_method === "criteria_rating" && (
                  <div className="public-criteria">
                    {criteria.map((c) => (
                      <label key={c.id}>
                        <span>
                          {c.name}
                          <strong>{criteriaScores[c.id] ?? c.min_score}</strong>
                        </span>
                        <input
                          type="range"
                          min={c.min_score}
                          max={c.max_score}
                          value={criteriaScores[c.id] ?? c.min_score}
                          onChange={(e) =>
                            setCriteriaScores((cur) => ({
                              ...cur,
                              [c.id]: Number(e.target.value),
                            }))
                          }
                        />
                      </label>
                    ))}
                  </div>
                )}

                <div className="public-vote-actions">
                  <button className="public-secondary" type="button" onClick={backToList}>
                    ← Torna alle competizioni
                  </button>
                  <button
                    className="public-primary public-confirm"
                    disabled={!canSubmit}
                    onClick={() => void submitVote()}
                    type="button"
                  >
                    Conferma voto
                  </button>
                </div>
              </>
            )}
          </>
        )}

      </div>
    </main>
  );
}
