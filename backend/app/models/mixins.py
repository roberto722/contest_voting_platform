from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid4())


class IdMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
