from pydantic import BaseModel, ConfigDict, Field

from app.models import PublicVoteMethod


class PublicCriterionVoteInput(BaseModel):
    criterion_id: str
    score: float


class PublicCriteriaRatingInput(BaseModel):
    participant_id: str
    criteria: list[PublicCriterionVoteInput] = Field(min_length=1)


class PublicVoteSubmit(BaseModel):
    method: PublicVoteMethod
    participant_id: str | None = None
    ranked_participant_ids: list[str] | None = None
    ratings: list[PublicCriteriaRatingInput] | None = None


class PublicVoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    participant_id: str
    voting_session_id: str
    voter_account_id: str
    vote_method: PublicVoteMethod
    value: float | None
    rank_position: int | None


class PublicVoteSubmitRead(BaseModel):
    voting_session_id: str
    voter_account_id: str
    votes: list[PublicVoteRead]


class PublicVoteParticipantSummary(BaseModel):
    participant_id: str
    display_name: str
    vote_count: int


class PublicVoteSummaryRead(BaseModel):
    competition_id: str
    voting_session_id: str | None
    total_votes: int
    participants: list[PublicVoteParticipantSummary]


class SelfExclusionRead(BaseModel):
    excluded_participant_id: str | None


class VoterVotingStatusRead(BaseModel):
    voting_open: bool
    has_voted: bool
    allow_vote_update: bool
