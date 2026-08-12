from enum import Enum
from typing import Any
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotificationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class NotificationCreate(BaseModel):
    template_code: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )

    recipient: str = Field(
        min_length=3,
        max_length=255,
    )

    context: dict[str, Any] = Field(default_factory=dict)

    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=120,
    )


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    template_code: str
    recipient: str
    status: NotificationStatus


class NotificationRecord(NotificationCreate):
    id: UUID
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = Field(
        default_factory=utcnow,
    )

