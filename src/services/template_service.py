from typing import Any

from jinja2 import UndefinedError

from src.exceptions.templates import TemplateAlreadyExistsError, TemplateNotFoundError, TemplateRenderError
from src.models.template import Template
from src.repositories.templates import TemplatesRepository
from src.schemas.templates import TemplateCreate, TemplateRenderResponse
from src.services.template_renderer import render_template as render_jinja_template


class TemplateService:
    def __init__(self, repository: TemplatesRepository) -> None:
        self.repository = repository

    async def create_template(self, payload: TemplateCreate) -> Template:
        existing = await self.repository.get_by_code(payload.code)

        if existing is not None:
            raise TemplateAlreadyExistsError("Template already exists")

        return await self.repository.add(payload)

    async def get_template(self, code: str) -> Template:
        existing = await self.repository.get_by_code(code)

        if existing is None:
            raise TemplateNotFoundError("Template not found")

        return existing

    async def get_templates(self) -> list[Template]:
        return await self.repository.get_all()

    async def render_template(self, code: str, context: dict[str, Any]) -> TemplateRenderResponse:
        template = await self.get_template(code)

        try:
            rendered_subject = render_jinja_template(template_body=template.subject, context=context)
            rendered_body = render_jinja_template(template_body=template.body, context=context)
        except UndefinedError as error:
            raise TemplateRenderError(f"Template rendering error: {error}") from error

        return TemplateRenderResponse(subject=rendered_subject, body=rendered_body)