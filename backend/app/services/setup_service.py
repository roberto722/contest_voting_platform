from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Competition,
    CompetitionJudge,
    CompetitionStatus,
    Event,
    EventStatus,
    Judge,
    JudgeCriterion,
    Participant,
    PublicVoteCriterion,
    PublicVoteMethod,
)

FINAL_COMPETITION_STATUSES = {
    CompetitionStatus.REVEALED,
}


def get_competition_setup_status(db: Session, competition: Competition) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    issues: list[str] = []
    messages: list[str] = []

    def add_check(step: str, completed: bool, message: str, issue: str | None = None) -> None:
        checks.append({"step": step, "completed": completed, "message": message})
        messages.append(message)
        if not completed and issue is not None:
            issues.append(issue)

    active_participants = db.scalar(
        select(func.count(Participant.id)).where(
            Participant.competition_id == competition.id,
            Participant.active.is_(True),
        )
    ) or 0
    add_check(
        "participants",
        active_participants >= 2,
        (
            f"{active_participants} partecipanti attivi configurati"
            if active_participants >= 2
            else "Servono almeno 2 partecipanti attivi"
        ),
        "missing_active_participants",
    )

    has_voting_mode = competition.public_voting_enabled or competition.judge_voting_enabled
    add_check(
        "voting_modes",
        has_voting_mode,
        (
            "Almeno una modalita di voto e abilitata"
            if has_voting_mode
            else "Abilita voto pubblico o voto giudici"
        ),
        "missing_voting_mode",
    )

    if competition.public_voting_enabled:
        public_weight_ok = competition.public_weight > 0
        add_check(
            "public_weight",
            public_weight_ok,
            (
                f"Peso pubblico valido: {competition.public_weight:g}"
                if public_weight_ok
                else "Il peso pubblico deve essere maggiore di 0"
            ),
            "invalid_public_weight",
        )

        public_method_ok = competition.public_vote_method is not None
        add_check(
            "public_method",
            public_method_ok,
            (
                f"Metodo pubblico configurato: {competition.public_vote_method.value}"
                if public_method_ok
                else "Configura il metodo di voto pubblico"
            ),
            "missing_public_vote_method",
        )

        if competition.public_vote_method == PublicVoteMethod.CRITERIA_RATING:
            public_criteria = db.scalar(
                select(func.count(PublicVoteCriterion.id)).where(
                    PublicVoteCriterion.competition_id == competition.id,
                    PublicVoteCriterion.active.is_(True),
                )
            ) or 0
            add_check(
                "public_criteria",
                public_criteria > 0,
                (
                    f"{public_criteria} criteri pubblici attivi"
                    if public_criteria > 0
                    else "Aggiungi almeno un criterio pubblico attivo"
                ),
                "missing_public_criteria",
            )
    else:
        checks.append(
            {
                "step": "public_voting",
                "completed": True,
                "message": "Voto pubblico non richiesto",
            }
        )

    if competition.judge_voting_enabled:
        judge_weight_ok = competition.judge_weight > 0
        add_check(
            "judge_weight",
            judge_weight_ok,
            (
                f"Peso giudici valido: {competition.judge_weight:g}"
                if judge_weight_ok
                else "Il peso giudici deve essere maggiore di 0"
            ),
            "invalid_judge_weight",
        )

        judge_criteria = db.scalar(
            select(func.count(JudgeCriterion.id)).where(
                JudgeCriterion.competition_id == competition.id,
                JudgeCriterion.active.is_(True),
            )
        ) or 0
        add_check(
            "judge_criteria",
            judge_criteria > 0,
            (
                f"{judge_criteria} criteri giudici attivi"
                if judge_criteria > 0
                else "Aggiungi almeno un criterio giudice attivo"
            ),
            "missing_judge_criteria",
        )

        assigned_judges = db.scalar(
            select(func.count(CompetitionJudge.id))
            .join(Judge, Judge.id == CompetitionJudge.judge_id)
            .where(
                CompetitionJudge.competition_id == competition.id,
                CompetitionJudge.active.is_(True),
                Judge.active.is_(True),
            )
        ) or 0
        add_check(
            "judges",
            assigned_judges > 0,
            (
                f"{assigned_judges} giudici attivi assegnati"
                if assigned_judges > 0
                else "Assegna almeno un giudice attivo alla competizione"
            ),
            "missing_assigned_judges",
        )
    else:
        checks.append(
            {
                "step": "judge_voting",
                "completed": True,
                "message": "Voto giudici non richiesto",
            }
        )


    if competition.status in FINAL_COMPETITION_STATUSES:
        messages.append("Risultati gia congelati o rivelati")

    event = competition.event
    event_live_issue = [] if event.status == EventStatus.LIVE else ["event_not_live"]
    final_issue = (
        ["competition_results_final"]
        if competition.status in FINAL_COMPETITION_STATUSES
        else []
    )
    open_issues = [*issues, *event_live_issue, *final_issue]
    if event.status != EventStatus.LIVE:
        messages.append("Evento in bozza: porta l'evento live prima di aprire votazioni")

    completed_steps = [check["step"] for check in checks if check["completed"]]
    missing_steps = [check["step"] for check in checks if not check["completed"]]

    return {
        "competition_id": competition.id,
        "event_id": competition.event_id,
        "is_ready": len(issues) == 0,
        "can_open_voting": len(open_issues) == 0,
        "completed_steps": completed_steps,
        "missing_steps": missing_steps,
        "issues": issues,
        "open_issues": open_issues,
        "messages": messages,
        "checks": checks,
    }


def get_event_setup_status(db: Session, event: Event) -> dict[str, Any]:
    competitions = list(
        db.scalars(
            select(Competition)
            .where(Competition.event_id == event.id)
            .order_by(Competition.name)
        )
    )
    issues: list[str] = []
    messages: list[str] = []
    competition_statuses = []

    if not competitions:
        issues.append("missing_competitions")
        messages.append("Crea almeno una competizione prima del live")

    for competition in competitions:
        status = get_competition_setup_status(db, competition)
        competition_statuses.append(status)
        if not status["is_ready"]:
            issues.append(f"competition_not_ready:{competition.id}")
            messages.append(f"{competition.name}: configurazione incompleta")

    return {
        "event_id": event.id,
        "can_go_live": len(issues) == 0,
        "issues": issues,
        "messages": messages,
        "competitions": competition_statuses,
    }
