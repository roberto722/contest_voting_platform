from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    CompetitionStatus,
    EventStatus,
    PublicVoteMethod,
    VotingSessionStatus,
)


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: EventStatus | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: EventStatus


class CompetitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    public_voting_enabled: bool = True
    judge_voting_enabled: bool = True
    public_vote_method: PublicVoteMethod = PublicVoteMethod.SINGLE_CHOICE
    public_weight: float = 50
    judge_weight: float = 50
    max_votes_per_user: int = 1
    max_votes_per_competition: int = 1
    allow_vote_update: bool = False


class CompetitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    public_voting_enabled: bool | None = None
    judge_voting_enabled: bool | None = None
    public_vote_method: PublicVoteMethod | None = None
    public_weight: float | None = None
    judge_weight: float | None = None
    max_votes_per_user: int | None = None
    max_votes_per_competition: int | None = None
    allow_vote_update: bool | None = None


class CompetitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    name: str
    description: str | None
    type: str | None
    public_voting_enabled: bool
    judge_voting_enabled: bool
    public_vote_method: PublicVoteMethod
    public_weight: float
    judge_weight: float
    max_votes_per_user: int
    max_votes_per_competition: int
    allow_vote_update: bool
    status: CompetitionStatus


class SetupStepStatus(BaseModel):
    step: str
    completed: bool
    message: str


class CompetitionSetupStatus(BaseModel):
    competition_id: str
    event_id: str
    is_ready: bool
    can_open_voting: bool
    completed_steps: list[str]
    missing_steps: list[str]
    issues: list[str]
    open_issues: list[str]
    messages: list[str]
    checks: list[SetupStepStatus]


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    performance_title: str | None = None
    order_index: int = 0
    active: bool = True
    voter_account_ids: list[str] = Field(default_factory=list)


class ParticipantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    performance_title: str | None = None
    order_index: int | None = None
    active: bool | None = None
    voter_account_ids: list[str] | None = None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    name: str
    display_name: str
    description: str | None
    image_url: str | None
    performance_title: str | None
    order_index: int
    active: bool
    voter_account_id: str | None = None
    voter_account_ids: list[str] = Field(default_factory=list)


class CriterionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    min_score: float = 1
    max_score: float = 10
    weight: float = 1
    order_index: int = 0
    active: bool = True


class CriterionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    min_score: float | None = None
    max_score: float | None = None
    weight: float | None = None
    order_index: int | None = None
    active: bool | None = None


class CriterionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    name: str
    description: str | None
    min_score: float
    max_score: float
    weight: float
    order_index: int
    active: bool


class JudgeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    access_code: str = Field(min_length=1, max_length=255)
    active: bool = True


class JudgeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    access_code: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None


class JudgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    name: str
    display_name: str
    active: bool
    assigned_competition_ids: list[str] = Field(default_factory=list)


class JudgeAccessCodeResetRead(BaseModel):
    judge: JudgeRead
    access_code: str


class CompetitionJudgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    judge_id: str
    active: bool


class VotingSessionCreate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    opened_by_admin_id: str | None = Field(default=None, max_length=36)
    channels: list[str] | None = None


class VotingSessionClose(BaseModel):
    closed_by_admin_id: str | None = Field(default=None, max_length=36)
    channels: list[str] | None = None


class VotingSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    label: str | None
    status: VotingSessionStatus
    public_voting_open: bool
    judge_voting_open: bool
    opened_at: datetime | None
    closed_at: datetime | None
    opened_by_admin_id: str | None
    closed_by_admin_id: str | None


class CompetitionSeedFakeData(BaseModel):
    num_participants: int = Field(default=4, ge=1, le=100)
    num_judges: int = Field(default=3, ge=1, le=50)
    num_criteria: int = Field(default=3, ge=1, le=20)
