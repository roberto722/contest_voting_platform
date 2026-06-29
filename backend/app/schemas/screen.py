from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import ScreenMode


class ScreenStateUpdate(BaseModel):
    competition_id: str | None = None
    mode: ScreenMode = ScreenMode.IDLE
    payload_json: dict[str, Any] | None = None


class ScreenStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    competition_id: str | None
    mode: ScreenMode
    payload_json: dict[str, Any]
