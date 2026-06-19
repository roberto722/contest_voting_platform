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
  const token =
    typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(key, token);
  return token;
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

export default function PublicVotePage() {
  const queryCompetitionId =
    new URLSearchParams(window.location.search).get("competitionId") ?? "";
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
        activeParticipants
          .slice(0, competition.max_votes_per_user)
          .map((participant) => participant.id),
      );
      setCriteriaScores(
        Object.fromEntries(activeCriteria.map((criterion) => [criterion.id, criterion.min_score])),
      );
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
      const payload = buildPublicVotePayload(
        getPublicVoterToken(),
        data.competition.public_vote_method,
        {
          participantId: selectedParticipantId,
          rankedParticipantIds,
          ratings: data.criteria.map((criterion) => ({
            criterion_id: criterion.id,
            score: criteriaScores[criterion.id] ?? criterion.min_score,
          })),
        },
      );
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
  const canSubmit =
    data?.competition.public_vote_method === "ranked_choice"
      ? rankedParticipantIds.some(Boolean)
      : Boolean(selectedParticipantId);

  return (
    <main className="public-vote-page">
      <div className="public-vote-card">
        {phase === "access" ? (
          <>
            <BrandHeader
              title="Accedi alla competizione"
              subtitle="Inserisci i dati ricevuti"
            />
            <form
              className="public-access-form"
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                void loadCompetition();
              }}
            >
              <label>
                <span>Codice competizione</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/vote.svg" alt="" />
                  <input
                    value={competitionId}
                    onChange={(event) => setCompetitionId(event.target.value)}
                    required
                  />
                </span>
              </label>
              <label>
                <span>PIN, se richiesto</span>
                <span className="public-field">
                  <img src="/quasanremo/icons/lock.svg" alt="" />
                  <input
                    value={pin}
                    onChange={(event) => setPin(event.target.value)}
                    inputMode="numeric"
                  />
                </span>
              </label>
              <button className="public-primary" type="submit">
                Entra
              </button>
            </form>
          </>
        ) : null}

        {phase === "loading" || phase === "submitting" ? (
          <>
            <BrandHeader />
            <StatusView
              icon="waiting"
              title={phase === "loading" ? "Caricamento competizione" : "Registrazione del voto"}
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
              action={retry === "submit" ? "Riprova" : "Modifica i dati"}
              onAction={() => (retry === "submit" ? void submitVote() : setPhase("access"))}
            />
          </>
        ) : null}

        {phase === "success" ? (
          <>
            <BrandHeader />
            <StatusView
              icon="success"
              title="Voto registrato!"
              text="Grazie per aver partecipato."
              action="Torna all'accesso"
              onAction={reset}
            />
          </>
        ) : null}

        {phase === "ready" && data && votingState !== "open" ? (
          <>
            <BrandHeader />
            <StatusView
              icon={votingState === "waiting" ? "waiting" : "closed"}
              title={
                votingState === "waiting"
                  ? "La votazione non è ancora aperta"
                  : "La votazione è chiusa"
              }
              text={
                votingState === "waiting"
                  ? "Attendi l'annuncio del presentatore."
                  : "Grazie per aver partecipato."
              }
              action="Torna all'accesso"
              onAction={reset}
            />
          </>
        ) : null}

        {phase === "ready" && data && votingState === "open" ? (
          <>
            <BrandHeader title="Scegli il tuo artista" subtitle={data.competition.name} />
            <div className="public-context">
              <span>{data.competition.public_vote_method.replace(/_/g, " ")}</span>
              <strong>● Votazione aperta</strong>
            </div>
            {data.competition.public_vote_method !== "ranked_choice" ? (
              <div className="public-participants">
                {data.participants.map((participant, index) => (
                  <button
                    aria-pressed={participant.id === selectedParticipantId}
                    className={
                      participant.id === selectedParticipantId
                        ? "public-participant selected"
                        : "public-participant"
                    }
                    key={participant.id}
                    onClick={() => setSelectedParticipantId(participant.id)}
                    style={
                      { "--participant-bg": `url(${participantBackdrop(index)})` } as CSSProperties
                    }
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
                  <label key={index}>
                    <span>Posizione {index + 1}</span>
                    <select
                      value={participantId}
                      onChange={(event) => {
                        const next = [...rankedParticipantIds];
                        next[index] = event.target.value;
                        setRankedParticipantIds(next);
                      }}
                    >
                      <option value="">Seleziona</option>
                      {data.participants.map((participant) => (
                        <option
                          disabled={
                            rankedParticipantIds.includes(participant.id) &&
                            participantId !== participant.id
                          }
                          key={participant.id}
                          value={participant.id}
                        >
                          {participant.display_name}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            )}
            {data.competition.public_vote_method === "criteria_rating" ? (
              <div className="public-criteria">
                {data.criteria.map((criterion) => (
                  <label key={criterion.id}>
                    <span>
                      {criterion.name}
                      <strong>{criteriaScores[criterion.id] ?? criterion.min_score}</strong>
                    </span>
                    <input
                      type="range"
                      min={criterion.min_score}
                      max={criterion.max_score}
                      value={criteriaScores[criterion.id] ?? criterion.min_score}
                      onChange={(event) =>
                        setCriteriaScores((current) => ({
                          ...current,
                          [criterion.id]: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            ) : null}
            <button
              className="public-primary public-confirm"
              disabled={!canSubmit}
              onClick={() => void submitVote()}
              type="button"
            >
              Conferma voto
            </button>
          </>
        ) : null}
      </div>
    </main>
  );
}
