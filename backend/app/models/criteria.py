from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.vote import JudgeCriterionVote, PublicCriterionVote


class PublicVoteCriterion(IdMixin, Base):
    __tablename__ = "public_vote_criteria"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    min_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="public_criteria")
    criterion_votes: Mapped[list[PublicCriterionVote]] = relationship(back_populates="criterion")


class JudgeCriterion(IdMixin, Base):
    __tablename__ = "judge_criteria"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    min_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="judge_criteria")
    criterion_votes: Mapped[list[JudgeCriterionVote]] = relationship(back_populates="criterion")
