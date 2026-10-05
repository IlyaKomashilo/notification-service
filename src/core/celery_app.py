from celery import Celery

from src.core.rabbitmq import RABBITMQ_URL

app = Celery(
    "notifications",
    broker=RABBITMQ_URL,
    include=["src.tasks.notifications"],
)

app.conf.update(
    control_queue_exclusive=True,
    event_queue_exclusive=True,
)
