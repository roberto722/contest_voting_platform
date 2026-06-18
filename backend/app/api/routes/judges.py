from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import CompetitionJudgeRead, JudgeCreate, JudgeRead, JudgeUpdate
from app.services import admin_service

router = APIRouter(tags=["judges"])


@router.post(
    "/api/events/{event_id}/judges",
    response_model=JudgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_judge(
    event_id: str,
    payload: JudgeCreate,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeRead:
    return admin_service.create_judge(db, event_id, payload.model_dump())


@router.get("/api/events/{event_id}/judges", response_model=list[JudgeRead])
def list_judges(event_id: str, db: Annotated[Session, Depends(get_db)]) -> list[JudgeRead]:
    return admin_service.list_judges(db, event_id)


@router.patch("/api/judges/{judge_id}", response_model=JudgeRead)
def update_judge(
    judge_id: str,
    payload: JudgeUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeRead:
    return admin_service.update_judge(db, judge_id, payload.model_dump(exclude_unset=True))


@router.delete("/api/judges/{judge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_judge(judge_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    admin_service.delete_judge(db, judge_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/competitions/{competition_id}/judges/{judge_id}",
    response_model=CompetitionJudgeRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_judge(
    competition_id: str,
    judge_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CompetitionJudgeRead:
    return admin_service.assign_judge(db, competition_id, judge_id)


@router.delete(
    "/api/competitions/{competition_id}/judges/{judge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_judge_assignment(
    competition_id: str,
    judge_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    admin_service.remove_judge_assignment(db, competition_id, judge_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
