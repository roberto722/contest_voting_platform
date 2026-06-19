from pydantic import BaseModel, ConfigDict


class ResultComponentRead(BaseModel):
    enabled: bool
    weight: float
    raw_score: float
    normalized_score: float


class ResultEntryRead(BaseModel):
    participant_id: str
    display_name: str
    rank: int
    final_score: float
    public_score: ResultComponentRead
    judge_score: ResultComponentRead


class CompetitionResultsRead(BaseModel):
    competition_id: str
    voting_session_id: str | None
    results: list[ResultEntryRead]


class FreezeResultsRequest(BaseModel):
    snapshot_name: str = "Finale"
    created_by_admin_id: str | None = None


class ResultSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    snapshot_name: str
    results_json: CompetitionResultsRead
    created_by_admin_id: str | None
    is_final: bool
