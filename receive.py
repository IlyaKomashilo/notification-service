import asyncio

import aio_pika
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.core.rabbitmq import RABBITMQ_URL, setup_queue
from src.db.database import async_session_factory
from src.exceptions.notifications import IdempotencyConflictError
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.schemas.events import BookingConfirmedEvent
from src.schemas.notifications import NotificationCreate
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


async def save_notification(payload: NotificationCreate) -> None:
    async with async_session_factory() as session:
        template_repository = TemplatesRepository(session)
        notification_repository = NotificationsRepository(session)
        template_service = TemplateService(template_repository)
        notification_service = NotificationService(
            notification_repository, template_service
        )

        try:
            async with session.begin():
                await notification_service.create_notification(payload)
        except IntegrityError as error:
            db_error = error.orig.__cause__
            constraint_name = getattr(db_error, "constraint_name", None)
            if constraint_name != "uq_notifications_idempotency_key":
                raise

            async with session.begin():
                await notification_service.get_existing_idempotent_notification(payload)


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        queue = await setup_queue(channel)

        print("Подключились к очереди:", queue.name)

        async with queue.iterator() as messages:
            async for message in messages:
                try:
                    event = BookingConfirmedEvent.model_validate_json(message.body)
                    payload = NotificationCreate(
                        template_code="booking_confirmed",
                        recipient=event.recipient,
                        context=event.context,
                        idempotency_key=event.event_id,
                    )
                except ValidationError:
                    print("Сообщение отклонено: неправильные данные")
                    await message.reject(requeue=False)
                    continue

                try:
                    await save_notification(payload)
                except IdempotencyConflictError:
                    print("Сообщение отклонено: тот же event_id, но другие данные")
                    await message.reject(requeue=False)
                    continue

                await message.ack()


if __name__ == "__main__":
    asyncio.run(main())
