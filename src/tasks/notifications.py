import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.celery_app import app
from src.core.config import get_settings
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.services import notification_sender
from src.services.email_sender import EmailSender
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


@app.task
def send_notification_task(notification_id: str) -> None:
    asyncio.run(send_notification(notification_id))


async def send_notification(notification_id: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            template_repo = TemplatesRepository(session)
            template_service = TemplateService(template_repo)
            notification_repo = NotificationsRepository(session)
            notification_service = NotificationService(
                notification_repo, template_service
            )

            sender = EmailSender(
                host=settings.smtp_host,
                port=settings.smtp_port,
                sender=settings.smtp_from,
            )

            await notification_sender.send_notification(
                UUID(notification_id), session, notification_service, sender
            )
    finally:
        await engine.dispose()
