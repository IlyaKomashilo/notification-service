import asyncio

import aio_pika
from pydantic import ValidationError

from src.db.database import async_session_factory
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.schemas.events import BookingConfirmedEvent
from src.schemas.notifications import NotificationCreate
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService


async def main():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("hello", durable=True)

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

                async with async_session_factory() as session:
                    async with session.begin():
                        template_repository = TemplatesRepository(session)
                        notification_repository = NotificationsRepository(session)
                        template_service = TemplateService(template_repository)
                        notification_service = NotificationService(
                            notification_repository, template_service
                        )

                        await notification_service.create_notification(payload)

                await message.ack()


if __name__ == "__main__":
    asyncio.run(main())
