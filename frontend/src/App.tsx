import { FormEvent, ReactNode, useEffect, useState } from "react";
import QRCode from "qrcode";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const websocketBaseUrl = apiBaseUrl.replace(/^http/, "ws");

type AppView = "admin" | "public" | "judge" | "screen";

type EventStatus = "draft" | "live" | "closed" | "archived";
type CompetitionStatus =
  | "draft"
  | "ready"
  | "voting_open"
  | "voting_closed"
  | "results_frozen"
  | "revealed";
type PublicVoteMethod = "single_choice" | "ranked_choice" | "criteria_rating";
type AccessMethod = "public_link" | "qr_pin" | "private_link";
type VotingSessionStatus = "open" | "closed" | "cancelled";
type ScreenMode =
  | "idle"
  | "show_qr"
  | "voting_open"
  | "countdown"
  | "show_results"
  | "reveal_ranking"
  | "show_podium"
  | "show_final_winners";

type EventRead = {
  id: string;
  name: string;
  description: string | null;
  status: EventStatus;
};

type CompetitionRead = {
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
  allow_vote_update: boolean;
  status: CompetitionStatus;
};

type ParticipantRead = {
  id: string;
  display_name: string;
  order_index: number;
  active: boolean;
};

type CriterionRead = {
  id: string;
  name: string;
  min_score: number;
  max_score: number;
  weight: number;
  active: boolean;
};

type JudgeRead = {
  id: string;
  event_id: string;
  name: string;
  display_name: string;
  active: boolean;
  assigned_competition_ids: string[];
};

type JudgeAccessCodeResetRead = {
  judge: JudgeRead;
  access_code: string;
};

type VotingSessionRead = {
  id: string;
  label: string | null;
  status: VotingSessionStatus;
  opened_at: string | null;
  closed_at: string | null;
};

type ResultEntry = {
  participant_id: string;
  display_name: string;
  rank: number;
  final_score: number;
  public_score: { normalized_score: number; raw_score: number };
  judge_score: { normalized_score: number; raw_score: number };
};

type ResultsRead = {
  results: ResultEntry[];
};

type SetupStepStatus = {
  step: string;
  completed: boolean;
  message: string;
};

