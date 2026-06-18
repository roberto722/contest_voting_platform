from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AccessMethod, CompetitionStatus, PublicVoteMethod, enum_values
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.criteria import JudgeCriterion, PublicVoteCriterion
    from app.models.event import Event
    from app.models.judge import CompetitionJudge
    from app.models.participant import Participant
    from app.models.result import ResultSnapshot
    from app.models.screen import ScreenState
    from app.models.vote import JudgeVote, PublicVote
    from app.models.voting import VotingSession


class Competition(IdMixin, TimestampMixin, Base):
    __tablename__ = "competitions"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    type: Mapped[str | None] = mapped_column(String(100))
    public_voting_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    judge_voting_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_vote_method: Mapped[PublicVoteMethod] = mapped_column(
        Enum(PublicVoteMethod, native_enum=False, values_callable=enum_values),
        default=PublicVoteMethod.SINGLE_CHOICE,
        nullable=False,
    )
    public_weight: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    judge_weight: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    access_method: Mapped[AccessMethod] = mapped_column(
        Enum(AccessMethod, native_enum=False, values_callable=enum_values),
        default=AccessMethod.PUBLIC_LINK,
        nullable=False,
    )
    access_pin_hash: Mapped[str | None] = mapped_column(String(255))
    max_votes_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    allow_vote_update: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[CompetitionStatus] = mapped_column(
        Enum(CompetitionStatus, native_enum=False, values_callable=enum_values),
        default=CompetitionStatus.DRAFT,
        nullable=False,
    )

    event: Mapped[Event] = relationship(back_populates="competitions")
    participants: Mapped[list[Participant]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
        order_by="Participant.order_index",
    )
    public_criteria: Mapped[list[PublicVoteCriterion]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
        order_by="PublicVoteCriterion.order_index",
    )
    judge_criteria: Mapped[list[JudgeCriterion]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
        order_by="JudgeCriterion.order_index",
    )
    judges: Mapped[list[CompetitionJudge]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    voting_sessions: Mapped[list[VotingSession]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    public_votes: Mapped[list[PublicVote]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    judge_votes: Mapped[list[JudgeVote]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    result_snapshots: Mapped[list[ResultSnapshot]] = relationship(
        back_populates="competition",
        cascade="all, delete-orphan",
    )
    screen_states: Mapped[list[ScreenState]] = relationship(back_populates="competition")
