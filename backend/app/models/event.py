from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import EventStatus, enum_values
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.judge import Judge
    from app.models.screen import ScreenState
    from app.models.voting import VoterSession


class Event(IdMixin, TimestampMixin, Base):
    __tablename__ = "events"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, native_enum=False, values_callable=enum_values),
        default=EventStatus.DRAFT,
        nullable=False,
    )

    competitions: Mapped[list[Competition]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    judges: Mapped[list[Judge]] = relationship(back_populates="event", cascade="all, delete-orphan")
    voter_sessions: Mapped[list[VoterSession]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    screen_states: Mapped[list[ScreenState]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