type CompetitionSetupStatus = {
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

type PublicVoteSummaryRead = {
  competition_id: string;
  voting_session_id: string | null;
  total_votes: number;
  participants: { participant_id: string; display_name: string; vote_count: number }[];
};

type PublicCompetitionAccessRead = {
  competition_id: string;
  event_id: string;
  access_method: AccessMethod;
  access_granted: boolean;
};

type ScreenStateRead = {
  id: string;
  event_id: string;
  competition_id: string | null;
  mode: ScreenMode;
  payload_json: Record<string, unknown>;
};

type AuditLogRead = {
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

type AuditFilters = {
  query: string;
  actorType: string;
  entityType: string;
  action: string;
  pageSize: number;
  page: number;
};

type AdminTab =
  | "event"
  | "competition"
  | "participants"
  | "publicCriteria"
  | "judgeCriteria"
  | "judges"
  | "review"
  | "live"
  | "screen"
  | "results"
  | "logs";

type AdminStep = {
  id: AdminTab;
  label: string;
  disabled: boolean;
  reason?: string;
};

type JudgeAccessRead = {
  judge_id: string;
  display_name: string;
  competitions: CompetitionRead[];
};

type JudgeVoteStatusRead = {
  competition_id: string;
  judge_id: string;
  voting_session_id: string | null;
  voting_session_status: VotingSessionStatus | null;
  total_participants: number;
  voted_participants: number;
  completed: boolean;
};

type JudgeVoteDetailRead = {
  id: string;
  competition_id: string;
  participant_id: string;
  judge_id: string;
  voting_session_id: string;
  criterion_votes: { criterion_id: string; score: number }[];
};

type SavedJudgeVote = {
  votingSessionId: string;
  scores: Record<string, number>;
};

type AdminState = {
  events: EventRead[];
  competitions: CompetitionRead[];
  participants: ParticipantRead[];
  publicCriteria: CriterionRead[];
  judgeCriteria: CriterionRead[];
  judges: JudgeRead[];
  sessions: VotingSessionRead[];
  results: ResultsRead | null;
  setupStatus: CompetitionSetupStatus | null;
  screenState: ScreenStateRead | null;
  auditLogs: AuditLogRead[];
};

type PublicState = {
  competition: CompetitionRead | null;
  participants: ParticipantRead[];
  publicCriteria: CriterionRead[];
  sessions: VotingSessionRead[];
  selectedParticipantId: string;
  rankedParticipantIds: string[];
  criteriaScores: Record<string, number>;
  confirmation: string;
};

type JudgeState = {
  access: JudgeAccessRead | null;
  judgeId: string;
  accessCode: string;
  selectedCompetitionId: string;
  competition: CompetitionRead | null;
  participants: ParticipantRead[];
  judgeCriteria: CriterionRead[];
  sessions: VotingSessionRead[];
  status: JudgeVoteStatusRead | null;
  competitionStatuses: Record<string, JudgeVoteStatusRead>;
  savedVotes: Record<string, SavedJudgeVote>;
  selectedParticipantId: string;
  criteriaScores: Record<string, number>;
  confirmation: string;
};

type JudgeCredentialNotice = {
  judgeId: string;
  displayName: string;
  accessCode: string;
};

type ScreenAreaState = {
  eventId: string;
  activeEventId: string;
  connected: boolean;
  screenState: ScreenStateRead | null;
  competition: CompetitionRead | null;
  sessions: VotingSessionRead[];
  summary: PublicVoteSummaryRead | null;
  results: ResultsRead | null;
};

const emptyState: AdminState = {
  events: [],
  competitions: [],
  participants: [],
  publicCriteria: [],
  judgeCriteria: [],
  judges: [],
  sessions: [],
  results: null,
  setupStatus: null,
  screenState: null,
  auditLogs: [],
};

const emptyPublicState: PublicState = {
  competition: null,
  participants: [],
  publicCriteria: [],
  sessions: [],
  selectedParticipantId: "",
  rankedParticipantIds: [],
  criteriaScores: {},
  confirmation: "",
};

const emptyJudgeState: JudgeState = {
  access: null,
  judgeId: "",
  accessCode: "",
  selectedCompetitionId: "",
  competition: null,
  participants: [],
  judgeCriteria: [],
  sessions: [],
  status: null,
  competitionStatuses: {},
  savedVotes: {},
  selectedParticipantId: "",
  criteriaScores: {},
  confirmation: "",
};

const emptyScreenAreaState: ScreenAreaState = {
  eventId: "",
  activeEventId: "",
  connected: false,
  screenState: null,
  competition: null,
  sessions: [],
  summary: null,
  results: null,
};

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
  competition_results_final: "Risultati gia finali",
  missing_competitions: "Crea almeno una competizione",
};

const competitionStatusLabels: Record<string, string> = {
  draft: "Bozza",
  ready: "Pronto",
  voting_open: "Voto Aperto",
  voting_closed: "Voto Chiuso",
  results_frozen: "Congelato",
  revealed: "Svelato",
};

const eventStatusLabels: Record<string, string> = {
  draft: "Bozza",
  live: "Live",
  closed: "Chiuso",
  archived: "Archiviato",
};

async function api<T>(path: string, options?: RequestInit): Promise<T> {
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

export default function App() {
  const [state, setState] = useState<AdminState>(emptyState);
  const [view, setView] = useState<AppView>(initialViewFromUrl());
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [selectedCompetitionId, setSelectedCompetitionId] = useState<string>("");
  const [adminTab, setAdminTab] = useState<AdminTab>("event");
  const [deleteEventCandidate, setDeleteEventCandidate] = useState<EventRead | null>(null);
  const [deleteCompetitionCandidate, setDeleteCompetitionCandidate] = useState<CompetitionRead | null>(null);
  const [judgeCredentialNotice, setJudgeCredentialNotice] = useState<JudgeCredentialNotice | null>(null);
  const [auditFilters, setAuditFilters] = useState<AuditFilters>({
    query: "",
    actorType: "all",
    entityType: "all",
    action: "all",
    pageSize: 20,
    page: 1,
  });
  const [message, setMessage] = useState("Pronto");
  const selectedEvent = state.events.find((event) => event.id === selectedEventId);
  const selectedCompetition = state.competitions.find(
    (competition) => competition.id === selectedCompetitionId
  );
  const openSession = state.sessions.find((session) => session.status === "open");
  const isEventLive = selectedEvent?.status === "live";
  const configurationLocked = Boolean(selectedEvent && selectedEvent.status !== "draft");
  const activeParticipantsCount = state.participants.filter((participant) => participant.active).length;
  const setupReady = state.setupStatus?.is_ready ?? false;
  const canOpenVoting = state.setupStatus?.can_open_voting ?? false;
  const publicCriteriaRequired = Boolean(
    selectedCompetition?.public_voting_enabled &&
      selectedCompetition.public_vote_method === "criteria_rating"
  );
  const judgeSetupRequired = Boolean(selectedCompetition?.judge_voting_enabled);
  const adminSteps: AdminStep[] = [
    { id: "event", label: "Evento", disabled: false },
    { id: "competition", label: "Competizione", disabled: !selectedEvent, reason: "Seleziona evento" },
    {
      id: "participants",
      label: "Partecipanti",
      disabled: !selectedCompetition || configurationLocked,
      reason: configurationLocked ? "Evento live: configurazione bloccata" : "Crea competizione",
    },
    {
      id: "publicCriteria",
      label: "Criteri pubblico",
      disabled: !selectedCompetition || !publicCriteriaRequired || configurationLocked,
      reason: publicCriteriaRequired ? "Evento live: configurazione bloccata" : "Non richiesti",
    },
    {
      id: "judgeCriteria",
      label: "Criteri giudici",
      disabled: !selectedCompetition || !judgeSetupRequired || configurationLocked,
      reason: judgeSetupRequired ? "Evento live: configurazione bloccata" : "Non richiesti",
    },
    {
      id: "judges",
      label: "Giudici",
      disabled: !selectedEvent || configurationLocked,
      reason: configurationLocked ? "Evento live: configurazione bloccata" : "Seleziona evento",
    },
    { id: "review", label: "Review", disabled: !selectedCompetition, reason: "Crea competizione" },
    { id: "live", label: "Live", disabled: !selectedCompetition || !setupReady, reason: "Completa setup" },
    { id: "screen", label: "Schermo", disabled: !isEventLive, reason: "Porta evento live" },
    { id: "results", label: "Risultati", disabled: !isEventLive, reason: "Porta evento live" },
    { id: "logs", label: "Log", disabled: !selectedEvent, reason: "Seleziona evento" },
  ];
  const auditActorTypes = uniqueStringValues(state.auditLogs.map((log) => log.actor_type));
  const auditEntityTypes = uniqueStringValues(state.auditLogs.map((log) => log.entity_type));
  const auditActions = uniqueStringValues(state.auditLogs.map((log) => log.action));
  const filteredAuditLogs = state.auditLogs.filter((log) => {
    if (auditFilters.actorType !== "all" && log.actor_type !== auditFilters.actorType) return false;
    if (auditFilters.entityType !== "all" && log.entity_type !== auditFilters.entityType) return false;
    if (auditFilters.action !== "all" && log.action !== auditFilters.action) return false;
    return auditLogMatchesQuery(log, auditFilters.query);
  });
  const auditPageCount = Math.max(1, Math.ceil(filteredAuditLogs.length / auditFilters.pageSize));
  const auditPage = Math.min(auditFilters.page, auditPageCount);
  const pagedAuditLogs = filteredAuditLogs.slice(
    (auditPage - 1) * auditFilters.pageSize,
    auditPage * auditFilters.pageSize
  );

  async function run(action: () => Promise<void>, doneMessage: string) {
    try {
      await action();
      setMessage(doneMessage);
    } catch (error) {
      setMessage(`Errore: ${error instanceof Error ? error.message : "Errore inatteso"}`);
    }
  }

  async function loadEvents() {
    const events = await api<EventRead[]>("/api/events");
    setState((current) => ({ ...current, events }));
    if (!selectedEventId && events[0]) {
      setSelectedEventId(events[0].id);
    }
  }

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
      publicCriteria: [],
      judgeCriteria: [],
      sessions: [],
      results: null,
      screenState,
      auditLogs,
    }));
    setSelectedCompetitionId((current) =>
      current && competitions.some((competition) => competition.id === current)
        ? current
        : competitions[0]?.id ?? ""
    );
  }

  async function loadCompetitionData(competitionId: string) {
    const [participants, publicCriteria, judgeCriteria, sessions, results, setupStatus] = await Promise.all([
      api<ParticipantRead[]>(`/api/competitions/${competitionId}/participants`),
      api<CriterionRead[]>(`/api/competitions/${competitionId}/public-criteria`),
      api<CriterionRead[]>(`/api/competitions/${competitionId}/judge-criteria`),
      api<VotingSessionRead[]>(`/api/competitions/${competitionId}/voting-sessions`),
      api<ResultsRead>(`/api/competitions/${competitionId}/results`),
      api<CompetitionSetupStatus>(`/api/competitions/${competitionId}/setup-status`),
    ]);
    setState((current) => ({
      ...current,
      participants,
      publicCriteria,
      judgeCriteria,
      sessions,
      results,
      setupStatus,
    }));
  }

  useEffect(() => {
    void run(loadEvents, "Eventi caricati");
  }, []);

  useEffect(() => {
    if (selectedEventId) {
      void run(() => loadEventData(selectedEventId), "Evento caricato");
    }
  }, [selectedEventId]);

  useEffect(() => {
    if (selectedCompetitionId) {
      void run(() => loadCompetitionData(selectedCompetitionId), "Competizione caricata");
    }
  }, [selectedCompetitionId]);

  useEffect(() => {
    const currentStep = adminSteps.find((step) => step.id === adminTab);
    if (currentStep?.disabled) {
      setAdminTab("event");
    }
  }, [
    adminTab,
    selectedEventId,
    selectedCompetitionId,
    selectedEvent?.status,
    setupReady,
    publicCriteriaRequired,
    judgeSetupRequired,
  ]);

  function refreshSelectedEvent() {
    return selectedEventId ? loadEventData(selectedEventId) : loadEvents();
  }

  function refreshSelectedCompetition() {
    return selectedCompetitionId ? loadCompetitionData(selectedCompetitionId) : Promise.resolve();
  }

  async function createEvent(form: HTMLFormElement) {
    const data = new FormData(form);
    const event = await api<EventRead>("/api/events", {
      method: "POST",
      body: JSON.stringify({
        name: textValue(data, "name"),
        description: textValue(data, "description") || null,
      }),
    });
    form.reset();
    await loadEvents();
    setSelectedEventId(event.id);
  }

  async function deleteEvent(eventId: string) {
    await api(`/api/events/${eventId}`, { method: "DELETE" });
    const events = await api<EventRead[]>("/api/events");
    const nextEventId = events[0]?.id ?? "";
    setState((current) => ({
      ...current,
      events,
      competitions: [],
      participants: [],
      publicCriteria: [],
      judgeCriteria: [],
      judges: [],
      sessions: [],
      results: null,
      setupStatus: null,
      screenState: null,
      auditLogs: [],
    }));
    setSelectedEventId(nextEventId);
    setSelectedCompetitionId("");
    setDeleteEventCandidate(null);
    if (nextEventId) {
      await loadEventData(nextEventId);
    }
  }

  async function createCompetition(form: HTMLFormElement) {
    if (!selectedEventId) return;
    const data = new FormData(form);
    const competition = await api<CompetitionRead>(`/api/events/${selectedEventId}/competitions`, {
      method: "POST",
      body: JSON.stringify({
        name: textValue(data, "name"),
        public_voting_enabled: data.get("public_voting_enabled") === "on",
        judge_voting_enabled: data.get("judge_voting_enabled") === "on",
        public_vote_method: textValue(data, "public_vote_method"),
        public_weight: numberValue(data, "public_weight", 50),
        judge_weight: numberValue(data, "judge_weight", 50),
        access_method: textValue(data, "access_method"),
        access_pin: textValue(data, "access_pin") || null,
        max_votes_per_user: numberValue(data, "max_votes_per_user", 1),
        allow_vote_update: data.get("allow_vote_update") === "on",
      }),
    });
    form.reset();
    await loadEventData(selectedEventId);
    setSelectedCompetitionId(competition.id);
  }

  async function deleteCompetition(competitionId: string) {
    if (!selectedEventId) return;
    await api(`/api/competitions/${competitionId}`, { method: "DELETE" });
    const competitions = await api<CompetitionRead[]>(`/api/events/${selectedEventId}/competitions`);
    const nextCompetitionId =
      selectedCompetitionId === competitionId
        ? competitions[0]?.id ?? ""
        : competitions.some((competition) => competition.id === selectedCompetitionId)
          ? selectedCompetitionId
          : competitions[0]?.id ?? "";
    setState((current) => ({
      ...current,
      competitions,
      participants: [],
      publicCriteria: [],
      judgeCriteria: [],
      sessions: [],
      results: null,
      setupStatus: null,
    }));
    setSelectedCompetitionId(nextCompetitionId);
    setDeleteCompetitionCandidate(null);
    await loadEventData(selectedEventId);
    if (nextCompetitionId) {
      await loadCompetitionData(nextCompetitionId);
    }
  }

  async function createParticipant(form: HTMLFormElement) {
    if (!selectedCompetitionId) return;
    const data = new FormData(form);
    await api<ParticipantRead>(`/api/competitions/${selectedCompetitionId}/participants`, {
      method: "POST",
      body: JSON.stringify({
        name: slugValue(textValue(data, "display_name")),
        display_name: textValue(data, "display_name"),
        order_index: numberValue(data, "order_index", state.participants.length + 1),
      }),
    });
    form.reset();
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function createCriterion(form: HTMLFormElement, type: "public" | "judge") {
    if (!selectedCompetitionId) return;
    const data = new FormData(form);
    await api<CriterionRead>(
      `/api/competitions/${selectedCompetitionId}/${type === "public" ? "public" : "judge"}-criteria`,
      {
        method: "POST",
        body: JSON.stringify({
          name: textValue(data, "name"),
          min_score: numberValue(data, "min_score", 1),
          max_score: numberValue(data, "max_score", 10),
          weight: numberValue(data, "weight", 1),
        }),
      }
    );
    form.reset();
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function createJudge(form: HTMLFormElement) {
    if (!selectedEventId) return;
    const data = new FormData(form);
    const accessCode = textValue(data, "access_code");
    const judge = await api<JudgeRead>(`/api/events/${selectedEventId}/judges`, {
      method: "POST",
      body: JSON.stringify({
        name: slugValue(textValue(data, "display_name")),
        display_name: textValue(data, "display_name"),
        access_code: accessCode,
      }),
    });
    setJudgeCredentialNotice({
      judgeId: judge.id,
      displayName: judge.display_name,
      accessCode,
    });
    form.reset();
    await refreshSelectedEvent();
  }

  async function assignJudge(judgeId: string, competitionId: string) {
    await api(`/api/competitions/${competitionId}/judges/${judgeId}`, { method: "POST" });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function removeJudgeAssignment(judgeId: string, competitionId: string) {
    await api(`/api/competitions/${competitionId}/judges/${judgeId}`, { method: "DELETE" });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function toggleJudgeCompetition(judgeId: string, competitionId: string, isAssigned: boolean) {
    if (isAssigned) {
      await removeJudgeAssignment(judgeId, competitionId);
      return;
    }
    await assignJudge(judgeId, competitionId);
  }

  async function regenerateJudgeAccessCode(judgeId: string) {
    const reset = await api<JudgeAccessCodeResetRead>(
      `/api/judges/${judgeId}/access-code/regenerate`,
      { method: "POST" }
    );
    setJudgeCredentialNotice({
      judgeId: reset.judge.id,
      displayName: reset.judge.display_name,
      accessCode: reset.access_code,
    });
    await refreshSelectedEvent();
  }

  async function openVoting(form: HTMLFormElement) {
    if (!selectedCompetitionId) return;
    const data = new FormData(form);
    await api<VotingSessionRead>(`/api/competitions/${selectedCompetitionId}/voting-sessions`, {
      method: "POST",
      body: JSON.stringify({ label: textValue(data, "label") || "Round live" }),
    });
    form.reset();
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function closeVoting() {
    if (!selectedCompetitionId) return;
    await api<VotingSessionRead>(`/api/competitions/${selectedCompetitionId}/voting-sessions/close`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function freezeResults() {
    if (!selectedCompetitionId) return;
    await api(`/api/competitions/${selectedCompetitionId}/results/freeze`, {
      method: "POST",
      body: JSON.stringify({ snapshot_name: "Finale" }),
    });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function goEventLive() {
    if (!selectedEventId) return;
    await api<EventRead>(`/api/events/${selectedEventId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "live" }),
    });
    await loadEvents();
    await loadEventData(selectedEventId);
    if (selectedCompetitionId) {
      await loadCompetitionData(selectedCompetitionId);
    }
  }

  async function updateScreenState(form: HTMLFormElement) {
    if (!selectedEventId) return;
    const data = new FormData(form);
    await api<ScreenStateRead>(`/api/events/${selectedEventId}/screen-state`, {
      method: "PUT",
      body: JSON.stringify({
        competition_id: selectedCompetitionId || null,
        mode: textValue(data, "mode"),
        payload_json: {
          title: textValue(data, "title"),
          public_vote_url:
            textValue(data, "public_vote_url") ||
            (selectedCompetitionId
              ? `${window.location.origin}?view=public&competitionId=${selectedCompetitionId}`
              : ""),
          countdown_seconds: numberValue(data, "countdown_seconds", 90),
          reveal_upto: numberValue(data, "reveal_upto", 0),
        },
      }),
    });
    await refreshSelectedEvent();
  }

  return (
    <main className="admin-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Contest Voting Platform</p>
          <h1>
            {view === "admin"
              ? "Admin serata"
              : view === "public"
                ? "Voto pubblico"
                : view === "judge"
                  ? "Giudici"
                  : "Schermo pubblico"}
          </h1>
        </div>
        <div className="topbar-actions">
          <div className="mode-switch">
            <button
              className={view === "admin" ? "active" : ""}
              type="button"
              onClick={() => setView("admin")}
            >
              Admin
            </button>
            <button
              className={view === "public" ? "active" : ""}
              type="button"
              onClick={() => setView("public")}
            >
              Pubblico
            </button>
            <button
              className={view === "judge" ? "active" : ""}
              type="button"
              onClick={() => setView("judge")}
            >
              Giudici
            </button>
            <button
              className={view === "screen" ? "active" : ""}
              type="button"
              onClick={() => setView("screen")}
            >
              Schermo
            </button>
          </div>
          <div className={message.startsWith("Errore:") ? "status-pill error" : "status-pill"}>
            {message}
          </div>
        </div>
      </header>

      {view === "public" ? (
        <PublicArea setMessage={setMessage} />
      ) : view === "judge" ? (
        <JudgeArea setMessage={setMessage} />
      ) : view === "screen" ? (
        <ScreenArea setMessage={setMessage} />
      ) : (
      <section className="workspace">
        <aside className="rail">
          <Panel title="Eventi">
            <Form
              submitLabel="Crea evento"
              onSubmit={(form) => run(() => createEvent(form), "Evento creato")}
            >
              <input name="name" placeholder="Nome evento" required />
              <input name="description" placeholder="Descrizione" />
            </Form>
            <List>
              {state.events.map((event) => (
                <div className={event.id === selectedEventId ? "row active event-row" : "row event-row"} key={event.id}>
                  <button
                    className="event-select"
                    onClick={() => setSelectedEventId(event.id)}
                    type="button"
                  >
                    <span>{event.name}</span>
                    <Badge>{eventStatusLabels[event.status] || event.status}</Badge>
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={() => setDeleteEventCandidate(event)}
                  >
                    Elimina
                  </button>
                </div>
              ))}
            </List>
          </Panel>
        </aside>

        <section className="content">
          <Panel
            title={selectedEvent ? selectedEvent.name : "Seleziona evento"}
            action={
              selectedEvent ? (
                <div className="event-actions">
                  <button type="button" onClick={() => run(refreshSelectedEvent, "Evento aggiornato")}>
                    Aggiorna
                  </button>
                </div>
              ) : null
            }
          >
            <div className="split">
              <div>
                <h2>Competizioni</h2>
                <Form
                  submitLabel="Crea competizione"
                  onSubmit={(form) => run(() => createCompetition(form), "Competizione creata")}
                  disabled={!selectedEvent || configurationLocked}
                >
                  {configurationLocked ? (
                    <p className="lock-note">Evento live o chiuso: configurazione bloccata.</p>
                  ) : null}
                  <label className="field-stack">
                    <span>Nome competizione</span>
                    <input name="name" placeholder="Es. Miglior performance" required />
                  </label>
                  <div className="inline-grid">
                    <label className="checkline">
                      <input name="public_voting_enabled" type="checkbox" defaultChecked />
                      Voto pubblico
                    </label>
                    <label className="checkline">
                      <input name="judge_voting_enabled" type="checkbox" defaultChecked />
                      Voto giudici
                    </label>
                    <label className="checkline">
                      <input name="allow_vote_update" type="checkbox" />
                      Aggiornamento voto
                    </label>
                  </div>
                  <label className="field-stack">
                    <span>Metodo voto pubblico</span>
                    <select name="public_vote_method" defaultValue="single_choice">
                      <option value="single_choice">Scelta singola</option>
                      <option value="ranked_choice">Classifica</option>
                      <option value="criteria_rating">Valutazione per criteri</option>
                    </select>
                  </label>
                  <div className="inline-grid">
                    <label className="field-stack">
                      <span>Peso pubblico</span>
                      <input name="public_weight" type="number" defaultValue="50" min="0" />
                    </label>
                    <label className="field-stack">
                      <span>Peso giudici</span>
                      <input name="judge_weight" type="number" defaultValue="50" min="0" />
                    </label>
                    <label className="field-stack">
                      <span>Max voti per utente</span>
                      <input name="max_votes_per_user" type="number" defaultValue="1" min="1" />
                    </label>
                  </div>
                  <div className="inline-grid">
                    <label className="field-stack">
                      <span>Metodo accesso</span>
                      <select name="access_method" defaultValue="public_link">
                        <option value="public_link">Link pubblico</option>
                        <option value="qr_pin">QR + PIN</option>
                        <option value="private_link">Link privato</option>
                      </select>
                    </label>
                    <label className="field-stack">
                      <span>PIN se QR/PIN</span>
                      <input name="access_pin" placeholder="PIN pubblico" />
                    </label>
                  </div>
                </Form>
                <List>
                  {state.competitions.map((competition) => (
                    <div
                      className={
                        competition.id === selectedCompetitionId ? "row active event-row" : "row event-row"
                      }
                      key={competition.id}
                    >
                      <button
                        className="event-select"
                        onClick={() => setSelectedCompetitionId(competition.id)}
                        type="button"
                      >
                        <span>{competition.name}</span>
                        <Badge>{competitionStatusLabels[competition.status] || competition.status}</Badge>
                      </button>
                      <button
                        className="danger-button"
                        disabled={configurationLocked}
                        type="button"
                        onClick={() => setDeleteCompetitionCandidate(competition)}
                      >
                        Elimina
                      </button>
                    </div>
                  ))}
                </List>
              </div>

              <div>
                <h2>{selectedCompetition ? selectedCompetition.name : "Dettaglio"}</h2>
                {selectedCompetition ? (
                  <>
                    {selectedCompetition.description ? (
                      <p className="form-hint">{selectedCompetition.description}</p>
                    ) : null}
                    <div className="metrics">
                      <Metric label="ID voto" value={selectedCompetition.id} />
                      <Metric label="Stato" value={selectedCompetition.status} />
                      <Metric
                        label="Metodo voto pubblico"
                        value={formatPublicVoteMethod(selectedCompetition.public_vote_method)}
                      />
                      <Metric
                        label="Accesso pubblico"
                        value={formatAccessMethod(selectedCompetition.access_method)}
                      />
                      <Metric label="Peso pubblico" value={selectedCompetition.public_weight} />
                      <Metric label="Peso giudici" value={selectedCompetition.judge_weight} />
                      <Metric
                        label="Voto pubblico"
                        value={selectedCompetition.public_voting_enabled ? "attivo" : "disattivato"}
                      />
                      <Metric
                        label="Voto giudici"
                        value={selectedCompetition.judge_voting_enabled ? "attivo" : "disattivato"}
                      />
                      <Metric
                        label="Max voti per utente"
                        value={selectedCompetition.max_votes_per_user}
                      />
                      <Metric
                        label="Aggiornamento voto"
                        value={selectedCompetition.allow_vote_update ? "consentito" : "bloccato"}
                      />
                      <Metric label="Sessione" value={openSession ? "aperta" : "chiusa"} />
                      <Metric label="Tipo" value={selectedCompetition.type || "non impostato"} />
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          </Panel>

          {selectedCompetition ? (
            <>
              <div className="admin-tabs" role="tablist" aria-label="Sezioni admin competizione">
                {adminSteps.map((step) => (
                  <button
                    aria-selected={adminTab === step.id}
                    className={adminTab === step.id ? "admin-tab active" : "admin-tab"}
                    disabled={step.disabled}
                    key={step.id}
                    onClick={() => setAdminTab(step.id)}
                    role="tab"
                    title={step.disabled ? step.reason : undefined}
                    type="button"
                  >
                    {step.label}
                  </button>
                ))}
              </div>

              <div className="admin-tab-panel">
              {adminTab === "event" ? (
              <Panel title="Workflow evento">
                <div className="metrics">
                  <Metric label="Stato evento" value={selectedEvent ? eventStatusLabels[selectedEvent.status] : "-"} />
                  <Metric label="Competizioni" value={state.competitions.length} />
                  <Metric label="Configurazione" value={setupReady ? "completa" : "incompleta"} />
                  <Metric label="Live" value={isEventLive ? "abilitato" : "non abilitato"} />
                </div>
                {selectedEvent?.status === "draft" ? (
                  <div className="button-strip">
                    <button
                      type="button"
                      disabled={!setupReady}
                      onClick={() => run(goEventLive, "Evento live")}
                    >
                      Porta evento live
                    </button>
                  </div>
                ) : (
                  <p className="lock-note">Evento live o chiuso: setup bloccato, gestione live attiva.</p>
                )}
              </Panel>
              ) : null}

              {adminTab === "competition" ? (
              <Panel title="Impostazioni competizione">
                <div className="metrics">
                  <Metric label="Stato" value={competitionStatusLabels[selectedCompetition.status]} />
                  <Metric
                    label="Voto pubblico"
                    value={selectedCompetition.public_voting_enabled ? "attivo" : "disattivato"}
                  />
                  <Metric
                    label="Voto giudici"
                    value={selectedCompetition.judge_voting_enabled ? "attivo" : "disattivato"}
                  />
                  <Metric
                    label="Metodo pubblico"
                    value={formatPublicVoteMethod(selectedCompetition.public_vote_method)}
                  />
                  <Metric label="Accesso" value={formatAccessMethod(selectedCompetition.access_method)} />
                  <Metric label="Peso pubblico" value={selectedCompetition.public_weight} />
                  <Metric label="Peso giudici" value={selectedCompetition.judge_weight} />
                  <Metric label="Partecipanti attivi" value={activeParticipantsCount} />
                </div>
              </Panel>
              ) : null}

              {adminTab === "participants" ? (
              <Panel title="Partecipanti">
                <Form
                  submitLabel="Aggiungi"
                  onSubmit={(form) => run(() => createParticipant(form), "Partecipante aggiunto")}
                  disabled={configurationLocked}
                >
                  <input name="display_name" placeholder="Nome pubblico" required />
                  <input name="order_index" type="number" placeholder="Ordine" />
                </Form>
                <MiniTable
                  rows={state.participants.map((participant) => [
                    participant.display_name,
                    `#${participant.order_index}`,
                    participant.active ? "attivo" : "off",
                  ])}
                />
              </Panel>
              ) : null}

              {adminTab === "publicCriteria" ? (
              <Panel title="Criteri pubblico">
                {!publicCriteriaRequired ? (
                  <p className="empty">Non richiesti per metodo pubblico corrente.</p>
                ) : null}
                <CriterionForm
                  onSubmit={(form) => run(() => createCriterion(form, "public"), "Criterio aggiunto")}
                  disabled={configurationLocked || !publicCriteriaRequired}
                />
                <CriteriaList criteria={state.publicCriteria} />
              </Panel>
              ) : null}

              {adminTab === "judgeCriteria" ? (
              <Panel title="Criteri giudici">
                {!judgeSetupRequired ? (
                  <p className="empty">Non richiesti se voto giudici disattivato.</p>
                ) : null}
                <CriterionForm
                  onSubmit={(form) => run(() => createCriterion(form, "judge"), "Criterio aggiunto")}
                  disabled={configurationLocked || !judgeSetupRequired}
                />
                <CriteriaList criteria={state.judgeCriteria} />
              </Panel>
              ) : null}

              {adminTab === "judges" ? (
              <Panel title="Giudici">
                <Form
                  submitLabel="Crea giudice"
                  onSubmit={(form) => run(() => createJudge(form), "Giudice creato")}
                  disabled={configurationLocked}
                >
                  <input name="display_name" placeholder="Nome giudice" required />
                  <input name="access_code" placeholder="Codice accesso" required />
                  <p className="form-hint">L'ID tecnico del giudice viene mostrato dopo il salvataggio.</p>
                </Form>
                {judgeCredentialNotice ? (
                  <div className="credential-notice">
                    <strong>Credenziali da consegnare</strong>
                    <div className="credential-grid">
                      <Metric label="Giudice" value={judgeCredentialNotice.displayName} />
                      <Metric label="ID tecnico" value={judgeCredentialNotice.judgeId} />
                      <Metric label="Codice accesso" value={judgeCredentialNotice.accessCode} />
                    </div>
                  </div>
                ) : null}
                <List>
                  {state.judges.map((judge) => (
                    <div className="row compact judge-row" key={judge.id}>
                      <span>
                        <strong>{judge.display_name}</strong>
                        <small>ID tecnico: {judge.id}</small>
                        <small>
                          Competizioni:{" "}
                          {competitionNamesForJudge(judge, state.competitions) || "nessuna"}
                        </small>
                      </span>
                      <div className="judge-competition-list">
                        {state.competitions.length ? (
                          state.competitions.map((competition) => {
                            const isAssigned = judge.assigned_competition_ids.includes(competition.id);
                            return (
                              <label
                                className={isAssigned ? "assignment-chip selected" : "assignment-chip"}
                                key={competition.id}
                              >
                                <input
                                  checked={isAssigned}
                                  type="checkbox"
                                  disabled={configurationLocked}
                                  onChange={() =>
                                    run(
                                      () => toggleJudgeCompetition(judge.id, competition.id, isAssigned),
                                      isAssigned
                                        ? `Giudice rimosso da ${competition.name}`
                                        : `Giudice assegnato a ${competition.name}`
                                    )
                                  }
                                />
                                <span>{competition.name}</span>
                              </label>
                            );
                          })
                        ) : (
                          <small>Nessuna competizione.</small>
                        )}
                      </div>
                      <div className="judge-actions">
                        <button
                          className="secondary-button"
                          disabled={configurationLocked}
                          type="button"
                          onClick={() =>
                            run(
                              () => regenerateJudgeAccessCode(judge.id),
                              "Codice giudice rigenerato"
                            )
                          }
                        >
                          Rigenera codice
                        </button>
                      </div>
                    </div>
                  ))}
                </List>
              </Panel>
              ) : null}

              {adminTab === "review" ? (
              <Panel title="Review configurazione">
                <div className="setup-checklist">
                  <p><strong>Checklist setup</strong></p>
                  <ul>
                    {(state.setupStatus?.checks ?? []).map((check) => (
                      <li className={check.completed ? "done" : ""} key={check.step}>
                        <span>{check.completed ? "OK" : "NO"}</span> {check.message}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="metrics">
                  <Metric label="Setup" value={setupReady ? "completo" : "incompleto"} />
                  <Metric label="Apertura voto" value={canOpenVoting ? "possibile" : "bloccata"} />
                  <Metric label="Evento" value={selectedEvent ? eventStatusLabels[selectedEvent.status] : "-"} />
                  <Metric label="Competizione" value={competitionStatusLabels[selectedCompetition.status]} />
                </div>
                {state.setupStatus?.issues.length ? (
                  <ul className="issue-list">
                    {state.setupStatus.issues.map((issue) => (
                      <li key={issue}>{setupIssueMap[issue] || issue}</li>
                    ))}
                  </ul>
                ) : null}
              </Panel>
              ) : null}

              {adminTab === "live" ? (
              <div className="grid">
              <Panel title="Votazione">
                {state.setupStatus && !state.setupStatus.is_ready && (
                  <div className="setup-checklist">
                    <p><strong>Configurazione richiesta:</strong></p>
                    <ul>
                      {state.setupStatus.issues.map(issue => (
                        <li key={issue}>{setupIssueMap[issue] || issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {state.setupStatus && state.setupStatus.is_ready && !isEventLive && (
                   <div className="setup-success">
                     <p>Setup completo. Porta evento live per abilitare voto e schermo.</p>
                   </div>
                )}
                {state.setupStatus && state.setupStatus.is_ready && isEventLive && !openSession && (
                   <div className="setup-success">
                     <p>Configurazione completata. Votazione apribile.</p>
                   </div>
                )}
                {!isEventLive ? (
                  <div className="button-strip">
                    <button
                      type="button"
                      disabled={!setupReady}
                      onClick={() => run(goEventLive, "Evento live")}
                    >
                      Porta evento live
                    </button>
                  </div>
                ) : null}
                <Form
                  submitLabel="Apri votazione"
                  onSubmit={(form) => run(() => openVoting(form), "Votazione aperta")}
                  disabled={!canOpenVoting || !!openSession}
                >
                  <input name="label" placeholder="Round" defaultValue="Round live" />
                </Form>
                <div className="button-strip">
                  <button
                    type="button"
                    disabled={!openSession}
                    onClick={() => run(closeVoting, "Votazione chiusa")}
                  >
                    Chiudi votazione
                  </button>
                  <button type="button" onClick={() => run(freezeResults, "Risultati congelati")}>
                    Freeze risultati
                  </button>
                </div>
                <MiniTable
                  rows={state.sessions.map((session) => [
                    session.label ?? "Sessione",
                    session.status,
                    session.opened_at ? new Date(session.opened_at).toLocaleTimeString() : "-",
                  ])}
                />
              </Panel>
              </div>
              ) : null}

              {adminTab === "screen" ? (
              <Panel title="Schermo pubblico" className="screen-admin">
                <div className="screen-admin-links">
                  <input
                    readOnly
                    value={
                      selectedEventId
                        ? `${window.location.origin}?view=screen&eventId=${selectedEventId}`
                        : ""
                    }
                  />
                  <button
                    type="button"
                    disabled={!selectedEventId}
                    onClick={() => {
                      if (!selectedEventId) return;
                      window.open(
                        `${window.location.origin}?view=screen&eventId=${selectedEventId}`,
                        "_blank",
                        "noopener,noreferrer"
                      );
                    }}
                  >
                    Apri schermo
                  </button>
                </div>
                <Form
                  submitLabel="Aggiorna schermo"
                  onSubmit={(form) => run(() => updateScreenState(form), "Schermo aggiornato")}
                >
                  <select name="mode" defaultValue={state.screenState?.mode ?? "idle"}>
                    <option value="idle">Idle</option>
                    <option value="show_qr">QR code</option>
                    <option value="voting_open">Votazione aperta</option>
                    <option value="countdown">Countdown</option>
                    <option value="show_results">Risultati</option>
                    <option value="reveal_ranking">Reveal classifica</option>
                    <option value="show_podium">Podio</option>
                    <option value="show_final_winners">Finale</option>
                  </select>
                  <input
                    name="title"
                    placeholder="Titolo schermo"
                    defaultValue={String(state.screenState?.payload_json.title ?? "")}
                  />
                  <input
                    name="public_vote_url"
                    placeholder="URL voto pubblico"
                    defaultValue={
                      String(state.screenState?.payload_json.public_vote_url ?? "") ||
                      `${window.location.origin}?view=public&competitionId=${selectedCompetitionId}`
                    }
                  />
                  <input
                    name="countdown_seconds"
                    type="number"
                    min="0"
                    placeholder="Secondi countdown"
                    defaultValue={String(state.screenState?.payload_json.countdown_seconds ?? "90")}
                  />
                  <input
                    name="reveal_upto"
                    type="number"
                    min="0"
                    placeholder="Reveal fino a pos. (da fondo)"
                    defaultValue={String(state.screenState?.payload_json.reveal_upto ?? "0")}
                  />
                </Form>
                {state.screenState?.mode === "reveal_ranking" && (
                  <div className="reveal-controls">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => {
                        const current = numberPayload(state.screenState, "reveal_upto", 0);
                        const total = state.results?.results.length ?? 0;
                        if (current >= total) return;
                        
                        // Trova il form dello schermo per inviare i dati aggiornati
                        const form = document.querySelector(".screen-admin form") as HTMLFormElement;
                        if (form) {
                          const input = form.querySelector("input[name='reveal_upto']") as HTMLInputElement;
                          if (input) {
                            input.value = String(current + 1);
                            form.requestSubmit();
                          }
                        }
                      }}
                    >
                      Svela prossima posizione ({numberPayload(state.screenState, "reveal_upto", 0)} / {state.results?.results.length ?? 0})
                    </button>
                  </div>
                )}
                <div className="metrics">
                  <Metric label="Modalita" value={screenModeLabel(state.screenState?.mode ?? "idle")} />
                  <Metric label="Competizione" value={selectedCompetition.name} />
                </div>
              </Panel>
              ) : null}

              {adminTab === "results" ? (
              <Panel title="Risultati">
                <button
                  type="button"
                  onClick={() => run(refreshSelectedCompetition, "Risultati aggiornati")}
                >
                  Aggiorna risultati
                </button>
                <ol className="ranking">
                  {(state.results?.results ?? []).map((result) => (
                    <li key={result.participant_id}>
                      <strong>
                        {result.rank}. {result.display_name}
                      </strong>
                      <span>{result.final_score.toFixed(2)}</span>
                      <small>
                        Pub {result.public_score.normalized_score.toFixed(1)} / Giu{" "}
                        {result.judge_score.normalized_score.toFixed(1)}
                      </small>
                    </li>
                  ))}
                </ol>
              </Panel>
              ) : null}

              {adminTab === "logs" ? (
              <Panel title="Log attività">
                <div className="audit-controls">
                  <input
                    aria-label="Cerca log"
                    placeholder="Cerca nei log"
                    value={auditFilters.query}
                    onChange={(event) =>
                      setAuditFilters((current) => ({
                        ...current,
                        query: event.target.value,
                        page: 1,
                      }))
                    }
                  />
                  <select
                    aria-label="Filtra attore"
                    value={auditFilters.actorType}
                    onChange={(event) =>
                      setAuditFilters((current) => ({
                        ...current,
                        actorType: event.target.value,
                        page: 1,
                      }))
                    }
                  >
                    <option value="all">Tutti attori</option>
                    {auditActorTypes.map((actorType) => (
                      <option key={actorType} value={actorType}>
                        {actorType}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Filtra entità"
                    value={auditFilters.entityType}
                    onChange={(event) =>
                      setAuditFilters((current) => ({
                        ...current,
                        entityType: event.target.value,
                        page: 1,
                      }))
                    }
                  >
                    <option value="all">Tutte entità</option>
                    {auditEntityTypes.map((entityType) => (
                      <option key={entityType} value={entityType}>
                        {entityType}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Filtra azione"
                    value={auditFilters.action}
                    onChange={(event) =>
                      setAuditFilters((current) => ({
                        ...current,
                        action: event.target.value,
                        page: 1,
                      }))
                    }
                  >
                    <option value="all">Tutte azioni</option>
                    {auditActions.map((action) => (
                      <option key={action} value={action}>
                        {auditActionLabel(action)}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Log per pagina"
                    value={auditFilters.pageSize}
                    onChange={(event) =>
                      setAuditFilters((current) => ({
                        ...current,
                        pageSize: Number(event.target.value),
                        page: 1,
                      }))
                    }
                  >
                    {[20, 40, 100, 200].map((pageSize) => (
                      <option key={pageSize} value={pageSize}>
                        {pageSize} per pagina
                      </option>
                    ))}
                  </select>
                </div>
                <div className="audit-summary">
                  <span>
                    {filteredAuditLogs.length} log filtrati su {state.auditLogs.length}
                  </span>
                  <div className="audit-pagination">
                    <button
                      className="secondary-button"
                      disabled={auditPage <= 1}
                      type="button"
                      onClick={() =>
                        setAuditFilters((current) => ({
                          ...current,
                          page: Math.max(1, auditPage - 1),
                        }))
                      }
                    >
                      Precedente
                    </button>
                    <span>
                      {auditPage}/{auditPageCount}
                    </span>
                    <button
                      className="secondary-button"
                      disabled={auditPage >= auditPageCount}
                      type="button"
                      onClick={() =>
                        setAuditFilters((current) => ({
                          ...current,
                          page: Math.min(auditPageCount, auditPage + 1),
                        }))
                      }
                    >
                      Successiva
                    </button>
                  </div>
                </div>
                <List>
                  {pagedAuditLogs.length > 0 ? (
                    pagedAuditLogs.map((log) => (
                      <div className="row compact audit-row" key={log.id}>
                        <span>
                          <strong>{auditActionLabel(log.action)}</strong>
                          <small>{new Date(log.created_at).toLocaleString()}</small>
                          <small>
                            {log.actor_label ?? log.actor_type} · {log.entity_type}
                            {log.entity_id ? ` · ${log.entity_id}` : ""}
                          </small>
                          <small>{auditDetailsText(log.details_json)}</small>
                        </span>
                        <Badge>{log.actor_type}</Badge>
                      </div>
                    ))
                  ) : (
                    <p className="empty">Nessun log per i filtri selezionati.</p>
                  )}
                </List>
              </Panel>
              ) : null}
              </div>
            </>
          ) : null}
        </section>
      </section>
      )}
      {deleteEventCandidate ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="confirm-modal" role="dialog">
            <h2>Eliminare evento?</h2>
            <p>
              Verranno eliminati evento, competizioni, partecipanti, criteri, giudici, voti,
              sessioni, risultati, schermo e log collegati a "{deleteEventCandidate.name}".
            </p>
            <div className="button-strip">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setDeleteEventCandidate(null)}
              >
                Annulla
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={() =>
                  run(() => deleteEvent(deleteEventCandidate.id), "Evento eliminato")
                }
              >
                Elimina definitivamente
              </button>
            </div>
          </section>
        </div>
      ) : null}
      {deleteCompetitionCandidate ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="confirm-modal" role="dialog">
            <h2>Eliminare competizione?</h2>
            <p>
              Verranno eliminati competizione, partecipanti, criteri, sessioni, voti,
              risultati e log collegati a "{deleteCompetitionCandidate.name}".
            </p>
            <div className="button-strip">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setDeleteCompetitionCandidate(null)}
              >
                Annulla
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={() =>
                  run(() => deleteCompetition(deleteCompetitionCandidate.id), "Competizione eliminata")
                }
              >
                Elimina definitivamente
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}

function ScreenArea({ setMessage }: { setMessage: (message: string) => void }) {
  const [state, setState] = useState<ScreenAreaState>({
    ...emptyScreenAreaState,
    eventId: initialEventIdFromUrl(),
  });
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState("");
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const openSession = state.sessions.find((session) => session.status === "open");
  const title =
    textPayload(state.screenState, "title") ||
    state.competition?.name ||
    "Contest Voting Platform";
  const voteUrl =
    textPayload(state.screenState, "public_vote_url") || `${window.location.origin} - ID ${state.competition?.id ?? ""}`;
  const countdownSeconds = numberPayload(state.screenState, "countdown_seconds", 0);
  const allRanking = state.results?.results ?? [];
  const revealUpto = numberPayload(state.screenState, "reveal_upto", 0);
  const ranking =
    state.screenState?.mode === "reveal_ranking" && revealUpto > 0
      ? allRanking.slice(-revealUpto)
      : allRanking;
  const podium = allRanking.slice(0, 3);
  const maxScore = Math.max(...allRanking.map((result) => result.final_score), 1);

  async function run(action: () => Promise<void>, doneMessage: string) {
    try {
      await action();
      setMessage(doneMessage);
    } catch (error) {
      setMessage(`Errore: ${error instanceof Error ? error.message : "Errore inatteso"}`);
    }
  }

  async function connectScreen() {
    const eventId = state.eventId.trim();
    if (!eventId) {
      throw new Error("event_id mancante per lo schermo");
    }
    const screenState = await api<ScreenStateRead>(`/api/events/${eventId}/screen-state`);
    setState((current) => ({ ...current, activeEventId: eventId, screenState }));
    await loadScreenDetails(screenState);
  }

  async function loadScreenDetails(screenState: ScreenStateRead) {
    if (!screenState.competition_id) {
      setState((current) => ({
        ...current,
        screenState,
        competition: null,
        sessions: [],
        summary: null,
        results: null,
      }));
      return;
    }
    const [competition, sessions, summary, results] = await Promise.all([
      api<CompetitionRead>(`/api/competitions/${screenState.competition_id}`),
      api<VotingSessionRead[]>(`/api/competitions/${screenState.competition_id}/voting-sessions`),
      api<PublicVoteSummaryRead>(`/api/competitions/${screenState.competition_id}/public-votes/summary`),
      api<ResultsRead>(`/api/competitions/${screenState.competition_id}/results`),
    ]);
    setState((current) => ({
      ...current,
      screenState,
      competition,
      sessions,
      summary,
      results,
    }));
  }

  useEffect(() => {
    if (state.eventId && !state.activeEventId) {
      void run(connectScreen, "Schermo collegato");
    }
  }, [state.eventId, state.activeEventId]);

  useEffect(() => {
    if (!state.activeEventId) return undefined;
    const websocket = new WebSocket(`${websocketBaseUrl}/ws/events/${state.activeEventId}/screen`);
    websocket.onopen = () => setState((current) => ({ ...current, connected: true }));
    websocket.onclose = () => setState((current) => ({ ...current, connected: false }));
    websocket.onerror = () => setMessage("WebSocket schermo non disponibile");
    websocket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { screen_state?: ScreenStateRead };
      if (payload.screen_state) {
        void loadScreenDetails(payload.screen_state);
      }
    };
    return () => websocket.close();
  }, [state.activeEventId]);

  useEffect(() => {
    if (!voteUrl.trim()) {
      setQrCodeDataUrl("");
      return;
    }
    void QRCode.toDataURL(voteUrl, {
      margin: 1,
      width: 360,
      color: { dark: "#112736", light: "#ffffff" },
    }).then(setQrCodeDataUrl);
  }, [voteUrl]);

  useEffect(() => {
    const mode = state.screenState?.mode;
    const initialSeconds = numberPayload(state.screenState, "countdown_seconds", 0);

    if (mode === "countdown" && initialSeconds > 0) {
      setRemainingSeconds(initialSeconds);
      const timer = setInterval(() => {
        setRemainingSeconds((prev) => (prev !== null && prev > 0 ? prev - 1 : prev));
      }, 1000);
      return () => clearInterval(timer);
    } else {
      setRemainingSeconds(null);
    }
  }, [state.screenState?.mode, state.screenState?.payload_json]);

  return (
    <section className="screen-shell">
      <Panel title="Connessione schermo">
        <div className="public-access">
          <input
            value={state.eventId}
            onChange={(event) => setState((current) => ({ ...current, eventId: event.target.value }))}
            placeholder="ID evento"
          />
          <button type="button" onClick={() => run(connectScreen, "Schermo collegato")}>
            Collega
          </button>
        </div>
      </Panel>

      <section className={`stage stage-${state.screenState?.mode ?? "idle"}`}>
        <div className="stage-status">
          <span>{state.connected ? "live" : "offline"}</span>
          <span>{screenModeLabel(state.screenState?.mode ?? "idle")}</span>
          {state.competition?.status === "results_frozen" && <span>Ufficiale</span>}
        </div>
        <div className="stage-heading">
          <p>{state.competition?.name ?? "Nessuna competizione selezionata"}</p>
          <h2>{title}</h2>
        </div>

        {state.screenState?.mode === "show_qr" ? (
          <div className="qr-layout">
            <div className="qr-code" aria-label="QR code">
              {qrCodeDataUrl ? <img alt="QR code voto pubblico" src={qrCodeDataUrl} /> : null}
            </div>
            <div>
              <h3>Vota ora</h3>
              <p>{voteUrl}</p>
              <strong>{state.competition?.id ?? ""}</strong>
            </div>
          </div>
        ) : null}

        {state.screenState?.mode === "voting_open" || state.screenState?.mode === "countdown" ? (
          <div className="live-vote">
            <div>
              <span>Voti ricevuti</span>
              <strong>{state.summary?.total_votes ?? 0}</strong>
            </div>
            <div>
              <span>Sessione</span>
              <strong>{openSession ? "aperta" : "chiusa"}</strong>
            </div>
            {state.screenState?.mode === "countdown" ? (
              <div>
                <span>Countdown</span>
                <strong>{remainingSeconds ?? countdownSeconds}s</strong>
              </div>
            ) : null}
          </div>
        ) : null}

        {state.screenState?.mode === "show_results" || state.screenState?.mode === "reveal_ranking" ? (
          <ol className="stage-ranking">
            {ranking.map((result) => (
              <li key={result.participant_id}>
                <span>{result.rank}</span>
                <strong>{result.display_name}</strong>
                <div>
                  <i style={{ width: `${Math.max(8, (result.final_score / maxScore) * 100)}%` }} />
                </div>
                <em>{result.final_score.toFixed(1)}</em>
              </li>
            ))}
          </ol>
        ) : null}

        {state.screenState?.mode === "show_podium" || state.screenState?.mode === "show_final_winners" ? (
          <div className="podium">
            {podium.map((result) => (
              <div className={`podium-place podium-${result.rank}`} key={result.participant_id}>
                <span>#{result.rank}</span>
                <strong>{result.display_name}</strong>
                <em>{result.final_score.toFixed(1)}</em>
              </div>
            ))}
          </div>
        ) : null}

        {state.screenState?.mode === "idle" || !state.screenState ? (
          <div className="stage-idle">In attesa del comando admin.</div>
        ) : null}
      </section>
    </section>
  );
}

function JudgeArea({ setMessage }: { setMessage: (message: string) => void }) {
  const [state, setState] = useState<JudgeState>(emptyJudgeState);
  const openSession = state.sessions.find((session) => session.status === "open");
  const canVote = Boolean(state.competition?.judge_voting_enabled && openSession);
  const selectedSavedVote = state.savedVotes[state.selectedParticipantId];

  async function run(action: () => Promise<void>, doneMessage: string) {
    try {
      await action();
      setMessage(doneMessage);
    } catch (error) {
      setMessage(`Errore: ${error instanceof Error ? error.message : "Errore inatteso"}`);
    }
  }

  async function loginJudge(form: HTMLFormElement) {
    const data = new FormData(form);
    const judgeId = textValue(data, "judge_id");
    const accessCode = textValue(data, "access_code");
    const access = await api<JudgeAccessRead>("/api/judge-access", {
      method: "POST",
      body: JSON.stringify({ judge_id: judgeId, access_code: accessCode }),
    });
    const competitionStatuses = await loadJudgeCompetitionStatuses(access, judgeId, accessCode);
    const selectedCompetitionId =
      access.competitions.find(
        (competition) => competitionStatuses[competition.id]?.voting_session_status === "open"
      )?.id ??
      access.competitions[0]?.id ??
      "";
    setState({
      ...emptyJudgeState,
      access,
      judgeId,
      accessCode,
      competitionStatuses,
      selectedCompetitionId,
    });
  }

  async function loadJudgeCompetition(competitionId = state.selectedCompetitionId) {
    if (!competitionId || !state.access) return;
    const [competition, participants, judgeCriteria, sessions] = await Promise.all([
      api<CompetitionRead>(`/api/competitions/${competitionId}`),
      api<ParticipantRead[]>(`/api/competitions/${competitionId}/participants`),
      api<CriterionRead[]>(`/api/competitions/${competitionId}/judge-criteria`),
      api<VotingSessionRead[]>(`/api/competitions/${competitionId}/voting-sessions`),
    ]);
    const [status, savedVoteList]: [JudgeVoteStatusRead, JudgeVoteDetailRead[]] = competition.judge_voting_enabled
      ? await Promise.all([
          api<JudgeVoteStatusRead>(
            `/api/competitions/${competitionId}/judge-votes/status?judge_id=${state.judgeId}&access_code=${encodeURIComponent(
              state.accessCode
            )}`
          ),
          api<JudgeVoteDetailRead[]>(
            `/api/competitions/${competitionId}/judge-votes?judge_id=${state.judgeId}&access_code=${encodeURIComponent(
              state.accessCode
            )}`
          ),
        ])
      : [emptyJudgeVoteStatus(competitionId, state.judgeId), []];
    const savedVotes = savedJudgeVotesByParticipant(savedVoteList);
    setState((current) => {
      const selectedParticipantId =
        current.selectedCompetitionId === competitionId &&
        participants.some((participant) => participant.id === current.selectedParticipantId)
          ? current.selectedParticipantId
          : firstPendingParticipantId(participants, savedVotes) ?? participants[0]?.id ?? "";
      return {
        ...current,
        selectedCompetitionId: competitionId,
        competition,
        participants,
        judgeCriteria,
        sessions,
        status,
        competitionStatuses: {
          ...current.competitionStatuses,
          [competitionId]: status,
        },
        savedVotes,
        selectedParticipantId,
        criteriaScores: judgeScoresForParticipant(judgeCriteria, savedVotes, selectedParticipantId),
        confirmation: "",
      };
    });
  }

  async function submitJudgeVote() {
    if (!state.competition || !canVote) return;
    await api(`/api/competitions/${state.competition.id}/judge-votes`, {
      method: "POST",
      body: JSON.stringify({
        judge_id: state.judgeId,
        access_code: state.accessCode,
        participant_id: state.selectedParticipantId,
        criteria: state.judgeCriteria.map((criterion) => ({
          criterion_id: criterion.id,
          score: state.criteriaScores[criterion.id] ?? criterion.min_score,
        })),
      }),
    });
    const [status, savedVoteList] = await Promise.all([
      api<JudgeVoteStatusRead>(
        `/api/competitions/${state.competition.id}/judge-votes/status?judge_id=${state.judgeId}&access_code=${encodeURIComponent(
          state.accessCode
        )}`
      ),
      api<JudgeVoteDetailRead[]>(
        `/api/competitions/${state.competition.id}/judge-votes?judge_id=${state.judgeId}&access_code=${encodeURIComponent(
          state.accessCode
        )}`
      ),
    ]);
    const savedVotes = savedJudgeVotesByParticipant(savedVoteList);
    setState((current) => ({
      ...current,
      status,
      competitionStatuses: {
        ...current.competitionStatuses,
        [state.competition!.id]: status,
      },
      savedVotes,
      criteriaScores: judgeScoresForParticipant(
        current.judgeCriteria,
        savedVotes,
        current.selectedParticipantId
      ),
      confirmation: "Voto giudice salvato",
    }));
  }

  useEffect(() => {
    if (state.access && state.selectedCompetitionId && !state.competition) {
      void run(() => loadJudgeCompetition(), "Competizione giudice caricata");
    }
  }, [state.access, state.selectedCompetitionId, state.competition]);

  return (
    <section className="public-shell">
      <Panel title="Accesso giudice">
        <Form submitLabel="Entra" onSubmit={(form) => run(() => loginJudge(form), "Giudice autenticato")}>
          <input name="judge_id" placeholder="ID giudice" required />
          <input name="access_code" placeholder="Codice accesso" required />
        </Form>
      </Panel>

      {state.access ? (
        <Panel title={state.access.display_name}>
          <div className="judge-layout">
            <div>
              <h2>Competizioni assegnate</h2>
              <List>
                {state.access.competitions.length ? (
                  state.access.competitions.map((competition) => {
                    const status = state.competitionStatuses[competition.id];
                    return (
                      <button
                        className={competition.id === state.selectedCompetitionId ? "row active" : "row"}
                        key={competition.id}
                        type="button"
                        onClick={() => run(() => loadJudgeCompetition(competition.id), "Competizione caricata")}
                      >
                        <span>
                          <strong>{competition.name}</strong>
                          <small>{formatJudgeCompetitionProgress(status)}</small>
                        </span>
                        <Badge>{competition.status}</Badge>
                      </button>
                    );
                  })
                ) : (
                  <p className="empty">Nessuna competizione assegnata.</p>
                )}
              </List>
            </div>
            <div>
              <button
                type="button"
                disabled={!state.selectedCompetitionId}
                onClick={() => run(() => loadJudgeCompetition(), "Stato giudice aggiornato")}
              >
                Carica voto
              </button>
            </div>
          </div>
        </Panel>
      ) : null}

      {state.competition ? (
        <Panel title={state.competition.name}>
          <div className="public-header">
            <Metric label="Stato" value={openSession ? "votazione aperta" : "votazione chiusa"} />
            <Metric
              label="Completamento"
              value={
                state.status
                  ? `${state.status.voted_participants}/${state.status.total_participants}`
                  : "0/0"
              }
            />
            <Metric label="Esito" value={state.status?.completed ? "completo" : "in corso"} />
          </div>

          {!openSession ? (
            <div className="closed-state">La votazione giudici non e aperta in questo momento.</div>
          ) : (
            <div className="vote-surface">
              <ParticipantChoices
                participants={state.participants}
                selectedParticipantId={state.selectedParticipantId}
                badgesByParticipantId={Object.fromEntries(
                  state.participants.map((participant) => [
                    participant.id,
                    state.savedVotes[participant.id] ? "salvato" : "da votare",
                  ])
                )}
                onSelect={(participantId) =>
                  setState((current) => ({
                    ...current,
                    selectedParticipantId: participantId,
                    criteriaScores: judgeScoresForParticipant(
                      current.judgeCriteria,
                      current.savedVotes,
                      participantId
                    ),
                    confirmation: "",
                  }))
                }
              />
              {selectedSavedVote && !state.confirmation ? (
                <div className="confirmation">Voto salvato caricato per questo partecipante.</div>
              ) : null}
              <CriteriaRating
                criteria={state.judgeCriteria}
                scores={state.criteriaScores}
                onChange={(criterionId, score) =>
                  setState((current) => ({
                    ...current,
                    criteriaScores: { ...current.criteriaScores, [criterionId]: score },
                    confirmation: "",
                  }))
                }
              />
              <button type="button" onClick={() => run(submitJudgeVote, "Voto giudice inviato")}>
                Salva voto partecipante
              </button>
              {state.confirmation ? <div className="confirmation">{state.confirmation}</div> : null}
            </div>
          )}
        </Panel>
      ) : null}
    </section>
  );
}

async function loadJudgeCompetitionStatuses(
  access: JudgeAccessRead,
  judgeId: string,
  accessCode: string
): Promise<Record<string, JudgeVoteStatusRead>> {
  const entries = await Promise.all(
    access.competitions.map(async (competition) => {
      try {
        return [
          competition.id,
          await api<JudgeVoteStatusRead>(
            `/api/competitions/${competition.id}/judge-votes/status?judge_id=${judgeId}&access_code=${encodeURIComponent(
              accessCode
            )}`
          ),
        ] as const;
      } catch {
        return [competition.id, emptyJudgeVoteStatus(competition.id, judgeId)] as const;
      }
    })
  );
  return Object.fromEntries(entries);
}

function emptyJudgeVoteStatus(competitionId: string, judgeId: string): JudgeVoteStatusRead {
  return {
    competition_id: competitionId,
    judge_id: judgeId,
    voting_session_id: null,
    voting_session_status: null,
    total_participants: 0,
    voted_participants: 0,
    completed: false,
  };
}

function savedJudgeVotesByParticipant(
  savedVoteList: JudgeVoteDetailRead[]
): Record<string, SavedJudgeVote> {
  return Object.fromEntries(
    savedVoteList.map((vote) => [
      vote.participant_id,
      {
        votingSessionId: vote.voting_session_id,
        scores: Object.fromEntries(
          vote.criterion_votes.map((criterionVote) => [
            criterionVote.criterion_id,
            criterionVote.score,
          ])
        ),
      },
    ])
  );
}

function firstPendingParticipantId(
  participants: ParticipantRead[],
  savedVotes: Record<string, SavedJudgeVote>
): string | null {
  return participants.find((participant) => !savedVotes[participant.id])?.id ?? null;
}

function judgeScoresForParticipant(
  criteria: CriterionRead[],
  savedVotes: Record<string, SavedJudgeVote>,
  participantId: string
): Record<string, number> {
  const savedScores = savedVotes[participantId]?.scores ?? {};
  return Object.fromEntries(
    criteria.map((criterion) => [
      criterion.id,
      savedScores[criterion.id] ?? criterion.min_score,
    ])
  );
}

function formatJudgeCompetitionProgress(status: JudgeVoteStatusRead | undefined): string {
  if (!status) {
    return "Stato non caricato";
  }
  const progress = `${status.voted_participants}/${status.total_participants}`;
  if (status.completed) {
    return `Completa (${progress})`;
  }
  if (status.voting_session_status === "open") {
    return `Aperta (${progress})`;
  }
  if (status.voting_session_status === "closed") {
    return `Chiusa (${progress})`;
  }
  return `In attesa (${progress})`;
}

function PublicArea({ setMessage }: { setMessage: (message: string) => void }) {
  const [competitionId, setCompetitionId] = useState(
    new URLSearchParams(window.location.search).get("competitionId") ?? ""
  );
  const [accessPin, setAccessPin] = useState("");
  const [state, setState] = useState<PublicState>(emptyPublicState);
  const openSession = state.sessions.find((session) => session.status === "open");
  const canVote = Boolean(state.competition && openSession);

  async function run(action: () => Promise<void>, doneMessage: string) {
    try {
      await action();
      setMessage(doneMessage);
    } catch (error) {
      setMessage(`Errore: ${error instanceof Error ? error.message : "Errore inatteso"}`);
    }
  }

  async function loadCompetition() {
    const id = competitionId.trim();
    if (!id) return;
    await api<PublicCompetitionAccessRead>(`/api/competitions/${id}/public-access`, {
      method: "POST",
      body: JSON.stringify({ pin: accessPin || null }),
    });
    const [competition, participants, publicCriteria, sessions] = await Promise.all([
      api<CompetitionRead>(`/api/competitions/${id}`),
      api<ParticipantRead[]>(`/api/competitions/${id}/participants`),
      api<CriterionRead[]>(`/api/competitions/${id}/public-criteria`),
      api<VotingSessionRead[]>(`/api/competitions/${id}/voting-sessions`),
    ]);
    setState({
      competition,
      participants,
      publicCriteria,
      sessions,
      selectedParticipantId: participants[0]?.id ?? "",
      rankedParticipantIds: participants.slice(0, competition.max_votes_per_user).map((item) => item.id),
      criteriaScores: Object.fromEntries(publicCriteria.map((criterion) => [criterion.id, criterion.min_score])),
      confirmation: "",
    });
  }

  async function submitPublicVote() {
    if (!state.competition || !canVote) return;
    const voterToken = getPublicVoterToken();
    const payload =
      state.competition.public_vote_method === "single_choice"
        ? {
            voter_token: voterToken,
            method: "single_choice",
            participant_id: state.selectedParticipantId,
          }
        : state.competition.public_vote_method === "ranked_choice"
          ? {
              voter_token: voterToken,
              method: "ranked_choice",
              ranked_participant_ids: state.rankedParticipantIds.filter(Boolean),
            }
          : {
              voter_token: voterToken,
              method: "criteria_rating",
              ratings: [
                {
                  participant_id: state.selectedParticipantId,
                  criteria: state.publicCriteria.map((criterion) => ({
                    criterion_id: criterion.id,
                    score: state.criteriaScores[criterion.id] ?? criterion.min_score,
                  })),
                },
              ],
            };

    await api(`/api/competitions/${state.competition.id}/public-votes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setState((current) => ({ ...current, confirmation: "Voto registrato" }));
  }

  useEffect(() => {
    if (competitionId && !state.competition) {
      void run(loadCompetition, "Competizione caricata");
    }
  }, [competitionId, state.competition]);

  return (
    <section className="public-shell">
      <Panel title="Accesso competizione">
        <div className="public-access">
          <input
            value={competitionId}
            onChange={(event) => setCompetitionId(event.target.value)}
            placeholder="ID competizione"
          />
          <input
            value={accessPin}
            onChange={(event) => setAccessPin(event.target.value)}
            placeholder="PIN se richiesto"
          />
          <button type="button" onClick={() => run(loadCompetition, "Competizione caricata")}>
            Entra
          </button>
        </div>
      </Panel>

      {state.competition ? (
        <Panel title={state.competition.name}>
          <div className="public-header">
            <Metric label="Metodo" value={state.competition.public_vote_method} />
            <Metric label="Stato" value={openSession ? "votazione aperta" : "votazione chiusa"} />
          </div>
          {!openSession ? (
            <div className="closed-state">La votazione non e aperta in questo momento.</div>
          ) : (
            <div className="vote-surface">
              {state.competition.public_vote_method === "single_choice" ? (
                <ParticipantChoices
                  participants={state.participants}
                  selectedParticipantId={state.selectedParticipantId}
                  onSelect={(participantId) =>
                    setState((current) => ({ ...current, selectedParticipantId: participantId }))
                  }
                />
              ) : null}

              {state.competition.public_vote_method === "ranked_choice" ? (
                <RankedChoice
                  participants={state.participants}
                  maxVotes={state.competition.max_votes_per_user}
                  rankedParticipantIds={state.rankedParticipantIds}
                  onChange={(rankedParticipantIds) =>
                    setState((current) => ({ ...current, rankedParticipantIds }))
                  }
                />
              ) : null}

              {state.competition.public_vote_method === "criteria_rating" ? (
                <>
                  <ParticipantChoices
                    participants={state.participants}
                    selectedParticipantId={state.selectedParticipantId}
                    onSelect={(participantId) =>
                      setState((current) => ({ ...current, selectedParticipantId: participantId }))
                    }
                  />
                  <CriteriaRating
                    criteria={state.publicCriteria}
                    scores={state.criteriaScores}
                    onChange={(criterionId, score) =>
                      setState((current) => ({
                        ...current,
                        criteriaScores: { ...current.criteriaScores, [criterionId]: score },
                      }))
                    }
                  />
                </>
              ) : null}

              <button
                type="button"
                disabled={
                  !state.selectedParticipantId ||
                  (state.competition.public_vote_method === "ranked_choice" &&
                    state.rankedParticipantIds.filter(Boolean).length === 0)
                }
                onClick={() => run(submitPublicVote, "Voto inviato")}
              >
                Conferma voto
              </button>
              {state.confirmation ? <div className="confirmation">{state.confirmation}</div> : null}
            </div>
          )}
        </Panel>
      ) : null}
    </section>
  );
}

function ParticipantChoices({
  participants,
  selectedParticipantId,
  badgesByParticipantId,
  onSelect,
}: {
  participants: ParticipantRead[];
  selectedParticipantId: string;
  badgesByParticipantId?: Record<string, string>;
  onSelect: (participantId: string) => void;
}) {
  return (
    <div className="participant-grid">
      {participants.map((participant) => (
        <button
          className={participant.id === selectedParticipantId ? "vote-card selected" : "vote-card"}
          key={participant.id}
          type="button"
          onClick={() => onSelect(participant.id)}
        >
          <span>{participant.display_name}</span>
          {badgesByParticipantId?.[participant.id] ? (
            <small>{badgesByParticipantId[participant.id]}</small>
          ) : null}
        </button>
      ))}
    </div>
  );
}

function RankedChoice({
  participants,
  maxVotes,
  rankedParticipantIds,
  onChange,
}: {
  participants: ParticipantRead[];
  maxVotes: number;
  rankedParticipantIds: string[];
  onChange: (rankedParticipantIds: string[]) => void;
}) {
  const slots = Array.from({ length: Math.min(maxVotes, participants.length) }, (_, index) => index);
  return (
    <div className="ranked-list">
      {slots.map((index) => (
        <label key={index}>
          <span>Posizione {index + 1}</span>
          <select
            value={rankedParticipantIds[index] ?? ""}
            onChange={(event) => {
              const next = [...rankedParticipantIds];
              next[index] = event.target.value;
              onChange(next);
            }}
          >
            <option value="">Seleziona</option>
            {participants.map((participant) => (
              <option
                disabled={
                  rankedParticipantIds.includes(participant.id) &&
                  rankedParticipantIds[index] !== participant.id
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
  );
}

function CriteriaRating({
  criteria,
  scores,
  onChange,
}: {
  criteria: CriterionRead[];
  scores: Record<string, number>;
  onChange: (criterionId: string, score: number) => void;
}) {
  return (
    <div className="criteria-rating">
      {criteria.map((criterion) => (
        <label key={criterion.id}>
          <span>
            {criterion.name} ({scores[criterion.id] ?? criterion.min_score})
          </span>
          <input
            type="range"
            min={criterion.min_score}
            max={criterion.max_score}
            step="1"
            value={scores[criterion.id] ?? criterion.min_score}
            onChange={(event) => onChange(criterion.id, Number(event.target.value))}
          />
        </label>
      ))}
    </div>
  );
}

function Form({
  children,
  submitLabel,
  onSubmit,
  disabled,
}: {
  children: ReactNode;
  submitLabel: string;
  onSubmit: (form: HTMLFormElement) => void;
  disabled?: boolean;
}) {
  return (
    <form
      className="form"
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (disabled) return;
        onSubmit(event.currentTarget);
      }}
    >
      {children}
      <button type="submit" disabled={disabled}>{submitLabel}</button>
    </form>
  );
}

function CriterionForm({
  onSubmit,
  disabled,
}: {
  onSubmit: (form: HTMLFormElement) => void;
  disabled?: boolean;
}) {
  return (
    <Form submitLabel="Aggiungi criterio" onSubmit={onSubmit} disabled={disabled}>
      <input name="name" placeholder="Nome criterio" required />
      <div className="inline-grid">
        <input name="min_score" type="number" defaultValue="1" />
        <input name="max_score" type="number" defaultValue="10" />
        <input name="weight" type="number" defaultValue="1" />
      </div>
    </Form>
  );
}

function Panel({
  title,
  children,
  action,
  className,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={className ? `panel ${className}` : "panel"}>
      <div className="panel-title">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function List({ children }: { children: ReactNode }) {
  return <div className="list">{children}</div>;
}

function Badge({ children }: { children: ReactNode }) {
  return <span className="badge">{children}</span>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MiniTable({ rows }: { rows: string[][] }) {
  if (rows.length === 0) {
    return <p className="empty">Nessun dato.</p>;
  }
  return (
    <div className="mini-table">
      {rows.map((row, rowIndex) => (
        <div className="mini-row" key={`${row.join("-")}-${rowIndex}`}>
          {row.map((cell, cellIndex) => (
            <span key={`${cell}-${cellIndex}`}>{cell}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

function CriteriaList({ criteria }: { criteria: CriterionRead[] }) {
  return (
    <MiniTable
      rows={criteria.map((criterion) => [
        criterion.name,
        `${criterion.min_score}-${criterion.max_score}`,
        `x${criterion.weight}`,
      ])}
    />
  );
}

function competitionNamesForJudge(judge: JudgeRead, competitions: CompetitionRead[]): string {
  return judge.assigned_competition_ids
    .map((competitionId) => competitions.find((competition) => competition.id === competitionId)?.name)
    .filter((name): name is string => Boolean(name))
    .join(", ");
}

function initialViewFromUrl(): AppView {
  const view = new URLSearchParams(window.location.search).get("view");
  return view === "public" || view === "judge" || view === "screen" ? view : "admin";
}

function initialEventIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get("eventId") ?? "";
}

function screenModeLabel(mode: ScreenMode): string {
  const labels: Record<ScreenMode, string> = {
    idle: "Idle",
    show_qr: "QR code",
    voting_open: "Votazione aperta",
    countdown: "Countdown",
    show_results: "Risultati",
    reveal_ranking: "Reveal",
    show_podium: "Podio",
    show_final_winners: "Finale",
  };
  return labels[mode];
}

function auditActionLabel(action: string): string {
  const labels: Record<string, string> = {
    admin_event_created: "Evento creato",
    admin_event_updated: "Evento aggiornato",
    admin_event_deleted: "Evento eliminato",
    admin_competition_created: "Competizione creata",
    admin_competition_updated: "Competizione aggiornata",
    admin_competition_deleted: "Competizione eliminata",
    admin_participant_created: "Partecipante creato",
    admin_participant_updated: "Partecipante aggiornato",
    admin_participant_deleted: "Partecipante eliminato",
    admin_public_criterion_created: "Criterio pubblico creato",
    admin_public_criterion_updated: "Criterio pubblico aggiornato",
    admin_public_criterion_deleted: "Criterio pubblico eliminato",
    admin_judge_criterion_created: "Criterio giudice creato",
    admin_judge_criterion_updated: "Criterio giudice aggiornato",
    admin_judge_criterion_deleted: "Criterio giudice eliminato",
    admin_judge_created: "Giudice creato",
    admin_judge_updated: "Giudice aggiornato",
    admin_judge_deleted: "Giudice eliminato",
    admin_judge_assigned: "Giudice assegnato",
    admin_judge_access_code_regenerated: "Codice giudice rigenerato",
    admin_judge_unassigned: "Giudice rimosso",
    admin_voting_session_opened: "Votazione aperta",
    admin_voting_session_closed: "Votazione chiusa",
    admin_results_frozen: "Risultati congelati",
    admin_screen_state_updated: "Schermo aggiornato",
    public_access_granted: "Accesso pubblico",
    public_vote_submitted: "Voto pubblico",
    judge_access_granted: "Accesso giudice",
    judge_vote_submitted: "Voto giudice",
  };
  return labels[action] ?? action.replace(/_/g, " ");
}

function auditDetailsText(details: Record<string, unknown>): string {
  const entries = Object.entries(details).filter(
    ([, value]) => value !== null && value !== undefined && value !== ""
  );
  if (!entries.length) {
    return "Nessun dettaglio";
  }
  return entries
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        return `${key}: ${value.join(", ")}`;
      }
      if (typeof value === "object") {
        return `${key}: ${JSON.stringify(value)}`;
      }
      return `${key}: ${String(value)}`;
    })
    .join(" · ");
}

function auditLogMatchesQuery(log: AuditLogRead, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }
  const searchableText = [
    auditActionLabel(log.action),
    log.action,
    log.actor_type,
    log.actor_label,
    log.entity_type,
    log.entity_id,
    log.competition_id,
    auditDetailsText(log.details_json),
    new Date(log.created_at).toLocaleString(),
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase();

  return searchableText.includes(normalizedQuery);
}

function uniqueStringValues(values: string[]): string[] {
  return Array.from(new Set(values)).sort((first, second) => first.localeCompare(second));
}

function formatPublicVoteMethod(method: PublicVoteMethod): string {
  const labels: Record<PublicVoteMethod, string> = {
    single_choice: "scelta singola",
    ranked_choice: "classifica",
    criteria_rating: "valutazione per criteri",
  };
  return labels[method];
}

function formatAccessMethod(method: AccessMethod): string {
  const labels: Record<AccessMethod, string> = {
    public_link: "link pubblico",
    qr_pin: "QR + PIN",
    private_link: "link privato",
  };
  return labels[method];
}

function textPayload(screenState: ScreenStateRead | null, key: string): string {
  const value = screenState?.payload_json[key];
  return typeof value === "string" ? value : "";
}

function numberPayload(screenState: ScreenStateRead | null, key: string, fallback: number): number {
  const value = screenState?.payload_json[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function textValue(data: FormData, key: string): string {
  return String(data.get(key) ?? "").trim();
}

function numberValue(data: FormData, key: string, fallback: number): number {
  const value = Number(data.get(key));
  return Number.isFinite(value) ? value : fallback;
}

function slugValue(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function getPublicVoterToken(): string {
  const key = "contest-public-voter-token";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const token =
    typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(key, token);
  return token;
}
