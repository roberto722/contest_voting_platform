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

export type VoterSession = {
  voterAccountId: string;
  accessToken: string;
  displayName: string;
  eventId: string;
};

const NS = "cvp-voter";
const KEYS = {
  accountId: `${NS}-account-id`,
  accessToken: `${NS}-access-token`,
  displayName: `${NS}-display-name`,
  eventId: `${NS}-event-id`,
} as const;

export function saveVoterSession(session: VoterSession): void {
  localStorage.setItem(KEYS.accountId, session.voterAccountId);
  localStorage.setItem(KEYS.accessToken, session.accessToken);
  localStorage.setItem(KEYS.displayName, session.displayName);
  localStorage.setItem(KEYS.eventId, session.eventId);
}

export function loadVoterSession(): VoterSession | null {
  const voterAccountId = localStorage.getItem(KEYS.accountId);
  const accessToken = localStorage.getItem(KEYS.accessToken);
  const displayName = localStorage.getItem(KEYS.displayName);
  const eventId = localStorage.getItem(KEYS.eventId);
  if (!voterAccountId || !accessToken || !displayName || !eventId) return null;
  return { voterAccountId, accessToken, displayName, eventId };
}

export function clearVoterSession(): void {
  Object.values(KEYS).forEach((k) => localStorage.removeItem(k));
}

export function voterAuthHeaders(session: VoterSession): Record<string, string> {
  return {
    "X-Voter-Account-Id": session.voterAccountId,
    "X-Voter-Access-Token": session.accessToken,
  };
}

export function isPublicVotePath(pathname: string): boolean {
  return pathname === "/vote" || pathname === "/vote/";
}

export function publicVoteHref(eventId: string): string {
  return `/vote?eventId=${encodeURIComponent(eventId)}`;
}

export function getVotingState(sessions: Array<{ status: string }>): VotingState {
  if (sessions.some((s) => s.status === "open")) return "open";
  return sessions.length ? "closed" : "waiting";
}

export function participantBackdrop(index: number): string {
  const assetNumber = String((index % 5) + 1).padStart(2, "0");
  return `/quasanremo/artists/artist-bg-${assetNumber}.webp`;
}

/**
 * Builds the vote payload for the backend — no voter_token, auth goes in headers.
 */
export function buildVotePayload(method: PublicVoteMethod, selection: VoteSelection, maxVotes?: number) {
  if (method === "single_choice") {
    if (maxVotes && maxVotes > 1) {
      return { method, ranked_participant_ids: selection.rankedParticipantIds.filter(Boolean) };
    }
    return { method, participant_id: selection.participantId };
  }
  if (method === "ranked_choice") {
    return { method, ranked_participant_ids: selection.rankedParticipantIds.filter(Boolean) };
  }
  // criteria_rating
  return {
    method,
    ratings: [{ participant_id: selection.participantId, criteria: selection.ratings }],
  };
}
