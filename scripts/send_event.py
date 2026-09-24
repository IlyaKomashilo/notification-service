import asyncio
import json

import aio_pika

from src.core.rabbitmq import RABBITMQ_URL, setup_queue

event = {
    "event_id": "test-booking-003",
    "event_type": "booking.confirmed",
    "recipient": "ilya@example.com",
    "context": {
        "username": "Ilya",
        "booking_id": 123,
    },
}


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        queue = await setup_queue(channel)
        message = aio_pika.Message(
            body=json.dumps(event).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(message, routing_key=queue.name)
        print("Сообщение отправлено")


if __name__ == "__main__":
    asyncio.run(main())
