from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_template_service(session: SessionDep) -> TemplateService:
    repository = TemplatesRepository(session)
    return TemplateService(repository)


TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]


async def get_notification_service(
    session: SessionDep,
    template_service: TemplateServiceDep,
) -> NotificationService:
    repository = NotificationsRepository(session)
    return NotificationService(repository, template_service)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
