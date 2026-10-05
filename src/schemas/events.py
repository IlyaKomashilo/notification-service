from typing import Any, Literal

from pydantic import BaseModel, Field


class NotificationRequestedEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=120)
    event_type: Literal["notification.requested"]
    template_code: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )
    recipient: str = Field(min_length=3, max_length=255)
    context: dict[str, Any] = Field(default_factory=dict)
