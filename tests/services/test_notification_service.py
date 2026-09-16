from uuid import uuid4

import pytest

from src.exceptions.notifications import IdempotencyConflictError
from src.exceptions.templates import TemplateNotFoundError
from src.models.notification import Notification
from src.models.template import Template
from src.schemas.notifications import NotificationCreate
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


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


class FakeTemplateRepository:
    def __init__(self, existing: Template | None = None) -> None:
        self.existing = existing
        self.searched_code = None

    async def get_by_code(self, code: str) -> Template | None:
        self.searched_code = code

        if self.existing is not None and self.existing.code == code:
            return self.existing

        return None


def create_template() -> Template:
    return Template(
        code="booking_created",
        subject="Booking {{ booking_id }}",
        body="Your booking {{ booking_id }} is confirmed.",
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
    template_repo = FakeTemplateRepository(existing=create_template())
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload(idempotency_key=None)

    result = await service.create_notification(payload)

    assert repo.created_payload == payload
    assert result.idempotency_key is None
    assert template_repo.searched_code == payload.template_code


async def test_create_with_new_key() -> None:
    repo = FakeRepository()
    template_repo = FakeTemplateRepository(existing=create_template())
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload()

    result = await service.create_notification(payload)

    assert repo.searched_key == payload.idempotency_key
    assert repo.created_payload == payload
    assert result.idempotency_key == payload.idempotency_key
    assert template_repo.searched_code == payload.template_code


async def test_missing_template_without_key() -> None:
    repo = FakeRepository()
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload(idempotency_key=None)

    with pytest.raises(TemplateNotFoundError):
        await service.create_notification(payload)

    assert template_repo.searched_code == payload.template_code
    assert repo.created_payload is None


async def test_missing_template_with_new_key() -> None:
    repo = FakeRepository()
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload()

    with pytest.raises(TemplateNotFoundError):
        await service.create_notification(payload)

    assert repo.searched_key == payload.idempotency_key
    assert template_repo.searched_code == payload.template_code
    assert repo.created_payload is None


async def test_same_key_same_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload()

    result = await service.create_notification(payload)

    assert result is existing
    assert repo.created_payload is None
    assert template_repo.searched_code is None


async def test_same_key_different_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload(context={"booking_id": 999})

    with pytest.raises(IdempotencyConflictError):
        await service.create_notification(payload)

    assert repo.created_payload is None
    assert template_repo.searched_code is None


async def test_get_existing_same_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload()

    result = await service.get_existing_idempotent_notification(payload)

    assert result is existing
    assert repo.created_payload is None
    assert template_repo.searched_code is None


async def test_get_existing_different_payload() -> None:
    existing = create_notification()
    repo = FakeRepository(existing=existing)
    template_repo = FakeTemplateRepository()
    template_service = TemplateService(template_repo)
    service = NotificationService(repo, template_service)
    payload = create_payload(recipient="other@example.com")

    with pytest.raises(IdempotencyConflictError):
        await service.get_existing_idempotent_notification(payload)

    assert repo.created_payload is None
    assert template_repo.searched_code is None
