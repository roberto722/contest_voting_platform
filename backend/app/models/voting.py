from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import VotingSessionStatus, enum_values
from app.models.mixins import IdMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.event import Event
    from app.models.vote import JudgeVote, PublicVote



class VotingSession(IdMixin, TimestampMixin, Base):
    __tablename__ = "voting_sessions"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[VotingSessionStatus] = mapped_column(
        Enum(VotingSessionStatus, native_enum=False, values_callable=enum_values),
        default=VotingSessionStatus.OPEN,
        nullable=False,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_by_admin_id: Mapped[str | None] = mapped_column(String(36))
    closed_by_admin_id: Mapped[str | None] = mapped_column(String(36))

    competition: Mapped[Competition] = relationship(back_populates="voting_sessions")
    public_votes: Mapped[list[PublicVote]] = relationship(back_populates="voting_session")
    judge_votes: Mapped[list[JudgeVote]] = relationship(back_populates="voting_session")
