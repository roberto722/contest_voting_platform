from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    AccessMethod,
    CompetitionStatus,
    EventStatus,
    PublicVoteMethod,
    VotingSessionStatus,
)


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: EventStatus = EventStatus.DRAFT


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
    access_method: AccessMethod = AccessMethod.PUBLIC_LINK
    access_pin: str | None = None
    max_votes_per_user: int = 1
    allow_vote_update: bool = False
    status: CompetitionStatus = CompetitionStatus.DRAFT


class CompetitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    public_voting_enabled: bool | None = None
    judge_voting_enabled: bool | None = None
    public_vote_method: PublicVoteMethod | None = None
    public_weight: float | None = None
    judge_weight: float | None = None
    access_method: AccessMethod | None = None
    access_pin: str | None = None
    max_votes_per_user: int | None = None
    allow_vote_update: bool | None = None
    status: CompetitionStatus | None = None


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
    access_method: AccessMethod
    max_votes_per_user: int
    allow_vote_update: bool
    status: CompetitionStatus


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    performance_title: str | None = None
    order_index: int = 0
    active: bool = True


class ParticipantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    performance_title: str | None = None
    order_index: int | None = None
    active: bool | None = None


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


class CompetitionJudgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    judge_id: str
    active: bool


class VotingSessionCreate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    opened_by_admin_id: str | None = Field(default=None, max_length=36)


class VotingSessionClose(BaseModel):
    closed_by_admin_id: str | None = Field(default=None, max_length=36)


class VotingSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    label: str | None
    status: VotingSessionStatus
    opened_at: datetime | None
    closed_at: datetime | None
    opened_by_admin_id: str | None
    closed_by_admin_id: str | None
