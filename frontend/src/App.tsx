import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { participantBackdrop, publicVoteHref } from "./public-vote/publicVote";
import { podiumAssets, podiumDisplayOrder, podiumPercent } from "./screen/podium";
import { GoldDustCanvas } from "./screen/GoldDustCanvas";
import {
  clampRevealCount,
  nextRevealRank,
  previousRevealCount,
  revealTotal,
  visibleRevealedResults,
  type RevealMode,
} from "./screen/reveal";
import "./styles.css";
import { VoterAccountsTab } from "./admin/VoterAccountsTab";
import {
  Panel,
  Form,
  List,
  Badge,
  Metric,
  MiniTable,
  CriterionForm,
  CriteriaList,
  competitionNamesForJudge,
  screenModeLabel,
  auditActionLabel,
  auditDetailsText,
  auditLogMatchesQuery,
  uniqueStringValues,
  formatPublicVoteMethod,
  textPayload,
  numberPayload,
  textValue,
  numberValue,
  slugValue,
} from "./admin/components";
import { EventTab } from "./admin/EventTab";
import { CompetitionTab } from "./admin/CompetitionTab";
import { ParticipantsTab } from "./admin/ParticipantsTab";
import { CriteriaTab } from "./admin/CriteriaTab";
import { JudgesTab } from "./admin/JudgesTab";
import { ReviewTab } from "./admin/ReviewTab";
import { LiveTab } from "./admin/LiveTab";
import { ResultsTab } from "./admin/ResultsTab";
import { LogsTab } from "./admin/LogsTab";
import type {
  EventStatus,
  CompetitionStatus,
  PublicVoteMethod,
  VotingSessionStatus,
  ScreenMode,
  EventRead,
  CompetitionRead,
  ParticipantRead,
  CriterionRead,
  JudgeRead,
  JudgeAccessCodeResetRead,
  VotingSessionRead,
  ResultEntry,
  ResultsRead,
  SetupStepStatus,
  CompetitionSetupStatus,
  PublicVoteSummaryRead,
  ScreenStateRead,
  AuditLogRead,
  AuditFilters,
  AdminTab,
  AdminStep,
  AdminState,
  VoterAccountRead,
  VoterCredentialNotice,
  JudgeCredentialNotice,
} from "./admin/types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const websocketBaseUrl = apiBaseUrl.replace(/^http/, "ws");

type AppView = "admin" | "judge" | "screen";

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
  voterAccounts: [],
  allParticipants: [],
  sessions: [],
  results: null,
  setupStatus: null,
  screenState: null,
  auditLogs: [],
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
  event_not_live: "Evento non ancora live",
  missing_competitions: "Crea almeno una competizione",
};

