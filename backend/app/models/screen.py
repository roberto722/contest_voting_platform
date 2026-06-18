from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ScreenMode, enum_values
from app.models.mixins import IdMixin, TimestampMixin


class ScreenState(IdMixin, TimestampMixin, Base):
    __tablename__ = "screen_states"
    __table_args__ = (UniqueConstraint("event_id", "competition_id"),)

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    competition_id: Mapped[str | None] = mapped_column(
        ForeignKey("competitions.id", ondelete="SET NULL"),
        index=True,
    )
    mode: Mapped[ScreenMode] = mapped_column(
        Enum(ScreenMode, native_enum=False, values_callable=enum_values),
        default=ScreenMode.IDLE,
        nullable=False,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    event = relationship("Event", back_populates="screen_states")
    competition = relationship("Competition", back_populates="screen_states")
