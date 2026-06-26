import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";

import { participantBackdrop } from "../public-vote/publicVote";
import EmojiSlider from "../components/EmojiSlider";
import "../public-vote/public-vote.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type CompetitionAccess = {
  id: string;
  name: string;
  status: string;
};

type JudgeAccessRead = {
  judge_id: string;
  display_name: string;
  competitions: CompetitionAccess[];
};

type CompetitionRead = {
  id: string;
  name: string;
  judge_voting_enabled: boolean;
};

type ParticipantRead = {
  id: string;
  display_name: string;
  active: boolean;
};

type CriterionRead = {
  id: string;
  name: string;
  min_score: number;
  max_score: number;
};

type VotingSessionRead = {
  id: string;
  status: "open" | "closed" | "cancelled";
};

type JudgeVoteStatusRead = {
  competition_id: string;
  judge_id: string;
  voting_session_id: string | null;
  voting_session_status: string | null;
  total_participants: number;
  voted_participants: number;
  completed: boolean;
};

type JudgeVoteDetailRead = {
  id: string;
  participant_id: string;
  criterion_votes: { criterion_id: string; score: number }[];
};

type SavedJudgeVote = {
  scores: Record<string, number>;
};

type Phase = "access" | "loading" | "ready" | "submitting" | "success" | "error";

async function judgeApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? response.statusText);
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

