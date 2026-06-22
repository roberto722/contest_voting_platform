from secrets import token_urlsafe
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AuditLog,
    Competition,
    CompetitionJudge,
    Event,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVoteCriterion,
    PublicVoteMethod,
)
from app.models.enums import CompetitionStatus, EventStatus
from app.services import audit_service, setup_service
from app.services.access_service import hash_secret


class ResourceNotFound(Exception):
    def __init__(self, resource: str, resource_id: str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} not found")


class AdminStateError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 409,
        issues: list[str] | None = None,
        messages: list[str] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.issues = issues or []
        self.messages = messages or []
        super().__init__(message)


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


def _audit(
    db: Session,
    *,
    event_id: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    competition_id: str | None = None,
    details_json: dict[str, Any] | None = None,
) -> None:
    audit_service.record_audit_log(
        db,
        event_id=event_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        competition_id=competition_id,
        actor_type="admin",
        actor_label="Admin",
        details_json=details_json,
    )


def _ensure_event_configuration_editable(event: Event) -> None:
    if event.status != EventStatus.DRAFT:
        raise AdminStateError("event configuration is locked after draft")


def _ensure_competition_configuration_editable(competition: Competition) -> None:
    _ensure_event_configuration_editable(competition.event)


def _set_event_live(db: Session, event: Event) -> None:
    setup_status = setup_service.get_event_setup_status(db, event)
    if not setup_status["can_go_live"]:
        raise AdminStateError(
            "event is not ready for live",
            issues=setup_status["issues"],
            messages=setup_status["messages"],
        )
    event.status = EventStatus.LIVE


def create_event(db: Session, data: dict[str, Any]) -> Event:
    event = _save(db, Event(**data))
    _audit(
        db,
        event_id=event.id,
        action="admin_event_created",
        entity_type="event",
        entity_id=event.id,
        details_json={"name": event.name, "status": event.status.value},
    )
    return event


def list_events(db: Session) -> list[Event]:
    return list(db.scalars(select(Event).order_by(Event.created_at.desc())))


def get_event(db: Session, event_id: str) -> Event:
    return get_required(db, Event, event_id, "event")


def update_event(db: Session, event_id: str, data: dict[str, Any]) -> Event:
    event = get_event(db, event_id)
    requested_status = data.pop("status", None)
    old_status = event.status

    if requested_status is not None:
        new_status = EventStatus(requested_status)
        allowed_transitions = {
            EventStatus.DRAFT: {EventStatus.DRAFT, EventStatus.LIVE},
            EventStatus.LIVE: {EventStatus.LIVE, EventStatus.CLOSED},
            EventStatus.CLOSED: {EventStatus.CLOSED, EventStatus.ARCHIVED},
            EventStatus.ARCHIVED: {EventStatus.ARCHIVED},
        }
        if new_status not in allowed_transitions[event.status]:
            raise AdminStateError("invalid event status transition")
        if new_status == EventStatus.LIVE and event.status != EventStatus.LIVE:
            _set_event_live(db, event)
        else:
            event.status = new_status

    event = _update(db, event, data)
    _audit(
        db,
        event_id=event.id,
        action="admin_event_updated",
        entity_type="event",
        entity_id=event.id,
        details_json={**data, "old_status": old_status.value, "status": event.status.value},
    )
    return event


def delete_event(db: Session, event_id: str) -> None:
    event = get_event(db, event_id)
    db.execute(delete(AuditLog).where(AuditLog.event_id == event.id))
    db.delete(event)
    db.commit()


def create_competition(db: Session, event_id: str, data: dict[str, Any]) -> Competition:
    event = get_event(db, event_id)
    _ensure_event_configuration_editable(event)
    access_pin = data.pop("access_pin", None)
    if access_pin:
        data["access_pin_hash"] = hash_secret(access_pin)
    competition = _save(db, Competition(event=event, **data))
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=event.id,
        competition_id=competition.id,
        action="admin_competition_created",
        entity_type="competition",
        entity_id=competition.id,
        details_json={
            "name": competition.name,
            "status": competition.status.value,
            "public_vote_method": competition.public_vote_method.value,
        },
    )
    return competition


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
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    access_pin = data.pop("access_pin", None)
    if access_pin:
        data["access_pin_hash"] = hash_secret(access_pin)
    competition = _update(db, competition, data)
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_competition_updated",
        entity_type="competition",
        entity_id=competition.id,
        details_json=data,
    )
    return competition


def delete_competition(db: Session, competition_id: str) -> None:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    db.execute(delete(AuditLog).where(AuditLog.competition_id == competition.id))
    db.delete(competition)
    db.commit()


