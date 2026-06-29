from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.services.access_service import hash_secret


def record_audit_log(
    db: Session,
    *,
    event_id: str,
    action: str,
    entity_type: str,
    actor_type: str = "admin",
    competition_id: str | None = None,
    actor_id: str | None = None,
    actor_label: str | None = None,
    entity_id: str | None = None,
    details_json: dict[str, object] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    log = AuditLog(
        event_id=event_id,
        competition_id=competition_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_label=actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details_json or {},
        ip_hash=hash_secret(ip_address) if ip_address else None,
        user_agent_hash=hash_secret(user_agent) if user_agent else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_event_audit_logs(db: Session, event_id: str, limit: int = 100) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.event_id == event_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    )
