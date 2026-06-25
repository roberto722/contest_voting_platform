// frontend/src/admin/types.ts

export type EventStatus = "draft" | "live" | "closed" | "archived";
export type CompetitionStatus =
  | "draft"
  | "ready"
  | "voting_open"
  | "voting_closed"
  | "revealed";
export type PublicVoteMethod = "single_choice" | "ranked_choice" | "criteria_rating";
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
  max_votes_per_user: number;
  max_votes_per_competition: number;
  allow_vote_update: boolean;
  status: CompetitionStatus;
};

export type ParticipantRead = {
  id: string;
  competition_id: string;
  name: string;
  display_name: string;
  description: string | null;
  image_url: string | null;
  performance_title: string | null;
  order_index: number;
  active: boolean;
  voter_account_id: string | null;
};

export type CriterionRead = {
  id: string;
  competition_id: string;
  name: string;
  description: string | null;
  min_score: number;
  max_score: number;
  weight: number;
  order_index: number;
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
  competition_id: string;
  label: string | null;
  status: VotingSessionStatus;
  opened_at: string | null;
  closed_at: string | null;
  opened_by_admin_id: string | null;
  closed_by_admin_id: string | null;
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
  allParticipants: ParticipantRead[];
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
