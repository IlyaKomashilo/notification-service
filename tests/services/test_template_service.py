import pytest

from src.exceptions.templates import (
    TemplateAlreadyExistsError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from src.models.template import Template
from src.schemas.templates import TemplateCreate
from src.services.template_service import TemplateService


class FakeTemplatesRepository:
    def __init__(self, templates: list[Template] | None = None) -> None:
        if templates is None:
            templates = []

        self.templates = {template.code: template for template in templates}

    async def get_by_code(self, code: str) -> Template | None:
        return self.templates.get(code)

    async def add(self, payload: TemplateCreate) -> Template:
        template = Template(
            code=payload.code,
            subject=payload.subject,
            body=payload.body,
        )
        self.templates[template.code] = template
        return template

    async def get_all(self) -> list[Template]:
        return list(self.templates.values())


def create_template(code: str = "booking_created") -> Template:
    return Template(
        code=code,
        subject="Booking {{ booking_id }}",
        body="Hello, {{ username }}!",
    )


async def test_create_template() -> None:
    repo = FakeTemplatesRepository()
    service = TemplateService(repo)
    payload = TemplateCreate(
        code="booking_created",
        subject="Booking {{ booking_id }}",
        body="Hello, {{ username }}!",
    )

    result = await service.create_template(payload)

    assert result.code == payload.code
    assert result.subject == payload.subject
    assert result.body == payload.body
    assert repo.templates[payload.code] is result
    assert len(repo.templates) == 1


async def test_create_existing_template() -> None:
    template = create_template()
    repo = FakeTemplatesRepository([template])
    service = TemplateService(repo)
    payload = TemplateCreate(
        code=template.code,
        subject="Changed subject",
        body="Changed body",
    )

    with pytest.raises(TemplateAlreadyExistsError):
        await service.create_template(payload)

    assert len(repo.templates) == 1
    assert repo.templates[template.code] is template
    assert template.subject == "Booking {{ booking_id }}"
    assert template.body == "Hello, {{ username }}!"


async def test_get_template() -> None:
    first = create_template()
    second = create_template(code="booking_cancelled")
    repo = FakeTemplatesRepository([first, second])
    service = TemplateService(repo)

    result = await service.get_template(second.code)

    assert result is second


async def test_get_missing_template() -> None:
    template = create_template()
    repo = FakeTemplatesRepository([template])
    service = TemplateService(repo)

    with pytest.raises(TemplateNotFoundError):
        await service.get_template("missing_template")


async def test_get_templates() -> None:
    first = create_template()
    second = create_template(code="booking_cancelled")
    repo = FakeTemplatesRepository([first, second])
    service = TemplateService(repo)

    result = await service.get_templates()

    assert result == [first, second]


async def test_get_empty_templates() -> None:
    repo = FakeTemplatesRepository()
    service = TemplateService(repo)

    result = await service.get_templates()

    assert result == []


async def test_render_template() -> None:
    template = create_template()
    repo = FakeTemplatesRepository([template])
    service = TemplateService(repo)
    context = {"booking_id": 123, "username": "Ilya"}

    result = await service.render_template(template.code, context)

    assert result.subject == "Booking 123"
    assert result.body == "Hello, Ilya!"
    assert template.subject == "Booking {{ booking_id }}"
    assert template.body == "Hello, {{ username }}!"


async def test_render_missing_template() -> None:
    repo = FakeTemplatesRepository()
    service = TemplateService(repo)
    context = {"booking_id": 123, "username": "Ilya"}

    with pytest.raises(TemplateNotFoundError):
        await service.render_template("missing_template", context)


async def test_render_without_subject_variable() -> None:
    template = create_template()
    repo = FakeTemplatesRepository([template])
    service = TemplateService(repo)
    context = {"username": "Ilya"}

    with pytest.raises(TemplateRenderError):
        await service.render_template(template.code, context)


async def test_render_without_body_variable() -> None:
    template = create_template()
    repo = FakeTemplatesRepository([template])
    service = TemplateService(repo)
    context = {"booking_id": 123}

    with pytest.raises(TemplateRenderError):
        await service.render_template(template.code, context)
