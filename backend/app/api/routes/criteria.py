from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import CriterionCreate, CriterionRead, CriterionUpdate
from app.services import admin_service

router = APIRouter(tags=["criteria"])


@router.post(
    "/api/competitions/{competition_id}/public-criteria",
    response_model=CriterionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_public_criterion(
    competition_id: str,
    payload: CriterionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> CriterionRead:
    return admin_service.create_public_criterion(db, competition_id, payload.model_dump())


@router.get(
    "/api/competitions/{competition_id}/public-criteria",
    response_model=list[CriterionRead],
)
def list_public_criteria(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[CriterionRead]:
    return admin_service.list_public_criteria(db, competition_id)


@router.patch("/api/public-criteria/{criterion_id}", response_model=CriterionRead)
def update_public_criterion(
    criterion_id: str,
    payload: CriterionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> CriterionRead:
    return admin_service.update_public_criterion(
        db,
        criterion_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/api/public-criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_public_criterion(criterion_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    admin_service.delete_public_criterion(db, criterion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/competitions/{competition_id}/judge-criteria",
    response_model=CriterionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_judge_criterion(
    competition_id: str,
    payload: CriterionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> CriterionRead:
    return admin_service.create_judge_criterion(db, competition_id, payload.model_dump())


@router.get("/api/competitions/{competition_id}/judge-criteria", response_model=list[CriterionRead])
def list_judge_criteria(
    competition_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[CriterionRead]:
    return admin_service.list_judge_criteria(db, competition_id)


@router.patch("/api/judge-criteria/{criterion_id}", response_model=CriterionRead)
def update_judge_criterion(
    criterion_id: str,
    payload: CriterionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> CriterionRead:
    return admin_service.update_judge_criterion(
        db,
        criterion_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/api/judge-criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_judge_criterion(criterion_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    admin_service.delete_judge_criterion(db, criterion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
