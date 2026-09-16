from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.main import app


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


async def test_create_existing_template(client: AsyncClient, template_payload: dict) -> None:
    first = await client.post("/templates", json=template_payload)
    assert first.status_code == 201

    response = await client.post("/templates", json=template_payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Template already exists"}


async def test_render_missing_variable(client: AsyncClient, template_payload: dict) -> None:
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


async def test_notification_conflict(client: AsyncClient, template_payload: dict) -> None:
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
