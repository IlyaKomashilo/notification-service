from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.template import Template
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.schemas.notifications import NotificationCreate
from src.schemas.templates import TemplateCreate


@pytest_asyncio.fixture
async def template(db_session: AsyncSession) -> Template:
    repo = TemplatesRepository(db_session)
    payload = TemplateCreate(
        code=f"test_{uuid4().hex}",
        subject="Booking {{ booking_id }}",
        body="Your booking {{ booking_id }} is confirmed.",
    )
    return await repo.add(payload)


def create_payload(template_code: str) -> NotificationCreate:
    return NotificationCreate(
        template_code=template_code,
        recipient="ilya@example.com",
        context={"booking_id": 123},
        idempotency_key=f"test-{uuid4().hex}",
    )


async def test_save_notification(db_session: AsyncSession, template: Template) -> None:
    repo = NotificationsRepository(db_session)
    payload = create_payload(template.code)

    notification = await repo.add(payload)
    notification_id = notification.id
    await db_session.commit()
    db_session.expunge_all()

    result = await repo.get_by_id(notification_id)

    assert result is not None
    assert result is not notification
    assert result.template_code == payload.template_code
    assert result.recipient == payload.recipient
    assert result.context == payload.context
    assert result.idempotency_key == payload.idempotency_key
    assert result.status == "pending"
    assert result.created_at is not None


async def test_missing_template(db_session: AsyncSession) -> None:
    repo = NotificationsRepository(db_session)
    payload = create_payload(f"missing_{uuid4().hex}")

    with pytest.raises(IntegrityError) as error:
        await repo.add(payload)

    db_error = error.value.orig.__cause__
    assert db_error.constraint_name == "fk_notifications_template_code_templates"

    await db_session.rollback()
    result = await repo.get_by_idempotency_key(payload.idempotency_key)
    assert result is None


async def test_duplicate_key(db_session: AsyncSession, template: Template) -> None:
    repo = NotificationsRepository(db_session)
    payload = create_payload(template.code)
    notification = await repo.add(payload)
    notification_id = notification.id
    await db_session.commit()

    with pytest.raises(IntegrityError) as error:
        await repo.add(payload)

    db_error = error.value.orig.__cause__
    assert db_error.constraint_name == "uq_notifications_idempotency_key"

    await db_session.rollback()
    result = await repo.get_by_idempotency_key(payload.idempotency_key)
    assert result is not None
    assert result.id == notification_id
