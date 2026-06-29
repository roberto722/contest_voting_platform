from typing import Any

from pydantic import BaseModel


class ResultEntryRead(BaseModel):
    participant_id: str
    participant_name: str
    display_name: str
    rank: int
    final_score: float
    public_score: float
    judge_score: float
    public_votes: int
    judge_votes_count: int
    details: dict[str, Any]


class CompetitionResultsRead(BaseModel):
    competition_id: str
    voting_session_id: str | None
    is_final: bool = False
    results: list[ResultEntryRead]