def create_participant(db: Session, competition_id: str, data: dict[str, Any]) -> Participant:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    participant = _save(db, Participant(competition=competition, **data))
    refresh_competition_status(db, competition_id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_participant_created",
        entity_type="participant",
        entity_id=participant.id,
        details_json={"display_name": participant.display_name, "active": participant.active},
    )
    return participant


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
    participant = get_participant(db, participant_id)
    _ensure_competition_configuration_editable(participant.competition)
    participant = _update(db, participant, data)
    refresh_competition_status(db, participant.competition_id)
    _audit(
        db,
        event_id=participant.competition.event_id,
        competition_id=participant.competition_id,
        action="admin_participant_updated",
        entity_type="participant",
        entity_id=participant.id,
        details_json=data,
    )
    return participant


def delete_participant(db: Session, participant_id: str) -> None:
    participant = get_participant(db, participant_id)
    competition = participant.competition
    _ensure_competition_configuration_editable(competition)
    _delete(db, participant)
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_participant_deleted",
        entity_type="participant",
        entity_id=participant.id,
        details_json={"display_name": participant.display_name},
    )


def create_public_criterion(
    db: Session,
    competition_id: str,
    data: dict[str, Any],
) -> PublicVoteCriterion:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    criterion = _save(db, PublicVoteCriterion(competition=competition, **data))
    refresh_competition_status(db, competition_id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_public_criterion_created",
        entity_type="public_criterion",
        entity_id=criterion.id,
        details_json={"name": criterion.name, "active": criterion.active},
    )
    return criterion


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
    criterion = get_public_criterion(db, criterion_id)
    _ensure_competition_configuration_editable(criterion.competition)
    criterion = _update(db, criterion, data)
    refresh_competition_status(db, criterion.competition_id)
    _audit(
        db,
        event_id=criterion.competition.event_id,
        competition_id=criterion.competition_id,
        action="admin_public_criterion_updated",
        entity_type="public_criterion",
        entity_id=criterion.id,
        details_json=data,
    )
    return criterion


def delete_public_criterion(db: Session, criterion_id: str) -> None:
    criterion = get_public_criterion(db, criterion_id)
    competition = criterion.competition
    _ensure_competition_configuration_editable(competition)
    _delete(db, criterion)
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_public_criterion_deleted",
        entity_type="public_criterion",
        entity_id=criterion.id,
        details_json={"name": criterion.name},
    )


def create_judge_criterion(
    db: Session,
    competition_id: str,
    data: dict[str, Any],
) -> JudgeCriterion:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    criterion = _save(db, JudgeCriterion(competition=competition, **data))
    refresh_competition_status(db, competition_id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_judge_criterion_created",
        entity_type="judge_criterion",
        entity_id=criterion.id,
        details_json={"name": criterion.name, "active": criterion.active},
    )
    return criterion


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
    criterion = get_judge_criterion(db, criterion_id)
    _ensure_competition_configuration_editable(criterion.competition)
    criterion = _update(db, criterion, data)
    refresh_competition_status(db, criterion.competition_id)
    _audit(
        db,
        event_id=criterion.competition.event_id,
        competition_id=criterion.competition_id,
        action="admin_judge_criterion_updated",
        entity_type="judge_criterion",
        entity_id=criterion.id,
        details_json=data,
    )
    return criterion


def delete_judge_criterion(db: Session, criterion_id: str) -> None:
    criterion = get_judge_criterion(db, criterion_id)
    competition = criterion.competition
    _ensure_competition_configuration_editable(competition)
    _delete(db, criterion)
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_judge_criterion_deleted",
        entity_type="judge_criterion",
        entity_id=criterion.id,
        details_json={"name": criterion.name},
    )


def create_judge(db: Session, event_id: str, data: dict[str, Any]) -> Judge:
    event = get_event(db, event_id)
    _ensure_event_configuration_editable(event)
    access_code = data.pop("access_code")
    data["access_code_hash"] = hash_secret(access_code)
    judge = _save(db, Judge(event=event, **data))
    _audit(
        db,
        event_id=event.id,
        action="admin_judge_created",
        entity_type="judge",
        entity_id=judge.id,
        details_json={"display_name": judge.display_name, "active": judge.active},
    )
    return judge


def list_judges(db: Session, event_id: str) -> list[Judge]:
    get_event(db, event_id)
    return list(
        db.scalars(
            select(Judge)
            .where(Judge.event_id == event_id)
            .options(selectinload(Judge.competitions))
            .order_by(Judge.name)
        )
    )


def get_judge(db: Session, judge_id: str) -> Judge:
    return get_required(db, Judge, judge_id, "judge")


