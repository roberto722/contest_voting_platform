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
