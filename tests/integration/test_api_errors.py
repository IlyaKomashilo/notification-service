from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from aiosmtplib.errors import SMTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_email_sender
from src.db.database import get_db
from src.main import app
from src.repositories.notifications import NotificationsRepository


class FakeSender:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.calls = 0
        self.recipient = None
        self.subject = None
        self.body = None
        self.fail = False
        self.transaction_open = None

    async def send(self, recipient: str, subject: str, body: str) -> None:
        self.calls += 1
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.transaction_open = self.session.in_transaction()

        if self.fail:
            raise SMTPException("SMTP server unavailable")


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def get_test_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = get_test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def sender(client: AsyncClient, db_session: AsyncSession) -> FakeSender:
    fake = FakeSender(db_session)

    def get_test_sender() -> FakeSender:
        return fake

    app.dependency_overrides[get_email_sender] = get_test_sender
    return fake


@pytest.fixture
def template_payload() -> dict:
    return {
        "code": f"test_{uuid4().hex}",
        "subject": "Booking confirmed",
        "body": "Hello, {{ username }}!",
    }


def notification_payload(template_code: str) -> dict:
    return {
        "template_code": template_code,
        "recipient": "ilya@example.com",
        "context": {"username": "Ilya"},
        "idempotency_key": f"test-{uuid4().hex}",
    }


@pytest_asyncio.fixture
async def notification_id(client: AsyncClient, template_payload: dict) -> str:
    template_payload["subject"] = "Booking for {{ username }}"
    response = await client.post("/templates", json=template_payload)
    assert response.status_code == 201

    payload = notification_payload(template_payload["code"])
    response = await client.post("/notifications", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


async def set_status(
    db_session: AsyncSession, notification_id: str, status: str
) -> None:
    repo = NotificationsRepository(db_session)
    async with db_session.begin():
        notification = await repo.get_by_id(UUID(notification_id))
        await repo.update_status(notification, status)


async def test_get_missing_template(client: AsyncClient) -> None:
    response = await client.get(f"/templates/missing_{uuid4().hex}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Template not found"}


async def test_render_missing_template(client: AsyncClient) -> None:
    response = await client.post(
        f"/templates/missing_{uuid4().hex}/render",
        json={"context": {}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Template not found"}


async def test_create_existing_template(
    client: AsyncClient, template_payload: dict
) -> None:
    first = await client.post("/templates", json=template_payload)
    assert first.status_code == 201

    response = await client.post("/templates", json=template_payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Template already exists"}


async def test_render_missing_variable(
    client: AsyncClient, template_payload: dict
) -> None:
    created = await client.post("/templates", json=template_payload)
    assert created.status_code == 201

    response = await client.post(
        f"/templates/{template_payload['code']}/render",
        json={"context": {}},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Template rendering error: 'username' is undefined",
    }


async def test_notification_missing_template(client: AsyncClient) -> None:
    payload = notification_payload(f"missing_{uuid4().hex}")

    response = await client.post("/notifications", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Template not found"}


async def test_notification_conflict(
    client: AsyncClient, template_payload: dict
) -> None:
    created = await client.post("/templates", json=template_payload)
    assert created.status_code == 201
    payload = notification_payload(template_payload["code"])
    first = await client.post("/notifications", json=payload)
    assert first.status_code == 201

    payload["recipient"] = "other@example.com"
    response = await client.post("/notifications", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Idempotency key is already used"}


async def test_notification_repeat(client: AsyncClient, template_payload: dict) -> None:
    created = await client.post("/templates", json=template_payload)
    assert created.status_code == 201
    payload = notification_payload(template_payload["code"])
    first = await client.post("/notifications", json=payload)
    assert first.status_code == 201

    response = await client.post("/notifications", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == first.json()["id"]


async def test_send_missing_notification(
    client: AsyncClient, sender: FakeSender
) -> None:
    response = await client.post(f"/notifications/{uuid4()}/send")

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found"}
    assert sender.calls == 0


async def test_send_processing_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_id: str,
    sender: FakeSender,
) -> None:
    await set_status(db_session, notification_id, "processing")

    response = await client.post(f"/notifications/{notification_id}/send")

    assert response.status_code == 409
    assert response.json() == {"detail": "Notification is not pending"}
    assert sender.calls == 0
    saved = await client.get(f"/notifications/{notification_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "processing"


async def test_send_sent_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_id: str,
    sender: FakeSender,
) -> None:
    await set_status(db_session, notification_id, "sent")

    response = await client.post(f"/notifications/{notification_id}/send")

    assert response.status_code == 409
    assert response.json() == {"detail": "Notification is not pending"}
    assert sender.calls == 0
    saved = await client.get(f"/notifications/{notification_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "sent"


async def test_send_failed_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_id: str,
    sender: FakeSender,
) -> None:
    await set_status(db_session, notification_id, "failed")

    response = await client.post(f"/notifications/{notification_id}/send")

    assert response.status_code == 409
    assert response.json() == {"detail": "Notification is not pending"}
    assert sender.calls == 0
    saved = await client.get(f"/notifications/{notification_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "failed"


async def test_send_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_id: str,
    sender: FakeSender,
) -> None:
    response = await client.post(f"/notifications/{notification_id}/send")

    assert response.status_code == 200
    assert response.json()["id"] == notification_id
    assert response.json()["status"] == "sent"
    assert sender.calls == 1
    assert sender.recipient == "ilya@example.com"
    assert sender.subject == "Booking for Ilya"
    assert sender.body == "Hello, Ilya!"
    assert sender.transaction_open is False

    db_session.expunge_all()
    saved = await client.get(f"/notifications/{notification_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "sent"


async def test_send_notification_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_id: str,
    sender: FakeSender,
) -> None:
    sender.fail = True

    response = await client.post(f"/notifications/{notification_id}/send")

    assert response.status_code == 502
    assert response.json() == {"detail": "Email sending failed"}
    assert sender.calls == 1
    assert sender.transaction_open is False

    db_session.expunge_all()
    saved = await client.get(f"/notifications/{notification_id}")
    assert saved.status_code == 200
    assert saved.json()["status"] == "failed"
