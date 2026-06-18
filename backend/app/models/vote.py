from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import PublicVoteMethod, enum_values
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.criteria import JudgeCriterion, PublicVoteCriterion
    from app.models.judge import Judge
    from app.models.participant import Participant
    from app.models.voting import VoterSession, VotingSession


class PublicVote(IdMixin, TimestampMixin, Base):
    __tablename__ = "public_votes"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        index=True,
    )
    voting_session_id: Mapped[str] = mapped_column(
        ForeignKey("voting_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    voter_session_id: Mapped[str] = mapped_column(
        ForeignKey("voter_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    vote_method: Mapped[PublicVoteMethod] = mapped_column(
        Enum(PublicVoteMethod, native_enum=False, values_callable=enum_values),
        nullable=False,
    )
    value: Mapped[float | None] = mapped_column(Float)
    rank_position: Mapped[int | None] = mapped_column(Integer)

    competition: Mapped[Competition] = relationship(back_populates="public_votes")
    participant: Mapped[Participant] = relationship(back_populates="public_votes")
    voting_session: Mapped[VotingSession] = relationship(back_populates="public_votes")
    voter_session: Mapped[VoterSession] = relationship(back_populates="public_votes")
    criterion_votes: Mapped[list[PublicCriterionVote]] = relationship(
        back_populates="public_vote",
        cascade="all, delete-orphan",
    )


class PublicCriterionVote(IdMixin, TimestampMixin, Base):
    __tablename__ = "public_criterion_votes"
    __table_args__ = (UniqueConstraint("public_vote_id", "criterion_id"),)

    public_vote_id: Mapped[str] = mapped_column(
        ForeignKey("public_votes.id", ondelete="CASCADE"),
        index=True,
    )
    criterion_id: Mapped[str] = mapped_column(
        ForeignKey("public_vote_criteria.id", ondelete="CASCADE"),
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)

    public_vote: Mapped[PublicVote] = relationship(back_populates="criterion_votes")
    criterion: Mapped[PublicVoteCriterion] = relationship(back_populates="criterion_votes")


class JudgeVote(IdMixin, TimestampMixin, Base):
    __tablename__ = "judge_votes"
    __table_args__ = (UniqueConstraint("participant_id", "judge_id", "voting_session_id"),)

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        index=True,
    )
    judge_id: Mapped[str] = mapped_column(ForeignKey("judges.id", ondelete="CASCADE"), index=True)
    voting_session_id: Mapped[str] = mapped_column(
        ForeignKey("voting_sessions.id", ondelete="CASCADE"),
        index=True,
    )

    competition: Mapped[Competition] = relationship(back_populates="judge_votes")
    participant: Mapped[Participant] = relationship(back_populates="judge_votes")
    judge: Mapped[Judge] = relationship(back_populates="votes")
    voting_session: Mapped[VotingSession] = relationship(back_populates="judge_votes")
    criterion_votes: Mapped[list[JudgeCriterionVote]] = relationship(
        back_populates="judge_vote",
        cascade="all, delete-orphan",
    )


class JudgeCriterionVote(IdMixin, TimestampMixin, Base):
    __tablename__ = "judge_criterion_votes"
    __table_args__ = (UniqueConstraint("judge_vote_id", "criterion_id"),)

    judge_vote_id: Mapped[str] = mapped_column(
        ForeignKey("judge_votes.id", ondelete="CASCADE"),
        index=True,
    )
    criterion_id: Mapped[str] = mapped_column(
        ForeignKey("judge_criteria.id", ondelete="CASCADE"),
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)

    judge_vote: Mapped[JudgeVote] = relationship(back_populates="criterion_votes")
    criterion: Mapped[JudgeCriterion] = relationship(back_populates="criterion_votes")
