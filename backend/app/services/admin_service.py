from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    CompetitionJudge,
    Event,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVoteCriterion,
)
from app.services.access_service import hash_secret


class ResourceNotFound(Exception):
    def __init__(self, resource: str, resource_id: str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} not found")


def get_required[ModelT](
    db: Session,
    model: type[ModelT],
    resource_id: str,
    resource: str,
) -> ModelT:
    instance = db.get(model, resource_id)
    if instance is None:
        raise ResourceNotFound(resource, resource_id)
    return instance


def _save[ModelT](db: Session, instance: ModelT) -> ModelT:
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def _update[ModelT](db: Session, instance: ModelT, data: dict[str, Any]) -> ModelT:
    for key, value in data.items():
        setattr(instance, key, value)
    return _save(db, instance)


def _delete(db: Session, instance: object) -> None:
    db.delete(instance)
    db.commit()


def create_event(db: Session, data: dict[str, Any]) -> Event:
    return _save(db, Event(**data))


def list_events(db: Session) -> list[Event]:
    return list(db.scalars(select(Event).order_by(Event.created_at.desc())))


def get_event(db: Session, event_id: str) -> Event:
    return get_required(db, Event, event_id, "event")


def update_event(db: Session, event_id: str, data: dict[str, Any]) -> Event:
    return _update(db, get_event(db, event_id), data)


def delete_event(db: Session, event_id: str) -> None:
    _delete(db, get_event(db, event_id))


def create_competition(db: Session, event_id: str, data: dict[str, Any]) -> Competition:
    event = get_event(db, event_id)
    access_pin = data.pop("access_pin", None)
    if access_pin:
        data["access_pin_hash"] = hash_secret(access_pin)
    return _save(db, Competition(event=event, **data))


def list_competitions(db: Session, event_id: str) -> list[Competition]:
    get_event(db, event_id)
    return list(
        db.scalars(
            select(Competition)
            .where(Competition.event_id == event_id)
            .order_by(Competition.name)
        )
    )


def get_competition(db: Session, competition_id: str) -> Competition:
    return get_required(db, Competition, competition_id, "competition")


def update_competition(db: Session, competition_id: str, data: dict[str, Any]) -> Competition:
    access_pin = data.pop("access_pin", None)
    if access_pin:
        data["access_pin_hash"] = hash_secret(access_pin)
    return _update(db, get_competition(db, competition_id), data)


def delete_competition(db: Session, competition_id: str) -> None:
    _delete(db, get_competition(db, competition_id))


def create_participant(db: Session, competition_id: str, data: dict[str, Any]) -> Participant:
    competition = get_competition(db, competition_id)
    return _save(db, Participant(competition=competition, **data))


def list_participants(db: Session, competition_id: str) -> list[Participant]:
    get_competition(db, competition_id)
    return list(
        db.scalars(
            select(Participant)
            .where(Participant.competition_id == competition_id)
            .order_by(Participant.order_index, Participant.display_name)
        )
    )


def get_participant(db: Session, participant_id: str) -> Participant:
    return get_required(db, Participant, participant_id, "participant")


def update_participant(db: Session, participant_id: str, data: dict[str, Any]) -> Participant:
    return _update(db, get_participant(db, participant_id), data)


def delete_participant(db: Session, participant_id: str) -> None:
    _delete(db, get_participant(db, participant_id))


def create_public_criterion(
    db: Session,
    competition_id: str,
    data: dict[str, Any],
) -> PublicVoteCriterion:
    competition = get_competition(db, competition_id)
    return _save(db, PublicVoteCriterion(competition=competition, **data))


def list_public_criteria(db: Session, competition_id: str) -> list[PublicVoteCriterion]:
    get_competition(db, competition_id)
    return list(
        db.scalars(
            select(PublicVoteCriterion)
            .where(PublicVoteCriterion.competition_id == competition_id)
            .order_by(PublicVoteCriterion.order_index, PublicVoteCriterion.name)
        )
    )


def get_public_criterion(db: Session, criterion_id: str) -> PublicVoteCriterion:
    return get_required(db, PublicVoteCriterion, criterion_id, "public criterion")


def update_public_criterion(
    db: Session,
    criterion_id: str,
    data: dict[str, Any],
) -> PublicVoteCriterion:
    return _update(db, get_public_criterion(db, criterion_id), data)


def delete_public_criterion(db: Session, criterion_id: str) -> None:
    _delete(db, get_public_criterion(db, criterion_id))


def create_judge_criterion(
    db: Session,
    competition_id: str,
    data: dict[str, Any],
) -> JudgeCriterion:
    competition = get_competition(db, competition_id)
    return _save(db, JudgeCriterion(competition=competition, **data))


def list_judge_criteria(db: Session, competition_id: str) -> list[JudgeCriterion]:
    get_competition(db, competition_id)
    return list(
        db.scalars(
            select(JudgeCriterion)
            .where(JudgeCriterion.competition_id == competition_id)
            .order_by(JudgeCriterion.order_index, JudgeCriterion.name)
        )
    )


def get_judge_criterion(db: Session, criterion_id: str) -> JudgeCriterion:
    return get_required(db, JudgeCriterion, criterion_id, "judge criterion")


def update_judge_criterion(db: Session, criterion_id: str, data: dict[str, Any]) -> JudgeCriterion:
    return _update(db, get_judge_criterion(db, criterion_id), data)


def delete_judge_criterion(db: Session, criterion_id: str) -> None:
    _delete(db, get_judge_criterion(db, criterion_id))


def create_judge(db: Session, event_id: str, data: dict[str, Any]) -> Judge:
    event = get_event(db, event_id)
    access_code = data.pop("access_code")
    data["access_code_hash"] = hash_secret(access_code)
    return _save(db, Judge(event=event, **data))


def list_judges(db: Session, event_id: str) -> list[Judge]:
    get_event(db, event_id)
    return list(db.scalars(select(Judge).where(Judge.event_id == event_id).order_by(Judge.name)))


def get_judge(db: Session, judge_id: str) -> Judge:
    return get_required(db, Judge, judge_id, "judge")


def update_judge(db: Session, judge_id: str, data: dict[str, Any]) -> Judge:
    access_code = data.pop("access_code", None)
    if access_code:
        data["access_code_hash"] = hash_secret(access_code)
    return _update(db, get_judge(db, judge_id), data)


def delete_judge(db: Session, judge_id: str) -> None:
    _delete(db, get_judge(db, judge_id))


def assign_judge(db: Session, competition_id: str, judge_id: str) -> CompetitionJudge:
    get_competition(db, competition_id)
    get_judge(db, judge_id)
    existing = db.scalar(
        select(CompetitionJudge).where(
            CompetitionJudge.competition_id == competition_id,
            CompetitionJudge.judge_id == judge_id,
        )
    )
    if existing is not None:
        return existing
    return _save(db, CompetitionJudge(competition_id=competition_id, judge_id=judge_id))


def remove_judge_assignment(db: Session, competition_id: str, judge_id: str) -> None:
    assignment = db.scalar(
        select(CompetitionJudge).where(
            CompetitionJudge.competition_id == competition_id,
            CompetitionJudge.judge_id == judge_id,
        )
    )
    if assignment is None:
        raise ResourceNotFound("competition judge assignment", f"{competition_id}:{judge_id}")
    _delete(db, assignment)
