from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


class EventStatus(StrEnum):
    DRAFT = "draft"
    LIVE = "live"
    CLOSED = "closed"
    ARCHIVED = "archived"


class PublicVoteMethod(StrEnum):
    SINGLE_CHOICE = "single_choice"
    RANKED_CHOICE = "ranked_choice"
    CRITERIA_RATING = "criteria_rating"


class CompetitionStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    VOTING_OPEN = "voting_open"
    VOTING_CLOSED = "voting_closed"
    RESULTS_FROZEN = "results_frozen"
    REVEALED = "revealed"


class VotingSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ScreenMode(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    REVEAL_RANKING = "reveal_ranking"
    SHOW_PODIUM = "show_podium"
