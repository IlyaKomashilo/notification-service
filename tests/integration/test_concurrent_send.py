import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.api.dependencies import get_email_sender
from src.db.database import get_db
from src.exceptions.notifications import NotificationStatusError
from src.main import app
from src.models.notification import Notification
from src.models.template import Template
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


class FakeSender:
    def __init__(self) -> None:
        self.calls = 0
        self.started = asyncio.Event()
        self.finish = asyncio.Event()

    async def send(self, recipient: str, subject: str, body: str) -> None:
        self.calls += 1
        self.started.set()
        await self.finish.wait()


async def test_concurrent_send(db_engine: AsyncEngine) -> None:
    template_code = f"test_{uuid4().hex}"
    notification_id = uuid4()
    sender = FakeSender()

    async def get_test_db() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

    def get_test_sender() -> FakeSender:
        return sender

    previous_overrides = app.dependency_overrides.copy()
    try:
        # Commit makes the test data visible to both request sessions.
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                session.add(
                    Template(
                        code=template_code,
                        subject="Booking confirmed",
                        body="Hello, {{ username }}!",
                    )
                )
                await session.flush()
                session.add(
                    Notification(
                        id=notification_id,
                        template_code=template_code,
                        recipient="ilya@example.com",
                        context={"username": "Ilya"},
                        status="pending",
                    )
                )

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_email_sender] = get_test_sender

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            url = f"/notifications/{notification_id}/send"
            first_request = asyncio.create_task(client.post(url))
            try:
                async with asyncio.timeout(10):
                    await sender.started.wait()

                    second = await client.post(url)
                    assert second.status_code == 409
                    assert second.json() == {"detail": "Notification is not pending"}
                    assert sender.calls == 1

                    sender.finish.set()
                    first = await first_request
                    assert first.status_code == 200
                    assert first.json()["status"] == "sent"
            finally:
                first_request.cancel()
                await asyncio.gather(first_request, return_exceptions=True)

        assert sender.calls == 1
        async with AsyncSession(db_engine) as session:
            saved = await session.get(Notification, notification_id)
            assert saved is not None
            assert saved.status == "sent"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        # These rows were committed, so an outer rollback cannot remove them.
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                await session.execute(
                    delete(Notification).where(Notification.id == notification_id)
                )
                await session.execute(
                    delete(Template).where(Template.code == template_code)
                )


async def test_prepare_send_waits_for_lock(db_engine: AsyncEngine) -> None:
    template_code = f"test_{uuid4().hex}"
    notification_id = uuid4()
    second_started = asyncio.Event()
    second_pid = None

    def make_service(session: AsyncSession) -> NotificationService:
        return NotificationService(
            NotificationsRepository(session),
            TemplateService(TemplatesRepository(session)),
        )

    async def prepare_second() -> None:
        nonlocal second_pid
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            async with session.begin():
                second_pid = await session.scalar(text("SELECT pg_backend_pid()"))
                second_started.set()
                await make_service(session).prepare_send(notification_id)

    try:
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                session.add(
                    Template(
                        code=template_code,
                        subject="Booking confirmed",
                        body="Hello, {{ username }}!",
                    )
                )
                await session.flush()
                session.add(
                    Notification(
                        id=notification_id,
                        template_code=template_code,
                        recipient="ilya@example.com",
                        context={"username": "Ilya"},
                        status="pending",
                    )
                )

        async with AsyncSession(db_engine, expire_on_commit=False) as first:
            second_task = None
            try:
                async with asyncio.timeout(10):
                    async with first.begin():
                        first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
                        notification, _ = await make_service(first).prepare_send(
                            notification_id
                        )
                        assert notification.status == "processing"

                        second_task = asyncio.create_task(prepare_second())
                        await second_started.wait()

                        # Ask PostgreSQL who blocks the second connection.
                        async with db_engine.connect() as observer:
                            while True:
                                blockers = await observer.scalar(
                                    text("SELECT pg_blocking_pids(:pid)"),
                                    {"pid": second_pid},
                                )
                                if first_pid in blockers:
                                    break
                                if second_task.done():
                                    await second_task
                                    pytest.fail("Second transaction did not wait")
                                await asyncio.sleep(0.01)

                        assert not second_task.done()

                    # Commit releases the lock and makes processing visible.
                    with pytest.raises(
                        NotificationStatusError, match="Notification is not pending"
                    ):
                        await second_task
            finally:
                if second_task is not None:
                    second_task.cancel()
                    await asyncio.gather(second_task, return_exceptions=True)

        async with AsyncSession(db_engine) as session:
            saved = await session.get(Notification, notification_id)
            assert saved is not None
            assert saved.status == "processing"
    finally:
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                await session.execute(
                    delete(Notification).where(Notification.id == notification_id)
                )
                await session.execute(
                    delete(Template).where(Template.code == template_code)
                )
