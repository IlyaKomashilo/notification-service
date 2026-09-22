import json

import pika

event = {
    "event_id": "test-booking-001",
    "event_type": "booking.confirmed",
    "recipient": "ilya@example.com",
    "context": {
        "username": "Ilya",
        "booking_id": 123,
    },
}

connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))

channel = connection.channel()

print("Подключение работает")

channel.queue_declare(queue="hello", durable=True)

channel.basic_publish(
    exchange="",
    routing_key="hello",
    body=json.dumps(event),
)

print("Сообщение отправлено")

connection.close()
