import aio_pika

RABBITMQ_URL = "amqp://guest:guest@localhost/"


async def setup_queue(channel, name="booking_events"):
    failed_name = f"{name}.failed"
    exchange_name = f"{name}.dlx"

    exchange = await channel.declare_exchange(
        exchange_name, aio_pika.ExchangeType.DIRECT, durable=True
    )
    failed_queue = await channel.declare_queue(failed_name, durable=True)
    await failed_queue.bind(exchange, routing_key=failed_name)

    queue = await channel.declare_queue(
        name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": exchange_name,
            "x-dead-letter-routing-key": failed_name,
        },
    )
    return queue
