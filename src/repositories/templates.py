from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.template import Template
from src.schemas.templates import TemplateCreate


class TemplatesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, payload: TemplateCreate) -> Template:
        template = Template(**payload.model_dump())
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_by_code(self, code: str) -> Template | None:
        return await self.session.get(Template, code)

    async def get_all(self) -> list[Template]:
        stmt = select(Template).order_by(Template.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
