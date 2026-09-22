from typing import Any, Literal

from pydantic import BaseModel, Field


class BookingConfirmedEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=120)
    event_type: Literal["booking.confirmed"]
    recipient: str = Field(min_length=3, max_length=255)
    context: dict[str, Any] = Field()