def update_judge(db: Session, judge_id: str, data: dict[str, Any]) -> Judge:
    judge = get_judge(db, judge_id)
    _ensure_event_configuration_editable(judge.event)
    access_code = data.pop("access_code", None)
    if access_code:
        data["access_code_hash"] = hash_secret(access_code)
    judge = _update(db, judge, data)
    _audit(
        db,
        event_id=judge.event_id,
        action="admin_judge_updated",
        entity_type="judge",
        entity_id=judge.id,
        details_json=data,
    )
    return judge


def regenerate_judge_access_code(db: Session, judge_id: str) -> tuple[Judge, str]:
    access_code = token_urlsafe(12)
    judge = get_judge(db, judge_id)
    judge = _update(db, judge, {"access_code_hash": hash_secret(access_code)})
    _audit(
        db,
        event_id=judge.event_id,
        action="admin_judge_access_code_regenerated",
        entity_type="judge",
        entity_id=judge.id,
        details_json={"display_name": judge.display_name},
    )
    return judge, access_code


def delete_judge(db: Session, judge_id: str) -> None:
    judge = get_judge(db, judge_id)
    _ensure_event_configuration_editable(judge.event)
    _delete(db, judge)
    _audit(
        db,
        event_id=judge.event_id,
        action="admin_judge_deleted",
        entity_type="judge",
        entity_id=judge.id,
        details_json={"display_name": judge.display_name},
    )


def assign_judge(db: Session, competition_id: str, judge_id: str) -> CompetitionJudge:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)
    judge = get_judge(db, judge_id)
    if judge.event_id != competition.event_id:
        raise AdminStateError("judge does not belong to competition event")
    if not competition.judge_voting_enabled:
        raise AdminStateError("judge voting is disabled for this competition")
    existing = db.scalar(
        select(CompetitionJudge).where(
            CompetitionJudge.competition_id == competition_id,
            CompetitionJudge.judge_id == judge_id,
        )
    )
    if existing is not None:
        _audit(
            db,
            event_id=competition.event_id,
            competition_id=competition.id,
            action="admin_judge_assignment_existing",
            entity_type="competition_judge",
            entity_id=existing.id,
            details_json={"judge_id": judge.id, "judge_name": judge.display_name},
        )
        return existing
    assignment = _save(db, CompetitionJudge(competition_id=competition_id, judge_id=judge_id))
    refresh_competition_status(db, competition_id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_judge_assigned",
        entity_type="competition_judge",
        entity_id=assignment.id,
        details_json={"judge_id": judge.id, "judge_name": judge.display_name},
    )
    return assignment


def remove_judge_assignment(db: Session, competition_id: str, judge_id: str) -> None:
    assignment = db.scalar(
        select(CompetitionJudge).where(
            CompetitionJudge.competition_id == competition_id,
            CompetitionJudge.judge_id == judge_id,
        )
    )
    if assignment is None:
        raise ResourceNotFound("competition judge assignment", f"{competition_id}:{judge_id}")
    competition = assignment.competition
    _ensure_competition_configuration_editable(competition)
    judge = assignment.judge
    _delete(db, assignment)
    refresh_competition_status(db, competition.id)
    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_judge_unassigned",
        entity_type="competition_judge",
        entity_id=assignment.id,
        details_json={"judge_id": judge.id, "judge_name": judge.display_name},
    )


def get_competition_setup_status(db: Session, competition_id: str) -> dict[str, Any]:
    competition = get_competition(db, competition_id)
    return setup_service.get_competition_setup_status(db, competition)


def refresh_competition_status(db: Session, competition_id: str) -> CompetitionStatus:
    competition = get_competition(db, competition_id)
    if competition.status not in [CompetitionStatus.DRAFT, CompetitionStatus.READY]:
        return competition.status

    setup_status = setup_service.get_competition_setup_status(db, competition)
    new_status = CompetitionStatus.READY if setup_status["is_ready"] else CompetitionStatus.DRAFT

    if competition.status != new_status:
        old_status = competition.status
        competition.status = new_status
        db.commit()
        db.refresh(competition)
        _audit(
            db,
            event_id=competition.event_id,
            competition_id=competition.id,
            action="competition_status_auto_updated",
            entity_type="competition",
            entity_id=competition.id,
            details_json={"old_status": old_status.value, "new_status": new_status.value},
        )
    return new_status


