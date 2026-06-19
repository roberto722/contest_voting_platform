from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.judge_vote import (
    JudgeAccessRead,
    JudgeAccessRequest,
    JudgeVoteDetailRead,
    JudgeVoteRead,
    JudgeVoteStatusRead,
    JudgeVoteSubmit,
)
from app.services import audit_service, judge_vote_service

router = APIRouter(tags=["judge votes"])


@router.post("/api/judge-access", response_model=JudgeAccessRead)
def judge_access(
    payload: JudgeAccessRequest,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeAccessRead:
    judge = judge_vote_service.access_service.verify_judge_access(
        db,
        payload.judge_id,
        payload.access_code,
    )
    competitions = judge_vote_service.list_accessible_competitions(
        db,
        payload.judge_id,
        payload.access_code,
    )
    audit_service.record_audit_log(
        db,
        event_id=judge.event_id,
        actor_type="judge",
        actor_id=judge.id,
        actor_label=judge.display_name,
        action="judge_access_granted",
        entity_type="judge_access",
        entity_id=judge.id,
        details_json={"competition_count": len(competitions)},
    )
    return {
        "judge_id": judge.id,
        "display_name": judge.display_name,
        "competitions": competitions,
    }


@router.get("/api/judges/{judge_id}/competitions", response_model=JudgeAccessRead)
def list_judge_competitions(
    judge_id: str,
    access_code: str,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeAccessRead:
    competitions = judge_vote_service.list_accessible_competitions(db, judge_id, access_code)
    judge = judge_vote_service.access_service.verify_judge_access(db, judge_id, access_code)
    return {
        "judge_id": judge.id,
        "display_name": judge.display_name,
        "competitions": competitions,
    }


@router.post(
    "/api/competitions/{competition_id}/judge-votes",
    response_model=JudgeVoteRead,
)
def submit_judge_vote(
    competition_id: str,
    payload: JudgeVoteSubmit,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeVoteRead:
    return judge_vote_service.submit_judge_vote(db, competition_id, payload)


@router.get(
    "/api/competitions/{competition_id}/judge-votes",
    response_model=list[JudgeVoteDetailRead],
)
def list_judge_votes(
    competition_id: str,
    judge_id: str,
    access_code: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[JudgeVoteDetailRead]:
    return judge_vote_service.list_judge_votes(db, competition_id, judge_id, access_code)


@router.get(
    "/api/competitions/{competition_id}/judge-votes/status",
    response_model=JudgeVoteStatusRead,
)
def judge_vote_status(
    competition_id: str,
    judge_id: str,
    access_code: str,
    db: Annotated[Session, Depends(get_db)],
) -> JudgeVoteStatusRead:
    return judge_vote_service.get_judge_vote_status(db, competition_id, judge_id, access_code)
