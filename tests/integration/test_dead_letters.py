import asyncio
import os
from uuid import uuid4

import aio_pika
import pytest
import pytest_asyncio

from src.core.rabbitmq import setup_queue


@pytest_asyncio.fixture
async def queues():
    url = os.getenv("TEST_RABBITMQ_URL")
    if not url:
        pytest.skip("TEST_RABBITMQ_URL is not configured")

    connection = await aio_pika.connect_robust(url)
    async with connection:
        channel = await connection.channel()
        name = f"test_{uuid4().hex}"
        try:
            queue = await setup_queue(channel, name)
            failed_queue = await channel.get_queue(f"{name}.failed")
            yield channel, queue, failed_queue
        finally:
            await channel.queue_delete(name)
            await channel.queue_delete(f"{name}.failed")
            await channel.exchange_delete(f"{name}.dlx")


async def test_rejected_message_goes_to_failed_queue(queues):
    channel, queue, failed_queue = queues
    await channel.default_exchange.publish(
        aio_pika.Message(body=b"invalid event"), routing_key=queue.name
    )

    message = await queue.get(timeout=5)
    await message.reject(requeue=False)

    async with asyncio.timeout(5):
        async with failed_queue.iterator() as messages:
            async for failed in messages:
                assert failed.body == b"invalid event"
                assert failed.headers["x-death"][0]["reason"] == "rejected"
                await failed.ack()
                break


async def test_confirmed_message_does_not_go_to_failed_queue(queues):
    channel, queue, failed_queue = queues
    await channel.default_exchange.publish(
        aio_pika.Message(body=b"valid event"), routing_key=queue.name
    )

    message = await queue.get(timeout=5)
    await message.ack()

    assert await queue.get(fail=False, timeout=5) is None
    assert await failed_queue.get(fail=False, timeout=5) is None
