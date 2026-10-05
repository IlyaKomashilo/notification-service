from uuid import UUID

from aiosmtplib import SMTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import Notification
from src.services.email_sender import EmailSender
from src.services.notification_service import NotificationService


async def send_notification(
    notification_id: UUID,
    session: AsyncSession,
    service: NotificationService,
    sender: EmailSender,
) -> Notification:
    async with session.begin():
        notification, rendered = await service.prepare_send(notification_id)

    try:
        await sender.send(
            recipient=notification.recipient,
            subject=rendered.subject,
            body=rendered.body,
        )
    except (SMTPException, OSError):
        async with session.begin():
            await service.finish_send(notification_id, success=False)
        raise

    async with session.begin():
        notification = await service.finish_send(notification_id, success=True)

    return notification