function BrandHeader({ title, subtitle }: { title?: string; subtitle?: string }) {
  return (
    <header className="public-brand">
      <img
        src="/quasanremo/brand/logo-rectangular-transparent.png"
        alt="Quasanremo International"
      />
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

export default function JudgePage() {
  const [judgeId, setJudgeId] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [access, setAccess] = useState<JudgeAccessRead | null>(null);

  const [selectedCompetitionId, setSelectedCompetitionId] = useState("");
  const [competition, setCompetition] = useState<CompetitionRead | null>(null);
  const [participants, setParticipants] = useState<ParticipantRead[]>([]);
  const [judgeCriteria, setJudgeCriteria] = useState<CriterionRead[]>([]);
  const [sessions, setSessions] = useState<VotingSessionRead[]>([]);
  const [status, setStatus] = useState<JudgeVoteStatusRead | null>(null);
  const [savedVotes, setSavedVotes] = useState<Record<string, SavedJudgeVote>>({});
  const [competitionStatuses, setCompetitionStatuses] = useState<Record<string, JudgeVoteStatusRead>>({});

  const [selectedParticipantId, setSelectedParticipantId] = useState("");
  const [criteriaScores, setCriteriaScores] = useState<Record<string, number>>({});

  const [phase, setPhase] = useState<Phase>("access");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState<"access" | "submit">("access");

  async function loginJudge() {
    if (!judgeId.trim() || !accessCode.trim()) return;
    setPhase("loading");
    setError("");
    try {
      const res = await judgeApi<JudgeAccessRead>("/api/judge-access", {
        method: "POST",
        body: JSON.stringify({ judge_id: judgeId, access_code: accessCode }),
      });
      setAccess(res);

      // Load statuses for all competitions
      const statuses: Record<string, JudgeVoteStatusRead> = {};
      await Promise.all(
        res.competitions.map(async (comp) => {
          try {
            statuses[comp.id] = await judgeApi<JudgeVoteStatusRead>(
              `/api/competitions/${comp.id}/judge-votes/status?judge_id=${res.judge_id}&access_code=${encodeURIComponent(
                accessCode
              )}`
            );
          } catch {
            // Fallback empty status
            statuses[comp.id] = {
              competition_id: comp.id,
              judge_id: res.judge_id,
              voting_session_id: null,
              voting_session_status: null,
              total_participants: 0,
              voted_participants: 0,
              completed: false,
            };
          }
        })
      );
      setCompetitionStatuses(statuses);
      setPhase("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Errore inatteso");
      setRetry("access");
      setPhase("error");
    }
  }

  async function loadCompetition(compId: string) {
    if (!access) return;
    setPhase("loading");
    setError("");
    try {
      const [compData, participantsData, criteriaData, sessionsData] = await Promise.all([
        judgeApi<CompetitionRead>(`/api/competitions/${compId}`),
        judgeApi<ParticipantRead[]>(`/api/competitions/${compId}/participants`),
        judgeApi<CriterionRead[]>(`/api/competitions/${compId}/judge-criteria`),
        judgeApi<VotingSessionRead[]>(`/api/competitions/${compId}/voting-sessions`),
      ]);

      const [statusData, savedVotesList] = compData.judge_voting_enabled
        ? await Promise.all([
            judgeApi<JudgeVoteStatusRead>(
              `/api/competitions/${compId}/judge-votes/status?judge_id=${access.judge_id}&access_code=${encodeURIComponent(
                accessCode
              )}`
            ),
            judgeApi<JudgeVoteDetailRead[]>(
              `/api/competitions/${compId}/judge-votes?judge_id=${access.judge_id}&access_code=${encodeURIComponent(
                accessCode
              )}`
            ),
          ])
        : [
            {
              competition_id: compId,
              judge_id: access.judge_id,
              voting_session_id: null,
              voting_session_status: null,
              total_participants: 0,
              voted_participants: 0,
              completed: false,
            },
            [],
          ];

      const activeParticipants = participantsData.filter((p) => p.active);
      const mappedSavedVotes: Record<string, SavedJudgeVote> = {};
      for (const vote of savedVotesList) {
        mappedSavedVotes[vote.participant_id] = {
          scores: Object.fromEntries(vote.criterion_votes.map((cv) => [cv.criterion_id, cv.score])),
        };
      }

      setCompetition(compData);
      setParticipants(activeParticipants);
      setJudgeCriteria(criteriaData);
      setSessions(sessionsData);
      setStatus(statusData);
      setSavedVotes(mappedSavedVotes);
      setSelectedCompetitionId(compId);

      // Find first pending participant or select the first one
      const pending = activeParticipants.find((p) => !mappedSavedVotes[p.id])?.id;
      const initialPartId = pending ?? activeParticipants[0]?.id ?? "";
      setSelectedParticipantId(initialPartId);

      // Initialize criteria scores
      const initialScores: Record<string, number> = {};
      const savedScores = mappedSavedVotes[initialPartId]?.scores ?? {};
      for (const c of criteriaData) {
        initialScores[c.id] = savedScores[c.id] ?? c.min_score;
      }
      setCriteriaScores(initialScores);
      setPhase("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Errore inatteso");
      setRetry("access");
      setPhase("error");
    }
  }

  async function submitVote() {
    if (!access || !competition) return;
    setPhase("submitting");
    setError("");
    try {
      await judgeApi(`/api/competitions/${competition.id}/judge-votes`, {
        method: "POST",
        body: JSON.stringify({
          judge_id: access.judge_id,
          access_code: accessCode,
          participant_id: selectedParticipantId,
          criteria: judgeCriteria.map((c) => ({
            criterion_id: c.id,
            score: criteriaScores[c.id] ?? c.min_score,
          })),
        }),
      });

      const [statusData, savedVotesList] = await Promise.all([
        judgeApi<JudgeVoteStatusRead>(
          `/api/competitions/${competition.id}/judge-votes/status?judge_id=${access.judge_id}&access_code=${encodeURIComponent(
            accessCode
          )}`
        ),
        judgeApi<JudgeVoteDetailRead[]>(
          `/api/competitions/${competition.id}/judge-votes?judge_id=${access.judge_id}&access_code=${encodeURIComponent(
            accessCode
          )}`
        ),
      ]);

      const mappedSavedVotes: Record<string, SavedJudgeVote> = {};
      for (const vote of savedVotesList) {
        mappedSavedVotes[vote.participant_id] = {
          scores: Object.fromEntries(vote.criterion_votes.map((cv) => [cv.criterion_id, cv.score])),
        };
      }

      setStatus(statusData);
      setSavedVotes(mappedSavedVotes);
      setCompetitionStatuses((current) => ({ ...current, [competition.id]: statusData }));
      setPhase("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Errore inatteso");
      setRetry("submit");
      setPhase("error");
    }
  }

  function handleParticipantSelect(participantId: string) {
    setSelectedParticipantId(participantId);
    const saved = savedVotes[participantId];
    const newScores: Record<string, number> = {};
    for (const c of judgeCriteria) {
      newScores[c.id] = saved?.scores[c.id] ?? c.min_score;
    }
    setCriteriaScores(newScores);
  }

  function isVoteDirty(): boolean {
    const saved = savedVotes[selectedParticipantId];
    if (!saved) return true;
    for (const c of judgeCriteria) {
      const currentVal = criteriaScores[c.id] ?? c.min_score;
      const savedVal = saved.scores[c.id];
      if (savedVal === undefined || currentVal !== savedVal) {
        return true;
      }
    }
    return false;
  }

  function formatJudgeProgress(s: JudgeVoteStatusRead | undefined): string {
    if (!s) return "0/0";
    return `${s.voted_participants}/${s.total_participants} ${s.completed ? "(completo)" : ""}`;
  }

  useEffect(() => {
    if (phase !== "ready" || !selectedCompetitionId) return;

    const interval = setInterval(async () => {
      try {
        const sessionsData = await judgeApi<VotingSessionRead[]>(
          `/api/competitions/${selectedCompetitionId}/voting-sessions`
        );
        setSessions(sessionsData);
      } catch (err) {
        console.error("Errore nel polling delle sessioni:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [phase, selectedCompetitionId]);

  const openSession = sessions.find((s) => s.status === "open");
  const isSessionOpen = Boolean(competition?.judge_voting_enabled && openSession);

  return (
    <main className="public-vote-page">
      <div className="public-vote-card">
        {phase === "access" ? (
          <>
            <BrandHeader title="Area Giudici" subtitle="Inserisci le credenziali di accesso" />
            <form
              className="public-access-form"
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                void loginJudge();
              }}
            >
              <label>
                <span>ID Giudice</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/vote.svg" alt="" />
                  <input value={judgeId} onChange={(e) => setJudgeId(e.target.value)} required />
                </span>
              </label>
              <label>
                <span>Codice Accesso</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/lock.svg" alt="" />
                  <input
                    value={accessCode}
                    onChange={(e) => setAccessCode(e.target.value)}
                    required
                    type="password"
                  />
                </span>
              </label>
              <button className="public-primary" type="submit">
                Accedi
              </button>
            </form>
          </>
        ) : null}

        {phase === "loading" || phase === "submitting" ? (
          <>
            <BrandHeader />
            <StatusView
              icon="waiting"
              title={phase === "loading" ? "Caricamento in corso..." : "Registrazione voto..."}
              text="Attendi qualche secondo."
            />
          </>
        ) : null}

        {phase === "error" ? (
          <>
            <BrandHeader />
            <StatusView
              icon="error"
              title="Si è verificato un errore"
              text={error}
              action={retry === "submit" ? "Riprova" : "Modifica credenziali"}
              onAction={() => {
                if (retry === "submit") {
                  void submitVote();
                } else {
                  setPhase("access");
                }
              }}
            />
          </>
        ) : null}

        {phase === "success" ? (
          <>
            <BrandHeader />
            <StatusView
              icon="success"
              title="Voto salvato con successo!"
              text="Il voto è stato caricato sul server."
              action="Continua"
              onAction={() => {
                // Find next pending or stay
                const pending = participants.find((p) => !savedVotes[p.id])?.id;
                if (pending) {
                  handleParticipantSelect(pending);
                }
                setPhase("ready");
              }}
            />
          </>
        ) : null}

        {phase === "ready" && access && !selectedCompetitionId ? (
          <>
            <BrandHeader title={`Ciao, ${access.display_name}`} subtitle="Competizioni assegnate" />
            <div className="public-access-form" style={{ gap: "10px", alignContent: "flex-start", marginTop: "10px" }}>
              {access.competitions.length ? (
                access.competitions.map((comp) => (
                  <button
                    key={comp.id}
                    className="public-participant"
                    style={{
                      minHeight: "72px",
                      padding: "12px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                      gap: "2px",
                      textAlign: "left",
                    }}
                    type="button"
                    onClick={() => void loadCompetition(comp.id)}
                  >
                    <strong style={{ color: "#efc477", fontSize: "1.05rem" }}>{comp.name}</strong>
                    <span style={{ color: "#ded7cc", fontSize: "0.85rem" }}>
                      Votati: {formatJudgeProgress(competitionStatuses[comp.id])}
                    </span>
                  </button>
                ))
              ) : (
                <p style={{ textAlign: "center", color: "#ded7cc" }}>Nessuna competizione assegnata.</p>
              )}

              <button
                className="public-primary"
                style={{
                  background: "transparent",
                  border: "1px solid #6f604c",
                  color: "#efc477",
                  marginTop: "24px",
                }}
                type="button"
                onClick={() => {
                  setAccess(null);
                  setPhase("access");
                }}
              >
                Disconnetti
              </button>
            </div>
          </>
        ) : null}

        {phase === "ready" && access && selectedCompetitionId && competition && !isSessionOpen ? (
          <>
            <BrandHeader title={competition.name} />
            <StatusView
              icon="closed"
              title="Votazione non attiva"
              text="La votazione non è aperta in questo momento."
              action="Indietro"
              onAction={() => setSelectedCompetitionId("")}
            />
          </>
        ) : null}

        {phase === "ready" && access && selectedCompetitionId && competition && isSessionOpen ? (
          <>
            <BrandHeader title="Valuta Artista" subtitle={competition.name} />
            <div className="public-context">
              <span>
                Completamento:{" "}
                {status ? `${status.voted_participants}/${status.total_participants}` : "0/0"}
              </span>
              <strong>● Votazione aperta</strong>
            </div>

            <div className="public-participants">
              {participants.map((p, idx) => (
                <button
                  key={p.id}
                  className={p.id === selectedParticipantId ? "public-participant selected" : "public-participant"}
                  onClick={() => handleParticipantSelect(p.id)}
                  style={{ "--participant-bg": `url(${participantBackdrop(idx)})` } as CSSProperties}
                  type="button"
                >
                  <span className="public-number">{String(idx + 1).padStart(2, "0")}</span>
                  <span>{p.display_name}</span>
                  {savedVotes[p.id] ? (
                    <b aria-hidden="true">✓</b>
                  ) : null}
                </button>
              ))}
            </div>

            {selectedParticipantId ? (
              <>
                <div className="public-criteria">
                  {judgeCriteria.map((c) => {
                    const val = criteriaScores[c.id] ?? c.min_score;
                    return (
                      <label key={c.id}>
                        <span>
                          <span>{c.name}</span>
                          <strong>
                            {val} / {c.max_score}
                          </strong>
                        </span>
                        <EmojiSlider
                          min={c.min_score}
                          max={c.max_score}
                          value={val}
                          onChange={(v) => {
                            setCriteriaScores((curr) => ({ ...curr, [c.id]: v }));
                          }}
                        />
                      </label>
                    );
                  })}
                </div>

                {isVoteDirty() ? (
                  <div
                    className="closed-state"
                    style={{
                      margin: "14px 0",
                      borderStyle: "dashed",
                      textAlign: "center",
                      borderRadius: "8px",
                      padding: "12px",
                      fontSize: "0.85rem",
                    }}
                  >
                    ⚠️ I voti inseriti o modificati per questo partecipante non sono validi finché non clicchi su "Salva voto".
                  </div>
                ) : (
                  <div
                    className="confirmation"
                    style={{
                      margin: "14px 0",
                      textAlign: "center",
                      borderRadius: "8px",
                      padding: "12px",
                      fontSize: "0.85rem",
                    }}
                  >
                    ✓ Voto caricato sul server.
                  </div>
                )}

                <button className="public-primary" onClick={submitVote} type="button">
                  Salva voto
                </button>
              </>
            ) : null}

            <button
              className="public-primary"
              style={{
                background: "transparent",
                border: "1px solid #6f604c",
                color: "#efc477",
                marginTop: "8px",
              }}
              type="button"
              onClick={() => setSelectedCompetitionId("")}
            >
              Indietro alle competizioni
            </button>
          </>
        ) : null}
      </div>
    </main>
  );
}
