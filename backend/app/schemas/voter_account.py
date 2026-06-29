from pydantic import BaseModel, ConfigDict, Field


class VoterAccountCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    active: bool = True


class VoterAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None
    active: bool | None = None


class VoterAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    display_name: str
    notes: str | None
    active: bool
    access_token: str


class VoterAccountCreatedRead(BaseModel):
    voter_account: VoterAccountRead
    access_code: str  # shown only at creation


class VoterAccountCodeRegeneratedRead(BaseModel):
    voter_account: VoterAccountRead
    access_code: str  # shown only at regeneration


class VoterAccountLinkParticipantRequest(BaseModel):
    participant_id: str = Field(min_length=1)


class LinkedParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    name: str
    display_name: str
    voter_account_id: str | None
