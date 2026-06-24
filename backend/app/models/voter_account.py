from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.participant import Participant
    from app.models.vote import PublicVote


class VoterAccount(IdMixin, TimestampMixin, Base):
    __tablename__ = "voter_accounts"

    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    access_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    event: Mapped[Event] = relationship(back_populates="voter_accounts")
    participants: Mapped[list[Participant]] = relationship(back_populates="voter_account")
    public_votes: Mapped[list[PublicVote]] = relationship(back_populates="voter_account")
