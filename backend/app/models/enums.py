from enum import StrEnum


class EventStatus(StrEnum):
    DRAFT = "draft"
    LIVE = "live"
    CLOSED = "closed"
    ARCHIVED = "archived"


class PublicVoteMethod(StrEnum):
    SINGLE_CHOICE = "single_choice"
    RANKED_CHOICE = "ranked_choice"
    CRITERIA_RATING = "criteria_rating"


class AccessMethod(StrEnum):
    PUBLIC_LINK = "public_link"
    QR_PIN = "qr_pin"
    PRIVATE_LINK = "private_link"


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
    SHOW_QR = "show_qr"
    VOTING_OPEN = "voting_open"
    COUNTDOWN = "countdown"
    SHOW_RESULTS = "show_results"
    REVEAL_RANKING = "reveal_ranking"
    SHOW_PODIUM = "show_podium"
    SHOW_FINAL_WINNERS = "show_final_winners"