const competitionStatusLabels: Record<string, string> = {
  draft: "Bozza",
  ready: "Pronto",
  voting_open: "Voto Aperto",
  voting_closed: "Voto Chiuso",
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
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
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
  const [voterCredentialNotice, setVoterCredentialNotice] = useState<VoterCredentialNotice | null>(null);
  const [showSeedConfirm, setShowSeedConfirm] = useState<boolean>(false);
  const [seedParticipantsCount, setSeedParticipantsCount] = useState<number>(4);
  const [seedJudgesCount, setSeedJudgesCount] = useState<number>(3);
  const [seedCriteriaCount, setSeedCriteriaCount] = useState<number>(3);
  const [auditFilters, setAuditFilters] = useState<AuditFilters>({
    query: "",
    actorType: "all",
    entityType: "all",
    action: "all",
    pageSize: 20,
    page: 1,
  });
  const [message, setMessage] = useState("Pronto");
  const [isRevealUpdating, setIsRevealUpdating] = useState(false);
  const selectedEvent = state.events.find((event) => event.id === selectedEventId);
  const selectedCompetition = state.competitions.find(
    (competition) => competition.id === selectedCompetitionId
  );
  const revealMode =
    state.screenState?.mode === "reveal_ranking" ||
    state.screenState?.mode === "show_podium"
      ? (state.screenState.mode as RevealMode)
      : null;
  const revealMaximum = revealMode
    ? revealTotal(revealMode, state.results?.results.length ?? 0)
    : 0;
  const revealedCount = clampRevealCount(
    numberPayload(state.screenState, "reveal_upto", 0),
    revealMaximum,
  );
  const upcomingRank = nextRevealRank(revealMaximum, revealedCount, revealMode);
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
  const hasAssignedJudges = state.judges.some(
    (judge) => selectedCompetition && judge.assigned_competition_ids?.includes(selectedCompetition.id)
  );
  const isUnpopulated = Boolean(
    selectedCompetition &&
      state.participants.length === 0 &&
      state.judgeCriteria.length === 0 &&
      state.publicCriteria.length === 0 &&
      !hasAssignedJudges
  );
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
      disabled: !selectedEvent,
      reason: "Seleziona evento",
    },
    {
      id: "voterAccounts",
      label: "Votanti",
      disabled: !selectedEvent,
      reason: "Seleziona evento",
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
    const [competitions, judges, voterAccounts, screenState, auditLogs] = await Promise.all([
      api<CompetitionRead[]>(`/api/events/${eventId}/competitions`),
      api<JudgeRead[]>(`/api/events/${eventId}/judges`),
      api<VoterAccountRead[]>(`/api/events/${eventId}/voter-accounts`),
      api<ScreenStateRead>(`/api/events/${eventId}/screen-state`),
      api<AuditLogRead[]>(`/api/events/${eventId}/audit-logs?limit=500`),
    ]);
    const participantsLists = await Promise.all(
      competitions.map((c) => api<ParticipantRead[]>(`/api/competitions/${c.id}/participants`))
    );
    const allParticipants = participantsLists.flat();
    setState((current) => ({
      ...current,
      competitions,
      judges,
      voterAccounts,
      participants: [],
      allParticipants,
      publicCriteria: [],
      judgeCriteria: [],
      sessions: [],
      results: null,
      screenState,
      auditLogs,
    }));
    const nextCompId = selectedCompetitionId && competitions.some((c) => c.id === selectedCompetitionId)
      ? selectedCompetitionId
      : competitions[0]?.id ?? "";

    if (nextCompId === selectedCompetitionId && nextCompId) {
      void run(() => loadCompetitionData(nextCompId), "Competizione ricaricata");
    } else {
      setSelectedCompetitionId(nextCompId);
    }
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
        max_votes_per_user: numberValue(data, "max_votes_per_user", 1),
        max_votes_per_competition: numberValue(data, "max_votes_per_competition", 1),
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

  async function seedCompetitionFakeData(numParticipants: number, numJudges: number, numCriteria: number) {
    if (!selectedCompetition) return;
    await api(`/api/competitions/${selectedCompetition.id}/seed-fake-data`, {
      method: "POST",
      body: JSON.stringify({
        num_participants: numParticipants,
        num_judges: numJudges,
        num_criteria: numCriteria,
      }),
    });
    if (selectedEventId) {
      await loadEventData(selectedEventId);
    }
    await loadCompetitionData(selectedCompetition.id);
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

  async function deleteParticipant(id: string) {
    await api(`/api/participants/${id}`, { method: "DELETE" });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function toggleParticipantActive(id: string, active: boolean) {
    await api(`/api/participants/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function deleteCriterion(id: string) {
    await api(`/api/criteria/${id}`, { method: "DELETE" });
    await refreshSelectedEvent();
    await refreshSelectedCompetition();
  }

  async function toggleCriterionActive(id: string, active: boolean) {
    await api(`/api/criteria/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    });
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

  async function deleteJudge(judgeId: string) {
    await api(`/api/judges/${judgeId}`, { method: "DELETE" });
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
    const screenState = await api<ScreenStateRead>(`/api/events/${selectedEventId}/screen-state`, {
      method: "PUT",
      body: JSON.stringify({
        competition_id: selectedCompetitionId || null,
        mode: textValue(data, "mode"),
        payload_json: {
          title: textValue(data, "title"),
          public_vote_url:
            textValue(data, "public_vote_url") ||
            (selectedCompetitionId
              ? `${window.location.origin}${publicVoteHref(selectedCompetitionId)}`
              : ""),
          countdown_seconds: numberValue(data, "countdown_seconds", 90),
          reveal_upto: numberValue(data, "reveal_upto", 0),
        },
      }),
    });
    setState((current) => ({ ...current, screenState }));
  }

  async function updateRevealCount(nextCount: number) {
    if (!selectedEventId || !state.screenState || !revealMode) return;
    setIsRevealUpdating(true);
    try {
      const screenState = await api<ScreenStateRead>(
        `/api/events/${selectedEventId}/screen-state`,
        {
          method: "PUT",
          body: JSON.stringify({
            competition_id: selectedCompetitionId || null,
            mode: state.screenState.mode,
            payload_json: {
              ...state.screenState.payload_json,
              reveal_upto: clampRevealCount(nextCount, revealMaximum),
            },
          }),
        },
      );
      setState((current) => ({ ...current, screenState }));
    } finally {
      setIsRevealUpdating(false);
    }
  }

  return (
    <main className={`admin-shell admin-shell-${view}`}>
      <header className="topbar">
        <div>
          <p className="eyebrow">Contest Voting Platform</p>
          <h1>
            {view === "admin" ? "Admin serata" : view === "judge" ? "Giudici" : "Schermo pubblico"}
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

      {view === "judge" ? (
        <JudgeArea setMessage={setMessage} />
      ) : view === "screen" ? (
        <ScreenArea setMessage={setMessage} />
      ) : (
      <section className="workspace">
        <aside className="rail">
          <EventTab
            events={state.events}
            selectedEventId={selectedEventId}
            onSelect={setSelectedEventId}
            onDelete={setDeleteEventCandidate}
            onCreate={(form) => run(() => createEvent(form), "Evento creato")}
          />
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
            <CompetitionTab
              competitions={state.competitions}
              selectedCompetitionId={selectedCompetitionId}
              selectedEventId={selectedEventId}
              configurationLocked={configurationLocked}
              onSelect={setSelectedCompetitionId}
              onDelete={setDeleteCompetitionCandidate}
              onCreate={(form) => run(() => createCompetition(form), "Competizione creata")}
              sessions={state.sessions}
            />
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

                {selectedEvent && (
                  <div className="event-id-box" style={{
                    marginTop: "20px",
                    padding: "16px",
                    background: "rgba(214, 157, 67, 0.06)",
                    border: "1px solid rgba(214, 157, 67, 0.15)",
                    borderRadius: "8px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
                      <div style={{ flex: "1 1 300px" }}>
                        <span style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.5px", opacity: 0.7, display: "block", marginBottom: "4px" }}>
                          ID Evento (UUID)
                        </span>
                        <code style={{ fontSize: "0.95rem", color: "#d69d43", wordBreak: "break-all", fontFamily: "monospace" }}>
                          {selectedEvent.id}
                        </code>
                      </div>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          type="button"
                          className="secondary-button"
                          style={{ padding: "6px 12px", fontSize: "0.85rem" }}
                          onClick={() => {
                            void navigator.clipboard.writeText(selectedEvent.id);
                            setMessage("ID Evento copiato negli appunti!");
                          }}
                        >
                          Copia ID
                        </button>
                        <button
                          type="button"
                          style={{ padding: "6px 12px", fontSize: "0.85rem" }}
                          onClick={() => {
                            const voteUrl = `${window.location.origin}/vote?eventId=${selectedEvent.id}`;
                            void navigator.clipboard.writeText(voteUrl);
                            setMessage("Link voto pubblico copiato!");
                          }}
                        >
                          Copia Link Voto
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {selectedEvent?.status === "draft" ? (
                  <div className="button-strip" style={{ marginTop: "20px" }}>
                    <button
                      type="button"
                      disabled={!setupReady}
                      onClick={() => run(goEventLive, "Evento live")}
                    >
                      Porta evento live
                    </button>
                  </div>
                ) : (
                  <p className="lock-note" style={{ marginTop: "20px" }}>Evento live o chiuso: setup bloccato, gestione live attiva.</p>
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
                  <Metric label="Peso pubblico" value={selectedCompetition.public_weight} />
                  <Metric label="Peso giudici" value={selectedCompetition.judge_weight} />
                  <Metric label="Partecipanti attivi" value={activeParticipantsCount} />
                </div>
              </Panel>
              ) : null}

              {adminTab === "participants" ? (
                <ParticipantsTab
                  participants={state.participants}
                  competitionId={selectedCompetitionId}
                  configurationLocked={configurationLocked}
                  onAdd={(form) => run(() => createParticipant(form), "Partecipante aggiunto")}
                  onToggleActive={(id, active) => run(() => toggleParticipantActive(id, active), "Stato partecipante aggiornato")}
                  onDelete={(id) => run(() => deleteParticipant(id), "Partecipante eliminato")}
                  voterAccounts={state.voterAccounts}
                />
              ) : null}

              {adminTab === "publicCriteria" ? (
                <CriteriaTab
                  criteria={state.publicCriteria}
                  type="public"
                  competitionId={selectedCompetitionId}
                  configurationLocked={configurationLocked}
                  onAdd={(form) => run(() => createCriterion(form, "public"), "Criterio aggiunto")}
                  onToggleActive={(id, active) => run(() => toggleCriterionActive(id, active), "Stato criterio aggiornato")}
                  onDelete={(id) => run(() => deleteCriterion(id), "Criterio eliminato")}
                  required={publicCriteriaRequired}
                  emptyMessage="Non richiesti per metodo pubblico corrente."
                />
              ) : null}

              {adminTab === "judgeCriteria" ? (
                <CriteriaTab
                  criteria={state.judgeCriteria}
                  type="judge"
                  competitionId={selectedCompetitionId}
                  configurationLocked={configurationLocked}
                  onAdd={(form) => run(() => createCriterion(form, "judge"), "Criterio aggiunto")}
                  onToggleActive={(id, active) => run(() => toggleCriterionActive(id, active), "Stato criterio aggiornato")}
                  onDelete={(id) => run(() => deleteCriterion(id), "Criterio eliminato")}
                  required={judgeSetupRequired}
                  emptyMessage="Non richiesti se voto giudici disattivato."
                />
              ) : null}

              {adminTab === "judges" ? (
                <JudgesTab
                  judges={state.judges}
                  competitions={state.competitions}
                  eventId={selectedEventId}
                  configurationLocked={configurationLocked}
                  onAdd={(form) => run(() => createJudge(form), "Giudice creato")}
                  onDelete={(id) => run(() => deleteJudge(id), "Giudice eliminato")}
                  onToggleCompetition={(judgeId, competitionId, isAssigned) =>
                    run(
                      () => toggleJudgeCompetition(judgeId, competitionId, isAssigned),
                      isAssigned
                        ? "Giudice rimosso"
                        : "Giudice assegnato"
                    )
                  }
                  onRegenerateCode={(judgeId) => run(() => regenerateJudgeAccessCode(judgeId), "Codice giudice rigenerato")}
                  judgeCredentialNotice={judgeCredentialNotice}
                />
              ) : null}

              {adminTab === "voterAccounts" && selectedEventId ? (
                <Panel title="Account votanti">
                  <VoterAccountsTab
                    eventId={selectedEventId}
                    competitions={state.competitions}
                    participants={state.allParticipants}
                    voterAccounts={state.voterAccounts}
                    configurationLocked={configurationLocked}
                    onChanged={() => loadEventData(selectedEventId)}
                    onCredential={setVoterCredentialNotice}
                  />
                </Panel>
              ) : null}

              {adminTab === "review" ? (
                <ReviewTab
                  setupStatus={state.setupStatus}
                  competition={selectedCompetition}
                  selectedEvent={selectedEvent ?? null}
                  isUnpopulated={isUnpopulated}
                  setupReady={setupReady}
                  canOpenVoting={canOpenVoting}
                  onPopolaFakeData={() => setShowSeedConfirm(true)}
                />
              ) : null}

              {adminTab === "live" ? (
                <LiveTab
                  competition={selectedCompetition}
                  event={selectedEvent ?? null}
                  sessions={state.sessions}
                  setupStatus={state.setupStatus}
                  canOpenVoting={canOpenVoting}
                  isEventLive={isEventLive}
                  setupReady={setupReady}
                  onGoLive={() => run(goEventLive, "Evento live")}
                  onOpenVoting={(form) => run(() => openVoting(form), "Votazione aperta")}
                  onCloseVoting={() => run(closeVoting, "Votazione chiusa")}
                />
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
                    <option value="countdown">Countdown</option>
                    <option value="reveal_ranking">Reveal classifica</option>
                    <option value="show_podium">Podio</option>
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
                      `${window.location.origin}${publicVoteHref(selectedCompetitionId)}`
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
                {revealMode ? (
                  <div className="reveal-controls">
                    <p>
                      Rivelate {revealedCount} di {revealMaximum}
                      {upcomingRank
                        ? ` — prossima: posizione ${upcomingRank}`
                        : " — sequenza completata"}
                    </p>
                    <div className="button-strip">
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isRevealUpdating || revealedCount === 0}
                        onClick={() =>
                          run(() => updateRevealCount(0), "Rivelazione azzerata")
                        }
                      >
                        Azzera
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={isRevealUpdating || revealedCount === 0}
                        onClick={() =>
                          run(
                            () =>
                              updateRevealCount(
                                previousRevealCount(revealedCount, revealMaximum),
                              ),
                            "Posizione nascosta",
                          )
                        }
                      >
                        Indietro
                      </button>
                      <button
                        type="button"
                        disabled={isRevealUpdating || revealedCount >= revealMaximum}
                        onClick={() =>
                          run(
                            () => updateRevealCount(revealedCount + 1),
                            "Posizione rivelata",
                          )
                        }
                      >
                        Rivela prossima
                      </button>
                    </div>
                  </div>
                ) : null}
                <div className="metrics">
                  <Metric label="Modalita" value={screenModeLabel(state.screenState?.mode ?? "idle")} />
                  <Metric label="Competizione" value={selectedCompetition.name} />
                </div>
              </Panel>
              ) : null}

              {adminTab === "results" ? (
                <ResultsTab
                  results={state.results}
                  competition={selectedCompetition}
                  onRefresh={() => run(refreshSelectedCompetition, "Risultati aggiornati")}
                />
              ) : null}

              {adminTab === "logs" ? (
                <LogsTab
                  auditLogs={state.auditLogs}
                  filters={auditFilters}
                  onFiltersChange={setAuditFilters}
                />
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
      {showSeedConfirm ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="confirm-modal" role="dialog" style={{ maxWidth: "450px" }}>
            <h2>Popola con Dati Fake</h2>
            <p style={{ marginBottom: "15px", fontSize: "0.9rem", opacity: 0.8 }}>
              Imposta le quantità di dati fittizi da generare per questa competizione. I partecipanti avranno nomi e cognomi completi (es. Sofia Ferrari).
            </p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "20px", textAlign: "left" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ fontSize: "0.85rem", fontWeight: "bold" }}>Numero di Partecipanti (1-100):</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={seedParticipantsCount}
                  onChange={(e) => setSeedParticipantsCount(Math.min(100, Math.max(1, parseInt(e.target.value) || 1)))}
                  style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #c7d0d9", background: "white", color: "black" }}
                />
              </div>

              {selectedCompetition?.judge_voting_enabled && (
                <>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <label style={{ fontSize: "0.85rem", fontWeight: "bold" }}>Numero di Giudici da assegnare (1-50):</label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      value={seedJudgesCount}
                      onChange={(e) => setSeedJudgesCount(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
                      style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #c7d0d9", background: "white", color: "black" }}
                    />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <label style={{ fontSize: "0.85rem", fontWeight: "bold" }}>Numero di Criteri Giudici (1-20):</label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={seedCriteriaCount}
                      onChange={(e) => setSeedCriteriaCount(Math.min(20, Math.max(1, parseInt(e.target.value) || 1)))}
                      style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #c7d0d9", background: "white", color: "black" }}
                    />
                  </div>
                </>
              )}

              {selectedCompetition?.public_voting_enabled && selectedCompetition.public_vote_method === "criteria_rating" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <label style={{ fontSize: "0.85rem", fontWeight: "bold" }}>Numero di Criteri Pubblici (1-20):</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={seedCriteriaCount}
                    onChange={(e) => setSeedCriteriaCount(Math.min(20, Math.max(1, parseInt(e.target.value) || 1)))}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #c7d0d9", background: "white", color: "black" }}
                  />
                </div>
              )}
            </div>

            <p style={{ fontSize: "0.8rem", color: "#666", marginBottom: "15px" }}>
              <strong>Nota:</strong> Questa operazione è possibile solo perché la competizione è vuota.
            </p>

            <div className="button-strip">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setShowSeedConfirm(false)}
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSeedConfirm(false);
                  void run(
                    () => seedCompetitionFakeData(seedParticipantsCount, seedJudgesCount, seedCriteriaCount),
                    "Competizione popolata con dati fake"
                  );
                }}
              >
                Conferma e Popola
              </button>
            </div>
          </section>
        </div>
      ) : null}
      {voterCredentialNotice && (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="confirm-modal" role="dialog" style={{ maxWidth: "450px" }}>
            <h2>Codice accesso</h2>
            <p>
              <strong>{voterCredentialNotice.displayName}</strong>
            </p>
            <p className="form-hint" style={{ color: "#79351f", fontWeight: "bold" }}>
              Copia questo codice subito: non sarà più recuperabile.
            </p>
            <code className="access-code-display" style={{ display: "block", fontSize: "1.5rem", padding: "10px", background: "#f0f0f0", borderRadius: "6px", margin: "14px 0", textAlign: "center", letterSpacing: "1px", color: "black" }}>{voterCredentialNotice.accessCode}</code>
            <div className="button-strip">
              <button type="button" onClick={() => setVoterCredentialNotice(null)}>
                Ho copiato il codice
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function StatusCapsules({
  mode,
  isRevealed,
  isOpen,
  lastUpdated,
}: {
  mode: string;
  isRevealed: boolean;
  isOpen: boolean;
  lastUpdated?: string;
}) {
  return (
    <div className="stage-status-capsules">
      {isOpen ? (
        <span className="capsule capsule-voting">
          <img src="/quasanremo/schermo/live_signal.png" alt="" />
          Votazione in corso
        </span>
      ) : (
        <span className="capsule capsule-closed">
          <img src="/quasanremo/schermo/lock_gold.png" alt="" />
          Votazione chiusa
        </span>
      )}

      {isRevealed ? (
        <span className="capsule capsule-official">
          <img src="/quasanremo/schermo/official_results.png" alt="" />
          Risultati ufficiali
        </span>
      ) : (
        <span className="capsule capsule-live">
          <span className="live-dot"></span>
          Aggiornamento live
        </span>
      )}

      {lastUpdated ? (
        <span className="capsule capsule-time">
          <img src="/quasanremo/schermo/clock_gold.png" alt="" />
          Ultimo aggiornamento {lastUpdated}
        </span>
      ) : null}
    </div>
  );
}

function WreathBadge({ rank }: { rank: number }) {
  if (rank >= 1 && rank <= 6) {
    return (
      <img
        src={`/quasanremo/schermo/rank_badge_${rank}.png`}
        className={`rank-badge-img rank-badge-${rank}`}
        alt={`Posizione ${rank}`}
      />
    );
  }

  return <span className="rank-text">{rank}</span>;
}

function getMockTrend(id: string) {
  const hash = id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const mod = hash % 3;
  if (mod === 0) return { dir: "up" as const, val: "+1" };
  if (mod === 1) return { dir: "down" as const, val: "-1" };
  return { dir: "neutral" as const, val: "—" };
}

function IdleFogBackground() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    let effect: { destroy: () => void } | null = null;

    async function startFog() {
      const [{ default: FOG }, THREE] = await Promise.all([
        import("vanta/dist/vanta.fog.min"),
        import("three"),
      ]);

      if (cancelled || !containerRef.current) return;

      effect = FOG({
        el: containerRef.current,
        THREE,
        mouseControls: false,
        touchControls: false,
        gyroControls: false,
        minHeight: 420,
        minWidth: 420,
        highlightColor: 0xffe2a1,
        midtoneColor: 0x9a6c2e,
        lowlightColor: 0x050506,
        baseColor: 0x090806,
        blurFactor: 0.42,
        speed: 1.15,
        zoom: 0.74,
      });
    }

    void startFog();

    return () => {
      cancelled = true;
      effect?.destroy();
    };
  }, []);

  return <div className="idle-fog-background" ref={containerRef} aria-hidden="true" />;
}

function ScreenArea({ setMessage }: { setMessage: (message: string) => void }) {
  const [state, setState] = useState<ScreenAreaState>({
    ...emptyScreenAreaState,
    eventId: initialEventIdFromUrl(),
  });
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [lastUpdatedTime, setLastUpdatedTime] = useState("");

  const openSession = state.sessions.find((session) => session.status === "open");
  const title =
    textPayload(state.screenState, "title") ||
    state.competition?.name ||
    "Contest Voting Platform";
  const countdownSeconds = numberPayload(state.screenState, "countdown_seconds", 0);
  const allRanking = state.results?.results ?? [];
  const screenRevealMode =
    state.screenState?.mode === "reveal_ranking" ||
    state.screenState?.mode === "show_podium"
      ? (state.screenState.mode as RevealMode)
      : null;
  const screenRevealCount = numberPayload(state.screenState, "reveal_upto", 0);
  const ranking =
    screenRevealMode === "reveal_ranking"
      ? visibleRevealedResults(allRanking, screenRevealMode, screenRevealCount)
      : allRanking;
  const podiumMode = state.screenState?.mode === "show_podium";
  const visiblePodium =
    screenRevealMode === "show_podium"
      ? visibleRevealedResults(allRanking, screenRevealMode, screenRevealCount)
      : allRanking.slice(0, 3);
  const totalFinalScore = allRanking.reduce((total, result) => total + result.final_score, 0);
  const maxScore = Math.max(...allRanking.map((result) => result.final_score), 1);

  let headingTitle = textPayload(state.screenState, "title");
  let headingSubtitle = textPayload(state.screenState, "subtitle");

  if (!headingTitle) {
    const mode = state.screenState?.mode;
    if (mode === "show_podium") {
      headingTitle = "Podio finale";
    } else if (mode === "countdown") {
      headingTitle = "Sessione di voto";
    } else {
      headingTitle = "";
    }
  }

  if (!headingSubtitle) {
    const mode = state.screenState?.mode;
    if (mode === "show_podium" || mode === "countdown") {
      headingSubtitle = "";
    } else {
      headingSubtitle = "";
    }
  }

  const countdownValue = Math.max(0, remainingSeconds ?? countdownSeconds);
  const countdownMinutes = Math.floor(countdownValue / 60);
  const countdownRemainder = countdownValue % 60;
  const countdownLabel =
    countdownMinutes > 0
      ? `${countdownMinutes}:${String(countdownRemainder).padStart(2, "0")}`
      : String(countdownRemainder);

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

  useEffect(() => {
    if (state.screenState) {
      setLastUpdatedTime(new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }));
    }
  }, [state.screenState, state.results, state.summary]);

  return (
    <section className={`screen-shell ${state.activeEventId ? "screen-shell-connected" : ""}`}>
      {!state.activeEventId ? (
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
      ) : null}

      <section className={`stage stage-${state.screenState?.mode ?? "idle"}`}>
        {state.screenState?.mode === "show_podium" ? (
          <GoldDustCanvas />
        ) : null}
        {(state.screenState?.mode === "idle" || !state.screenState) ? (
          <IdleFogBackground />
        ) : null}
        <div className="stage-decor-frame" />

        <div className="stage-header">
          <div className="stage-brand">
            <img src="/quasanremo/brand/quasanremo_logo.png" className="stage-brand-logo" alt="Logo" />
            <img src="/quasanremo/brand/logo-rectangular-transparent.png" className="stage-brand-wordmark" alt="Quasanremo International" />
          </div>
          <div className="stage-header-center">
            <svg viewBox="0 0 24 24" className="stage-center-star" aria-hidden="true">
              <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
            </svg>
          </div>
          {!podiumMode ? (
            <StatusCapsules
              mode={state.screenState?.mode ?? "idle"}
              isRevealed={state.competition?.status === "revealed"}
              isOpen={Boolean(openSession)}
              lastUpdated={lastUpdatedTime}
            />
          ) : null}
        </div>

        <div className="stage-heading">
          <p>{headingSubtitle}</p>
          <h2>{headingTitle}</h2>
        </div>

        <div className="stage-content">
          {state.screenState?.mode === "countdown" ? (
            <div className="countdown-stage">
              <div className="countdown-orbit" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div className="countdown-main">
                <strong className="countdown-number">{countdownLabel}</strong>
                <span className="countdown-unit">
                  {countdownMinutes > 0 ? "minuti" : "secondi"}
                </span>
              </div>
              <div className="countdown-meta">
                <div>
                  <span>Voti ricevuti</span>
                  <strong>{state.summary?.total_votes ?? 0}</strong>
                </div>
                <div>
                  <span>Sessione</span>
                  <strong>{openSession ? "Aperta" : "In attesa..."}</strong>
                </div>
              </div>
            </div>
          ) : null}

          {state.screenState?.mode === "reveal_ranking" ? (
            ranking.length === 0 ? (
              <div className="stage-idle">In attesa della prossima posizione.</div>
            ) : (
              <ol className="stage-ranking">
              {ranking.map((result, idx) => {
                const trend = getMockTrend(result.participant_id);
                const totalFinalScore = allRanking.reduce((acc, r) => acc + r.final_score, 0) || 1;
                const percent = ((result.final_score / totalFinalScore) * 100).toFixed(2).replace('.', ',');
                const votes = result.public_votes || Math.round(result.final_score * 3.5);

                return (
                  <li key={result.participant_id} className={`rank-item-${result.rank}`}>
                    <div className="rank-position-col">
                      <WreathBadge rank={result.rank} />
                      <div className={`trend-indicator trend-${trend.dir}`}>
                        {trend.dir === "up" && <img src="/quasanremo/schermo/trend_up_plus_1.png" className="trend-icon" alt="+1" />}
                        {trend.dir === "down" && <img src="/quasanremo/schermo/trend_down_minus_1.png" className="trend-icon" alt="-1" />}
                        {trend.dir === "neutral" && <img src="/quasanremo/schermo/rank_stable.png" className="trend-icon" alt="stabile" />}
                      </div>
                    </div>
                    <div
                      className="rank-avatar"
                      style={{ backgroundImage: `url(/quasanremo/artists/artist-bg-0${(idx % 5) + 1}.webp)` }}
                    />
                    <strong className="rank-name">{result.display_name}</strong>
                    <div className="rank-progress-col">
                      <div className="rank-votes-bar">
                        <i
                          className="rank-progress-fill"
                          style={{ width: `${Math.max(8, (result.final_score / maxScore) * 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className="rank-votes-count">{votes.toLocaleString("it-IT")} Voti</span>
                    <span className="rank-percent">{percent}%</span>
                  </li>
                );
              })}
              </ol>
            )
          ) : null}

          {state.screenState?.mode === "show_podium" ? (
            <div className="podium-section">
              {visiblePodium.length ? (
                <div className="podium">
                  {[2, 1, 3].map((rank) => {
                    const result = visiblePodium.find((r) => r.rank === rank);
                    if (!result) return null;

                    const index = allRanking.findIndex(
                      (entry) => entry.participant_id === result.participant_id,
                    );
                    const assets = podiumAssets(result.rank);

                    return (
                      <article className={`podium-place podium-${result.rank}`} key={result.participant_id}>
                        <div className="podium-portrait">
                          <div
                            className="podium-card-artist-bg"
                            style={{ backgroundImage: `url(${participantBackdrop(index)})` }}
                          />
                          <div className="podium-card-shade" />
                          <img className="podium-panel-asset" src={assets.panel} alt="" />
                          <div className="podium-card-content">
                            <strong className="podium-name" title={result.display_name}>
                              {result.display_name}
                            </strong>
                            <span className="podium-score-capsule">
                              {podiumPercent(result.final_score, totalFinalScore)}%
                            </span>
                          </div>
                        </div>
                        <img className="podium-base-asset" src={assets.base} alt="" />
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="podium-empty">In attesa della prossima posizione.</div>
              )}

              {allRanking.length > 3 ? (
                <div className="podium-runners-up">
                  {[4, 5].map((rank) => {
                    const result = allRanking.find((r) => r.rank === rank);
                    if (!result) return null;

                    const isRevealed = visiblePodium.some((r) => r.participant_id === result.participant_id);
                    const indexInAll = allRanking.findIndex((r) => r.participant_id === result.participant_id);

                    return (
                      <article
                        key={result.participant_id}
                        className="runner-up-item"
                        style={{ visibility: isRevealed ? "visible" : "hidden" }}
                      >
                        <span className="runner-up-rank">{result.rank}</span>
                        <span
                          className="runner-up-avatar"
                          style={{ backgroundImage: `url(${participantBackdrop(indexInAll)})` }}
                        />
                        <span className="runner-up-name" title={result.display_name}>
                          {result.display_name}
                        </span>
                        <span className="runner-up-score">
                          {podiumPercent(result.final_score, totalFinalScore)}%
                        </span>
                      </article>
                    );
                  })}
                </div>
              ) : null}

              <p className="podium-footer">
                ☆ Grazie a tutti i partecipanti e al pubblico che ha reso possibile questa edizione. ☆
              </p>
            </div>
          ) : null}

          {(state.screenState?.mode === "idle" || !state.screenState) ? (
            <div className="stage-idle-show">
              <div className="idle-show-motion" aria-hidden="true">
                <span className="idle-sweep idle-sweep-a" />
                <span className="idle-sweep idle-sweep-b" />
                <span className="idle-spark idle-spark-1" />
                <span className="idle-spark idle-spark-2" />
                <span className="idle-spark idle-spark-3" />
                <span className="idle-spark idle-spark-4" />
                <span className="idle-spark idle-spark-5" />
                <span className="idle-spark idle-spark-6" />
              </div>
              <div className="idle-show-content">
                <img
                  src="/quasanremo/brand/quasanremo_logo.png"
                  className="idle-show-logo"
                  alt="Quasanremo"
                />
                <p>La serata sta per continuare</p>
                <h3>{state.competition?.name ?? "Benvenuti alla serata"}</h3>
              </div>
            </div>
          ) : null}
        </div>
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
              {isVoteDirty(
                state.selectedParticipantId,
                state.savedVotes,
                state.criteriaScores,
                state.judgeCriteria
              ) ? (
                <div className="closed-state" style={{ margin: "12px 0", borderStyle: "dashed" }}>
                  ⚠️ Attenzione: le modifiche o i voti inseriti per questo partecipante non sono ancora validi. Clicca su &quot;Salva voto partecipante&quot; per caricarli.
                </div>
              ) : null}
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

function isVoteDirty(
  selectedParticipantId: string,
  savedVotes: Record<string, SavedJudgeVote>,
  criteriaScores: Record<string, number>,
  judgeCriteria: CriterionRead[]
): boolean {
  const saved = savedVotes[selectedParticipantId];
  if (!saved) {
    return true;
  }
  for (const criterion of judgeCriteria) {
    const currentScore = criteriaScores[criterion.id] ?? criterion.min_score;
    const savedScore = saved.scores[criterion.id];
    if (savedScore === undefined || currentScore !== savedScore) {
      return true;
    }
  }
  return false;
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



function initialViewFromUrl(): AppView {
  const view = new URLSearchParams(window.location.search).get("view");
  return view === "judge" || view === "screen" ? view : "admin";
}

function initialEventIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get("eventId") ?? "";
}
