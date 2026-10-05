import pytest
from pydantic import ValidationError

from src.schemas.events import NotificationRequestedEvent


def test_notification_event() -> None:
    event = NotificationRequestedEvent.model_validate(
        {
            "event_id": "message-001",
            "event_type": "notification.requested",
            "template_code": "welcome_message",
            "recipient": "ilya@example.com",
            "context": {"username": "Ilya"},
        }
    )

    assert event.template_code == "welcome_message"
    assert event.context == {"username": "Ilya"}


def test_notification_event_needs_template_code() -> None:
    with pytest.raises(ValidationError):
        NotificationRequestedEvent.model_validate(
            {
                "event_id": "message-001",
                "event_type": "notification.requested",
                "recipient": "ilya@example.com",
            }
        )
