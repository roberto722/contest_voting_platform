from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.vote import JudgeVote, PublicVote
    from app.models.voter_account import VoterAccount


participant_voter_accounts = Table(
    "participant_voter_accounts",
    Base.metadata,
    Column(
        "participant_id",
        ForeignKey("participants.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "voter_account_id",
        ForeignKey("voter_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Participant(IdMixin, TimestampMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("voter_account_id", "competition_id", name="uq_voter_account_competition"),
    )

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    voter_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("voter_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    performance_title: Mapped[str | None] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="participants")
    voter_account: Mapped[VoterAccount | None] = relationship()
    voter_accounts: Mapped[list[VoterAccount]] = relationship(
        secondary=participant_voter_accounts,
        back_populates="participants",
    )

    @property
    def voter_account_ids(self) -> list[str]:
        ids = [account.id for account in self.voter_accounts]
        if not ids and self.voter_account_id is not None:
            return [self.voter_account_id]
        return ids
    public_votes: Mapped[list[PublicVote]] = relationship(back_populates="participant")
    judge_votes: Mapped[list[JudgeVote]] = relationship(back_populates="participant")
