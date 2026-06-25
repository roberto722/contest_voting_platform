# Contest Scoring Formula Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update contest results so the backend is the source of truth for the requested public, judge, weighted final, tie-break, and frozen-result behavior, then adapt the frontend to display the returned ranking.

**Architecture:** Keep scoring in `backend/app/services/scoring_service.py`; routes only call the service and serialize schemas. Reintroduce `ResultSnapshot` as the immutable final-result source, add database constraints for duplicate public votes, and update the frontend `App.tsx` result types/rendering to consume the backend response without duplicating scoring formulas.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, React/TypeScript.

---

## Files

- Modify: `backend/app/services/scoring_service.py`
  - Replace linear public normalization for counted public votes with `100 * sqrt(votes / max_votes)`.
  - Return flat result fields required by the UI/API: `participant_name`, `final_score`, `public_score`, `judge_score`, `public_votes`, `judge_votes_count`, `details`.
  - Apply deterministic tie-break: `final_score`, `judge_score`, `public_score`, `public_votes`, `participant_name`.
  - Read final results from `ResultSnapshot` when competition status is `results_frozen` or a final snapshot exists.
  - Create final snapshots through a dedicated freeze function.
- Create: `backend/app/models/result_snapshot.py`
  - SQLAlchemy model for immutable final snapshots.
- Modify: `backend/app/models/__init__.py`
  - Export `ResultSnapshot`.
- Modify: `backend/app/models/competition.py`
  - Add relationship `result_snapshots`.
- Modify: `backend/app/models/vote.py`
  - Add unique constraint on `public_votes(voter_account_id, competition_id, participant_id, voting_session_id)` or, if product wants cross-session duplicate blocking, enforce cross-session in service and keep DB constraint session-scoped.
- Create: `backend/alembic/versions/<revision>_restore_result_snapshots_and_public_vote_constraint.py`
  - Recreate `result_snapshots`.
  - Add public-vote duplicate index/constraint.
- Modify: `backend/app/schemas/results.py`
  - Match new response shape, while optionally keeping legacy nested component fields only if needed for a short frontend transition.
- Modify: `backend/app/api/routes/results.py`
  - Add `POST /api/competitions/{competition_id}/results/freeze` if not already exposed.
- Modify: `backend/app/services/public_vote_service.py`
  - Enforce max 3 public choices per user per competition.
  - Keep update behavior when `allow_vote_update = true`.
  - Return deterministic `400/409` errors for duplicate participant choices.
- Modify: `backend/tests/test_results_api.py`
  - Replace old expected linear score tests with the requested formula tests.
- Modify: `backend/tests/test_public_votes_api.py`
  - Add constraints for max 3 voted participants and duplicate participant rejection.
- Modify: `frontend/src/App.tsx`
  - Update `CompetitionResultsRead` / result item types.
  - Replace `result.public_score.raw_score` with `result.public_votes`.
  - Show score breakdown from flat numeric fields and `details` where useful.

## Backend Plan

### Task 1: Reintroduce ResultSnapshot persistence

- [ ] Create `backend/app/models/result_snapshot.py`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.competition import Competition


class ResultSnapshot(IdMixin, TimestampMixin, Base):
    __tablename__ = "result_snapshots"

    competition_id: Mapped[str] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    snapshot_name: Mapped[str] = mapped_column(String(255), nullable=False)
    results_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by_admin_id: Mapped[str | None] = mapped_column(String(36))
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    competition: Mapped[Competition] = relationship(back_populates="result_snapshots")
```

- [ ] Export it from `backend/app/models/__init__.py`.

```python
from app.models.result_snapshot import ResultSnapshot
```

Add `"ResultSnapshot"` to `__all__`.

- [ ] Add relationship in `Competition`.

```python
if TYPE_CHECKING:
    from app.models.result_snapshot import ResultSnapshot

