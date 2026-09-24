import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.consumers import booking_events
from src.exceptions.notifications import IdempotencyConflictError
from src.models.notification import Notification
from src.models.template import Template
from src.repositories.notifications import NotificationsRepository
from src.schemas.notifications import NotificationCreate


@pytest_asyncio.fixture
async def payload(db_engine, monkeypatch):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr(booking_events, "async_session_factory", factory)
    template_code = f"test_{uuid4().hex}"
    try:
        async with factory.begin() as session:
            session.add(
                Template(code=template_code, subject="Booking", body="Confirmed")
            )
        yield NotificationCreate(
            template_code=template_code,
            recipient="ilya@example.com",
            context={"booking_id": 123},
            idempotency_key=f"test-{uuid4().hex}",
        )
    finally:
        async with factory.begin() as session:
            await session.execute(
                delete(Notification).where(Notification.template_code == template_code)
            )
            await session.execute(
                delete(Template).where(Template.code == template_code)
            )


@pytest.fixture
def wait_for_both(monkeypatch):
    barrier = asyncio.Barrier(2)
    original = NotificationsRepository.get_by_idempotency_key

    async def get_by_key(self, key):
        result = await original(self, key)
        if result is None:
            await barrier.wait()
        return result

    monkeypatch.setattr(NotificationsRepository, "get_by_idempotency_key", get_by_key)


async def get_notification(key):
    async with booking_events.async_session_factory() as session:
        repo = NotificationsRepository(session)
        return await repo.get_by_idempotency_key(key)


async def test_save_and_repeat(payload):
    await booking_events.save_notification(payload)
    await booking_events.save_notification(payload)

    saved = await get_notification(payload.idempotency_key)
    assert saved is not None
    assert saved.recipient == payload.recipient
    assert saved.status == "pending"


async def test_existing_conflict(payload):
    await booking_events.save_notification(payload)
    changed = payload.model_copy()
    changed.recipient = "other@example.com"

    with pytest.raises(IdempotencyConflictError):
        await booking_events.save_notification(changed)


async def test_concurrent_same_event(payload, wait_for_both):
    async with asyncio.timeout(10):
        results = await asyncio.gather(
            booking_events.save_notification(payload),
            booking_events.save_notification(payload),
            return_exceptions=True,
        )

    assert results == [None, None]
    saved = await get_notification(payload.idempotency_key)
    assert saved is not None
    assert saved.recipient == payload.recipient


async def test_concurrent_conflict(payload, wait_for_both):
    changed = payload.model_copy()
    changed.recipient = "other@example.com"
    async with asyncio.timeout(10):
        results = await asyncio.gather(
            booking_events.save_notification(payload),
            booking_events.save_notification(changed),
            return_exceptions=True,
        )

    saved = await get_notification(payload.idempotency_key)
    assert saved is not None

    if results[0] is None:
        assert isinstance(results[1], IdempotencyConflictError)
        assert saved.recipient == payload.recipient
    else:
        assert results[1] is None
        assert isinstance(results[0], IdempotencyConflictError)
        assert saved.recipient == changed.recipient


async def test_other_database_error_is_not_hidden(payload):
    invalid = payload.model_copy()
    invalid.recipient = None
    with pytest.raises(IntegrityError):
        await booking_events.save_notification(invalid)

    await booking_events.save_notification(payload)
