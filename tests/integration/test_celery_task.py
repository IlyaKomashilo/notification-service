import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from aiosmtplib import SMTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.exceptions.notifications import NotificationStatusError
from src.models.notification import Notification
from src.models.template import Template
from src.services.email_sender import EmailSender
from src.tasks import notifications as notification_tasks


@pytest_asyncio.fixture
async def notification_id(db_engine, monkeypatch):
    settings = get_settings()
    test_settings = settings.model_copy(
        update={"database_url": settings.test_database_url}
    )
    monkeypatch.setattr(notification_tasks, "get_settings", lambda: test_settings)

    template_code = f"test_{uuid4().hex}"
    notification_id = uuid4()

    try:
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                session.add(
                    Template(
                        code=template_code,
                        subject="Welcome, {{ username }}!",
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

        yield notification_id
    finally:
        async with AsyncSession(db_engine) as session:
            async with session.begin():
                await session.execute(
                    delete(Notification).where(Notification.id == notification_id)
                )
                await session.execute(
                    delete(Template).where(Template.code == template_code)
                )


async def test_task_sends_notification(notification_id, db_engine, monkeypatch):
    sent = []

    async def fake_send(self, recipient, subject, body):
        sent.append((recipient, subject, body))

    monkeypatch.setattr(EmailSender, "send", fake_send)

    await asyncio.to_thread(
        notification_tasks.send_notification_task.run, str(notification_id)
    )

    assert sent == [("ilya@example.com", "Welcome, Ilya!", "Hello, Ilya!")]
    async with AsyncSession(db_engine) as session:
        notification = await session.get(Notification, notification_id)
        assert notification.status == "sent"


async def test_task_marks_failed_when_email_fails(
    notification_id, db_engine, monkeypatch
):
    async def fake_send(self, recipient, subject, body):
        raise SMTPException("SMTP unavailable")

    monkeypatch.setattr(EmailSender, "send", fake_send)

    with pytest.raises(SMTPException):
        await asyncio.to_thread(
            notification_tasks.send_notification_task.run, str(notification_id)
        )

    async with AsyncSession(db_engine) as session:
        notification = await session.get(Notification, notification_id)
        assert notification.status == "failed"


async def test_task_does_not_send_twice(notification_id, db_engine, monkeypatch):
    sent = []

    async def fake_send(self, recipient, subject, body):
        sent.append(recipient)

    monkeypatch.setattr(EmailSender, "send", fake_send)

    await asyncio.to_thread(
        notification_tasks.send_notification_task.run, str(notification_id)
    )

    with pytest.raises(NotificationStatusError):
        await asyncio.to_thread(
            notification_tasks.send_notification_task.run, str(notification_id)
        )

    assert sent == ["ilya@example.com"]
    async with AsyncSession(db_engine) as session:
        notification = await session.get(Notification, notification_id)
        assert notification.status == "sent"
