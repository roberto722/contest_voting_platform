type Identified = { id: string };
type Criterion = { id: string; min_score: number };
type SavedVote = { scores?: Record<string, number> };

export function canOpenJudgeScoreSheet(participantId: string): boolean {
  return participantId.trim().length > 0;
}

export function nextJudgeParticipantId<T extends Identified>(
  participants: T[],
  savedVotes: Record<string, unknown>,
  currentParticipantId: string,
): string {
  return participants.find((participant) => !savedVotes[participant.id])?.id ?? currentParticipantId;
}

export function scoresForParticipant<T extends Criterion>(
  criteria: T[],
  savedVotes: Record<string, SavedVote>,
  participantId: string,
): Record<string, number> {
  const saved = savedVotes[participantId];
  return Object.fromEntries(
    criteria.map((criterion) => [
      criterion.id,
      saved?.scores?.[criterion.id] ?? criterion.min_score,
    ]),
  );
}

export function stateAfterSavedJudgeVote<TParticipant extends Identified, TCriterion extends Criterion>(
  participants: TParticipant[],
  criteria: TCriterion[],
  savedVotes: Record<string, SavedVote>,
  currentParticipantId: string,
): { selectedParticipantId: string; criteriaScores: Record<string, number> } {
  const selectedParticipantId = nextJudgeParticipantId(
    participants,
    savedVotes,
    currentParticipantId,
  );
  return {
    selectedParticipantId,
    criteriaScores: scoresForParticipant(criteria, savedVotes, selectedParticipantId),
  };
}
