from pydantic import BaseModel, ConfigDict, Field

from app.models import CompetitionStatus, PublicVoteMethod, VotingSessionStatus


class JudgeAccessRequest(BaseModel):
    judge_id: str = Field(min_length=1, max_length=36)
    access_code: str = Field(min_length=1, max_length=255)


class JudgeAccessCompetitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    public_vote_method: PublicVoteMethod
    judge_voting_enabled: bool
    status: CompetitionStatus


class JudgeAccessRead(BaseModel):
    judge_id: str
    display_name: str
    competitions: list[JudgeAccessCompetitionRead]


class JudgeCriterionVoteInput(BaseModel):
    criterion_id: str = Field(min_length=1, max_length=36)
    score: float


class JudgeVoteSubmit(BaseModel):
    judge_id: str = Field(min_length=1, max_length=36)
    access_code: str = Field(min_length=1, max_length=255)
    participant_id: str = Field(min_length=1, max_length=36)
    criteria: list[JudgeCriterionVoteInput] = Field(min_length=1)


class JudgeVoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    participant_id: str
    judge_id: str
    voting_session_id: str


class JudgeCriterionVoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_id: str
    score: float


class JudgeVoteDetailRead(JudgeVoteRead):
    criterion_votes: list[JudgeCriterionVoteRead]


class JudgeVoteStatusRead(BaseModel):
    competition_id: str
    judge_id: str
    voting_session_id: str | None
    voting_session_status: VotingSessionStatus | None
    total_participants: int
    voted_participants: int
    completed: bool
