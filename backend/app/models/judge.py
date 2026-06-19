from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.competition import Competition
    from app.models.event import Event
    from app.models.vote import JudgeVote


class Judge(IdMixin, TimestampMixin, Base):
    __tablename__ = "judges"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    event: Mapped[Event] = relationship(back_populates="judges")
    competitions: Mapped[list[CompetitionJudge]] = relationship(
        back_populates="judge",
        cascade="all, delete-orphan",
    )
    votes: Mapped[list[JudgeVote]] = relationship(back_populates="judge")

    @property
    def assigned_competition_ids(self) -> list[str]:
        return [
            assignment.competition_id
            for assignment in self.competitions
            if assignment.active
        ]


class CompetitionJudge(IdMixin, Base):
    __tablename__ = "competition_judges"
    __table_args__ = (UniqueConstraint("competition_id", "judge_id"),)

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
    )
    judge_id: Mapped[str] = mapped_column(ForeignKey("judges.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    competition: Mapped[Competition] = relationship(back_populates="judges")
    judge: Mapped[Judge] = relationship(back_populates="competitions")
