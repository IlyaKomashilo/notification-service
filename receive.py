import pika
from pydantic import ValidationError

from src.schemas.events import BookingConfirmedEvent

connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

channel.queue_declare(queue="hello", durable=True)


def handle_message(channel, method, properties, body):
    try:
        event = BookingConfirmedEvent.model_validate_json(body)
    except ValidationError:
        channel.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        print("Сообщение отклонено: неправильные данные")
        return

    print("Событие:", event.event_type)
    print("Получатель:", event.recipient)
    print("Получили:", body.decode())
    channel.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(
    queue="hello",
    on_message_callback=handle_message,
    auto_ack=False,
)

print("Ждём сообщения")
channel.start_consuming()
