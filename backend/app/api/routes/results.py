from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.results import CompetitionResultsRead
from app.services import scoring_service

router = APIRouter(tags=["results"])


@router.get("/api/competitions/{competition_id}/results", response_model=CompetitionResultsRead)
def get_competition_results(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionResultsRead:
    return scoring_service.get_competition_results(db, competition_id)


@router.post(
    "/api/competitions/{competition_id}/results/freeze",
    response_model=CompetitionResultsRead,
)
def freeze_competition_results(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionResultsRead:
    return scoring_service.freeze_competition_results(db, competition_id)
