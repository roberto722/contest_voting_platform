from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    competition_id: str | None
    actor_type: str
    actor_id: str | None
    actor_label: str | None
    action: str
    entity_type: str
    entity_id: str | None
    details_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
