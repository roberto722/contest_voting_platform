from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class AuditLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    competition_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    actor_label: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(255))
    user_agent_hash: Mapped[str | None] = mapped_column(String(255))
