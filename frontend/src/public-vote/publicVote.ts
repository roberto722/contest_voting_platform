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
