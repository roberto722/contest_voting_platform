from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.audit import AuditLogRead
from app.services import audit_service

router = APIRouter(tags=["audit logs"])


@router.get("/api/events/{event_id}/audit-logs", response_model=list[AuditLogRead])
def list_event_audit_logs(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditLogRead]:
    return audit_service.list_event_audit_logs(db, event_id, limit=limit)