def populate_competition_fake_data(
    db: Session,
    competition_id: str,
    num_participants: int = 4,
    num_judges: int = 3,
    num_criteria: int = 3,
) -> None:
    competition = get_competition(db, competition_id)
    _ensure_competition_configuration_editable(competition)

    # Check if competition already has participants, criteria, or judges
    has_participants = len(competition.participants) > 0
    has_judge_criteria = len(competition.judge_criteria) > 0
    has_public_criteria = len(competition.public_criteria) > 0

    has_judges_assigned = db.scalar(
        select(CompetitionJudge).where(CompetitionJudge.competition_id == competition_id)
    ) is not None

    if has_participants or has_judge_criteria or has_public_criteria or has_judges_assigned:
        raise AdminStateError(
            "La competizione contiene già dati (partecipanti, criteri o giudici) "
            "e non può essere popolata con dati fake."
        )

    # Generate fake participants with name and surname
    first_names = [
        "Alessandro", "Sofia", "Francesco", "Giulia", "Lorenzo",
        "Alice", "Mattia", "Aurora", "Andrea", "Emma",
        "Gabriele", "Giorgia", "Riccardo", "Beatrice", "Tommaso",
        "Sara", "Davide", "Martina", "Federico", "Chiara"
    ]
    last_names = [
        "Rossi", "Ferrari", "Russo", "Bianchi", "Romano",
        "Colombo", "Ricci", "Marini", "Greco", "Bruno",
        "Gallo", "Conti", "De Luca", "Costa", "Giordano",
        "Mancini", "Bernardi", "Rizzo", "Moretti", "Barbieri"
    ]

    for index in range(1, num_participants + 1):
        first_name = first_names[(index - 1) % len(first_names)]
        last_name = last_names[((index - 1) // len(first_names)) % len(last_names)]
        full_name = f"{first_name} {last_name}"
        slug = f"{first_name.lower()}_{last_name.lower()}"
        if index > len(first_names) * len(last_names):
            full_name += f" {index}"
            slug += f"_{index}"

        db.add(
            Participant(
                competition_id=competition_id,
                name=slug,
                display_name=full_name,
                order_index=index,
                active=True,
            )
        )

    # Generate fake judge criteria (if judge voting is enabled)
    if competition.judge_voting_enabled:
        fake_judge_criteria = [
            "Intonazione", "Presenza scenica", "Originalita", "Interpretazione",
            "Arrangiamento", "Testo", "Look", "Carisma", "Vocalita", "Emozione"
        ]
        for index in range(1, num_criteria + 1):
            criterion_name = fake_judge_criteria[(index - 1) % len(fake_judge_criteria)]
            if index > len(fake_judge_criteria):
                criterion_name += f"_{index}"
            db.add(
                JudgeCriterion(
                    competition_id=competition_id,
                    name=criterion_name,
                    weight=1.0,
                    order_index=index,
                    active=True,
                )
            )

    # Generate fake public criteria (if public voting is enabled and method is criteria_rating)
    if competition.public_voting_enabled and competition.public_vote_method == PublicVoteMethod.CRITERIA_RATING:
        fake_public_criteria = [
            "Gradimento generale", "Ritmo", "Emozione", "Originalita",
            "Testo", "Energia", "Coreografia", "Stile", "Coinvolgimento"
        ]
        for index in range(1, num_criteria + 1):
            criterion_name = fake_public_criteria[(index - 1) % len(fake_public_criteria)]
            if index > len(fake_public_criteria):
                criterion_name += f"_{index}"
            db.add(
                PublicVoteCriterion(
                    competition_id=competition_id,
                    name=criterion_name,
                    weight=1.0,
                    order_index=index,
                    active=True,
                )
            )

    # Generate/assign judges (if judge voting is enabled)
    if competition.judge_voting_enabled:
        event = competition.event
        event_judges = list(event.judges)

        # Top up event judges to match num_judges if there are fewer
        current_judges_count = len(event_judges)
        if current_judges_count < num_judges:
            for index in range(current_judges_count + 1, num_judges + 1):
                access_code = token_urlsafe(8)  # short for ease of demo access
                new_judge = Judge(
                    event_id=event.id,
                    name=f"giudice-{index}",
                    display_name=f"Giudice {index}",
                    access_code_hash=hash_secret(access_code),
                    active=True,
                )
                db.add(new_judge)
                event_judges.append(new_judge)

            db.flush()  # to get judge IDs if created

        # Assign judges to this competition
        for judge in event_judges[:num_judges]:
            db.add(
                CompetitionJudge(
                    competition_id=competition_id,
                    judge_id=judge.id,
                )
            )

    db.commit()
    refresh_competition_status(db, competition_id)

    _audit(
        db,
        event_id=competition.event_id,
        competition_id=competition.id,
        action="admin_competition_seeded_fake_data",
        entity_type="competition",
        entity_id=competition.id,
        details_json={
            "participants_count": num_participants,
            "judges_count": num_judges if competition.judge_voting_enabled else 0,
            "judge_voting_enabled": competition.judge_voting_enabled,
            "public_voting_enabled": competition.public_voting_enabled,
        },
    )