result_snapshots: Mapped[list[ResultSnapshot]] = relationship(
    back_populates="competition",
    cascade="all, delete-orphan",
    order_by="ResultSnapshot.created_at",
)
```

- [ ] Create Alembic migration.

```bash
cd backend
uv run alembic revision -m "restore result snapshots and public vote constraint"
```

Migration body:

```python
def upgrade() -> None:
    op.create_table(
        "result_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_name", sa.String(255), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(36), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_result_snapshots_competition_id", "result_snapshots", ["competition_id"])
    op.create_index("ix_result_snapshots_is_final", "result_snapshots", ["is_final"])
    op.create_unique_constraint(
        "uq_public_vote_voter_competition_participant_session",
        "public_votes",
        ["voter_account_id", "competition_id", "participant_id", "voting_session_id"],
    )
```

Downgrade must drop the unique constraint, indexes, and table.

### Task 2: Write scoring tests first

- [ ] Replace or extend `backend/tests/test_results_api.py` with tests for:
  - public score with `A=80`, `B=50`, `C=20`;
  - public score with `max_votes = 0`;
  - judge score with weighted criteria;
  - final score with `40/60` and `50/50`;
  - public weight `0`;
  - judge weight `0`;
  - tie-break on judge score;
  - tie-break on public score;
  - frozen result reads `ResultSnapshot`.

Core expected assertions for the requested numeric example:

```python
assert results[0]["participant_name"] == "A"
assert results[0]["final_score"] == 86.8
assert results[0]["public_score"] == 100.0
assert results[0]["judge_score"] == 78.0
assert results[0]["public_votes"] == 80

assert results[1]["participant_name"] == "B"
assert results[1]["final_score"] == 85.62
assert results[1]["public_score"] == 79.06
assert results[1]["judge_score"] == 90.0

assert results[2]["participant_name"] == "C"
assert results[2]["final_score"] == 71.0
assert results[2]["public_score"] == 50.0
assert results[2]["judge_score"] == 85.0
```

- [ ] Run the new scoring tests and confirm they fail against current code.

```bash
cd backend
uv run pytest tests/test_results_api.py -q
```

Expected: failures showing linear public normalization, old nested schema, or missing `ResultSnapshot`.

### Task 3: Implement scoring formula and output shape

- [ ] In `backend/app/services/scoring_service.py`, import `math`, `func`, `CompetitionStatus`, and `ResultSnapshot`.

- [ ] Replace counted public score normalization with:

```python
def calculate_public_score(votes: int, max_votes: int) -> float:
    if max_votes <= 0 or votes <= 0:
        return 0.0
    return round(100 * math.sqrt(votes / max_votes), 2)
```

- [ ] Keep criteria-rating public votes bounded on `0..100`; apply square-root formula only to counted public votes used for max-three public voting.

- [ ] Add judge calculation helpers:

```python
def calculate_judge_score(criterion_votes: list[JudgeCriterionVote]) -> float | None:
    weighted_total = 0.0
    weight_total = 0.0
    for criterion_vote in criterion_votes:
        criterion = criterion_vote.criterion
        if criterion.max_score <= criterion.min_score or criterion.weight <= 0:
            continue
        normalized = 100 * (
            (criterion_vote.score - criterion.min_score)
            / (criterion.max_score - criterion.min_score)
        )
        weighted_total += normalized * criterion.weight
        weight_total += criterion.weight
    if weight_total <= 0:
        return None
    return weighted_total / weight_total
```

- [ ] Normalize weights only for enabled components:

```python
public_weight = competition.public_weight if competition.public_voting_enabled and competition.public_weight > 0 else 0.0
judge_weight = competition.judge_weight if competition.judge_voting_enabled and competition.judge_weight > 0 else 0.0
total_weight = public_weight + judge_weight
```

When `total_weight <= 0`, return `final_score = 0` for every participant.

- [ ] Build result entries with this shape:

```python
{
    "participant_id": participant.id,
    "participant_name": participant.display_name,
    "rank": 0,
    "final_score": round(final_score, 2),
    "public_score": round(public_score, 2),
    "judge_score": round(judge_score, 2),
    "public_votes": public_votes,
    "judge_votes_count": judge_votes_count,
    "details": {
        "public": {
            "votes": public_votes,
            "max_votes": max_votes,
            "formula": "100 * sqrt(votes / max_votes)",
        },
        "judges": {
            "criteria_breakdown": criteria_breakdown,
            "judges_completed": judge_votes_count,
        },
    },
}
```

- [ ] Sort with deterministic tie-break:

```python
results.sort(
    key=lambda item: (
        -item["final_score"],
        -item["judge_score"],
        -item["public_score"],
        -item["public_votes"],
        item["participant_name"].casefold(),
        item["participant_id"],
    )
)
```

- [ ] Assign ranks. Use sequential ranks (`1, 2, 3`) for deterministic UI ordering. If ex aequo ranks are desired later, add an explicit product decision and test.

### Task 4: Implement frozen result behavior

- [ ] Add `_get_final_snapshot(db, competition_id)`.

```python
def _get_final_snapshot(db: Session, competition_id: str) -> ResultSnapshot | None:
    return db.scalar(
        select(ResultSnapshot)
        .where(
            ResultSnapshot.competition_id == competition_id,
            ResultSnapshot.is_final.is_(True),
        )
        .order_by(ResultSnapshot.created_at.desc())
    )
```

- [ ] At the start of `get_competition_results`, return snapshot JSON if:
  - competition status is `CompetitionStatus.RESULTS_FROZEN`; or
  - `_get_final_snapshot(...)` returns a final snapshot.

- [ ] Implement `freeze_competition_results(db, competition_id, created_by_admin_id=None)`.

```python
results = calculate_live_results(db, competition, include_final_snapshot=False)
snapshot = ResultSnapshot(
    competition_id=competition.id,
    snapshot_name="Final results",
    results_json=results,
    created_by_admin_id=created_by_admin_id,
    is_final=True,
)
competition.status = CompetitionStatus.RESULTS_FROZEN
db.add(snapshot)
db.commit()
db.refresh(snapshot)
return snapshot.results_json
```

- [ ] Ensure `calculate_live_results` never reads a snapshot; only the public entrypoint does. This prevents recursion during freeze.

- [ ] Add route:

```python
@router.post("/api/competitions/{competition_id}/results/freeze", response_model=CompetitionResultsRead)
def freeze_competition_results(...):
    return scoring_service.freeze_competition_results(db, competition_id)
```

### Task 5: Update result schemas

- [ ] Replace `ResultComponentRead` usage in `backend/app/schemas/results.py` with:

```python
from typing import Any

from pydantic import BaseModel


class ResultEntryRead(BaseModel):
    participant_id: str
    participant_name: str
    rank: int
    final_score: float
    public_score: float
    judge_score: float
    public_votes: int
    judge_votes_count: int
    details: dict[str, Any]


class CompetitionResultsRead(BaseModel):
    competition_id: str
    voting_session_id: str | None
    is_final: bool = False
    results: list[ResultEntryRead]
```

- [ ] If existing frontend code still expects `display_name`, either update frontend in the same branch or include `display_name` as a temporary alias equal to `participant_name`. Prefer frontend update if no external API clients are involved.

### Task 6: Enforce max-three and duplicate public vote constraints

- [ ] In `backend/app/services/public_vote_service.py`, centralize max choice validation:

```python
MAX_PUBLIC_CHOICES_PER_USER = 3


def _validate_public_choice_count(participant_ids: list[str], competition: Competition) -> None:
    max_allowed = min(competition.max_votes_per_user, MAX_PUBLIC_CHOICES_PER_USER)
    if len(participant_ids) > max_allowed:
        raise PublicVoteError(f"voter can select at most {max_allowed} participants", status_code=400)
    if len(set(participant_ids)) != len(participant_ids):
        raise PublicVoteError("cannot vote more than once for the same participant", status_code=400)
```

- [ ] Call it from `_build_multiple_choice_votes`, `_build_ranked_choice_votes`, and any criteria-rating path that accepts multiple participants.

- [ ] Keep `allow_vote_update = true` behavior by deleting existing votes for the active session before inserting replacement votes.

- [ ] Keep `allow_vote_update = false` behavior by rejecting if existing votes exist for the active session.

- [ ] Add API tests:

```python
assert too_many_response.status_code == 400
assert "at most 3" in too_many_response.json()["detail"]

assert duplicate_response.status_code == 400
assert "same participant" in duplicate_response.json()["detail"]
```

### Task 7: Frontend result type and rendering update

- [ ] In `frontend/src/App.tsx`, replace result type fields:

```ts
type ResultEntryRead = {
  participant_id: string;
  participant_name: string;
  rank: number;
  final_score: number;
  public_score: number;
  judge_score: number;
  public_votes: number;
  judge_votes_count: number;
  details: {
    public?: {
      votes: number;
      max_votes: number;
      formula: string;
    };
    judges?: {
      criteria_breakdown: unknown[];
      judges_completed: number;
    };
  };
};
```

- [ ] Replace display access:

```ts
result.display_name
```

with:

```ts
result.participant_name
```

- [ ] Replace vote count access:

```ts
result.public_score.raw_score
```

with:

```ts
result.public_votes
```

- [ ] Keep all percentage/bar width calculations based on `result.final_score`, since the frontend must not recalculate scoring.

- [ ] In admin results view, show:

```text
Finale: {final_score}
Pubblico: {public_score}
Giudici: {judge_score}
Voti pubblico: {public_votes}
Giudici completati: {judge_votes_count}
```

## Verification

- [ ] Run backend tests:

```bash
cd backend
uv run pytest tests/test_results_api.py tests/test_public_votes_api.py -q
```

Expected: all selected tests pass.

- [ ] Run full backend test suite:

```bash
cd backend
uv run pytest -q
```

Expected: all tests pass.

- [ ] Run migrations on a fresh database:

```bash
cd backend
uv run alembic upgrade head
```

Expected: migration succeeds and creates `result_snapshots` plus the public vote unique constraint.

- [ ] Run frontend checks:

```bash
cd frontend
npm run build
```

Expected: TypeScript/build succeeds.

- [ ] Manual smoke through Docker:

```bash
docker compose up --build
```

Expected:
- admin can create/configure competition;
- public user can vote for max 3 participants;
- duplicate participant selection is rejected;
- results show requested formula;
- freeze stores snapshot;
- changing raw votes after freeze does not change returned final results.

## Self-Review

- Spec coverage:
  - Formula public `sqrt(votes / max_votes)`: Task 3.
  - Judge weighted criteria normalization: Task 3.
  - Weighted final score: Task 3.
  - Tie-break: Task 3.
  - Frozen results from snapshot: Tasks 1 and 4.
  - Max 3 and duplicate public votes: Tasks 1 and 6.
  - Frontend displays backend results only: Task 7.
- Risk:
  - Existing frontend and tests currently expect nested `public_score.raw_score`; Task 7 must land with Task 5.
  - A previous migration explicitly dropped snapshots; reintroducing them is intentional and must be called out in PR notes.
  - DB unique constraint should include `voting_session_id` if updates delete same-session votes before insert. Cross-session duplicate policy remains governed by service limits unless product decides otherwise.
