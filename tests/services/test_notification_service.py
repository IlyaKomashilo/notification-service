from uuid import uuid4

import pytest

from src.exceptions.notifications import IdempotencyConflictError
from src.models.notification import Notification
from src.schemas.notifications import NotificationCreate
from src.services.notification_service import NotificationService


class FakeRepository:
    def __init__(self, existing: Notification | None = None) -> None:
        self.existing = existing
        self.created_payload = None
        self.searched_key = None

    async def get_by_idempotency_key(self, key: str) -> Notification | None:
        self.searched_key = key
        return self.existing

    async def add(self, payload: NotificationCreate) -> Notification:
        self.created_payload = payload

        return Notification(
            id=uuid4(),
            template_code=payload.template_code,
            recipient=payload.recipient,
            context=payload.context,
            idempotency_key=payload.idempotency_key,
            status="pending",
        )


def create_payload(
    idempotency_key: str | None = "booking-123-created",
    recipient: str = "ilya@example.com",
    context: dict | None = None,
) -> NotificationCreate:
    if context is None:
        context = {"booking_id": 123}

    return NotificationCreate(
        template_code="booking_created",
        recipient=recipient,
        context=context,
        idempotency_key=idempotency_key,
    )


def create_notification(
    idempotency_key: str | None = "booking-123-created",
    recipient: str = "ilya@example.com",
    context: dict | None = None,
) -> Notification:
    if context is None:
        context = {"booking_id": 123}

    return Notification(
        id=uuid4(),
        template_code="booking_created",
        recipient=recipient,
        context=context,
        idempotency_key=idempotency_key,
        status="pending",
    )


async def test_create_without_key() -> None:
    repo = FakeRepository()
    service = NotificationService(repo)
    payload = create_payload(idempotency_key=None)

    result = await service.create_notification(payload)

    assert repo.created_payload == payload
    assert result.idempotency_key is None


async def test_create_with_new_key() -> None:
    repo = FakeRepository()
    service = NotificationService(repo)
    payload = create_payload()

    result = await service.create_notification(payload)

    assert repo.searched_key == payload.idempotency_key
    assert repo.created_payload == payload
    assert result.idempotency_key == payload.idempotency_key


async def test_same_key_same_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    service = NotificationService(repo)
    payload = create_payload()

    result = await service.create_notification(payload)

    assert result is existing
    assert repo.created_payload is None


async def test_same_key_different_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    service = NotificationService(repo)
    payload = create_payload(context={"booking_id": 999})

    with pytest.raises(IdempotencyConflictError):
        await service.create_notification(payload)

    assert repo.created_payload is None


async def test_get_existing_same_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    service = NotificationService(repo)
    payload = create_payload()

    result = await service.get_existing_idempotent_notification(payload)

    assert result is existing


async def test_get_existing_different_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    service = NotificationService(repo)
    payload = create_payload(recipient="other@example.com")

    with pytest.raises(IdempotencyConflictError):
        await service.get_existing_idempotent_notification(payload)
