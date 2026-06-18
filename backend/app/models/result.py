from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class ResultSnapshot(IdMixin, TimestampMixin, Base):
    __tablename__ = "result_snapshots"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    snapshot_name: Mapped[str] = mapped_column(String(255), nullable=False)
    results_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_admin_id: Mapped[str | None] = mapped_column(String(36))
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    competition = relationship("Competition", back_populates="result_snapshots")
