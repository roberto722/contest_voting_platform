from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    CompetitionJudge,
    Event,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVoteMethod,
    VoterAccount,
)
from app.services.access_service import generate_voter_code, hash_secret


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

    # Demo voter accounts (codes printed to stdout for dev convenience)
    voter_names = ["Anna", "Marco", "Luca", "Giulia", "Votante Demo 1", "Votante Demo 2"]
    voter_accounts = []
    for name in voter_names:
        code = generate_voter_code()
        va = VoterAccount(
            event=event,
            display_name=name,
            access_code_hash=hash_secret(code),
            access_token=f"demo-token-{name.lower().replace(' ', '-')}",
            active=True,
        )
        voter_accounts.append((va, code))
        print(f"[SEED] VoterAccount '{name}': code={code}, token=demo-token-{name.lower().replace(' ', '-')}")

    participant_names = ["Anna", "Marco", "Luca", "Giulia"]
    performance_participants = []
    costume_participants = []

    for index, name in enumerate(participant_names, start=1):
        pp = Participant(name=name.lower(), display_name=name, order_index=index)
        performance.participants.append(pp)
        performance_participants.append(pp)

        cp = Participant(name=name.lower(), display_name=name, order_index=index)
        costume.participants.append(cp)
        costume_participants.append(cp)

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

    for judge in event.judges:
        session.add(CompetitionJudge(competition=performance, judge=judge))
        session.add(CompetitionJudge(competition=costume, judge=judge))

    session.add(event)
    # Flush to get IDs before linking participants to voter accounts
    session.flush()

    # Link first 4 voter accounts to the corresponding participants
    # Each participant-voter is linked in BOTH competitions
    for i, (va, _) in enumerate(voter_accounts[:4]):
        performance_participants[i].voter_account_id = va.id
        costume_participants[i].voter_account_id = va.id

    return event
