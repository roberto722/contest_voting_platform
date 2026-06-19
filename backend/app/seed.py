from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    Event,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVoteMethod,
)


def create_demo_data(session: Session) -> Event:
    existing = session.scalar(select(Event).where(Event.name == "Serata Contest Demo"))
    if existing is not None:
        return existing

    event = Event(name="Serata Contest Demo", description="Evento demo per sviluppo locale")

    performance = Competition(
        event=event,
        name="Miglior Performance Musicale",
        public_vote_method=PublicVoteMethod.SINGLE_CHOICE,
        public_weight=50,
        judge_weight=50,
    )
    costume = Competition(
        event=event,
        name="Miglior Costume",
        public_vote_method=PublicVoteMethod.RANKED_CHOICE,
        public_weight=50,
        judge_weight=50,
    )

    names = ["Anna", "Marco", "Luca", "Giulia"]
    for index, name in enumerate(names, start=1):
        performance.participants.append(
            Participant(name=name.lower(), display_name=name, order_index=index)
        )
        costume.participants.append(
            Participant(name=name.lower(), display_name=name, order_index=index)
        )

    for index, name in enumerate(["Giudice 1", "Giudice 2", "Giudice 3"], start=1):
        event.judges.append(
            Judge(
                name=f"judge-{index}",
                display_name=name,
                access_code_hash=f"demo-judge-{index}-hash",
            )
        )

    performance_criteria = ["Intonazione", "Presenza scenica", "Originalita"]
    for index, criterion_name in enumerate(performance_criteria, start=1):
        performance.judge_criteria.append(
            JudgeCriterion(name=criterion_name, weight=1, order_index=index)
        )

    costume_criteria = ["Creativita", "Realizzazione", "Impatto scenico"]
    for index, criterion_name in enumerate(costume_criteria, start=1):
        costume.judge_criteria.append(
            JudgeCriterion(name=criterion_name, weight=1, order_index=index)
        )

    # Associa i giudici alle competizioni
    from app.models import CompetitionJudge
    for judge in event.judges:
        session.add(CompetitionJudge(competition=performance, judge=judge))
        session.add(CompetitionJudge(competition=costume, judge=judge))

    session.add(event)
    return event
