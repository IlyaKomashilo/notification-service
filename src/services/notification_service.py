from src.exceptions.notifications import IdempotencyConflictError
from src.models.notification import Notification
from src.repositories.notifications import NotificationsRepository
from src.schemas.notifications import NotificationCreate


class NotificationService:
    def __init__(self, repository: NotificationsRepository):
        self.repository = repository

    async def create_notification(self, payload: NotificationCreate) -> Notification:
        if payload.idempotency_key is not None:
            existing = await self.repository.get_by_idempotency_key(payload.idempotency_key)

            if existing is not None:
                if self._is_same_request(existing, payload):
                    return existing

                raise IdempotencyConflictError("Idempotency key is already used")

        return await self.repository.add(payload)

    async def get_existing_idempotent_notification(self, payload: NotificationCreate) -> Notification:
        if payload.idempotency_key is None:
            raise RuntimeError("Cannot resolve idempotency race without idempotency key")

        existing = await self.repository.get_by_idempotency_key(payload.idempotency_key)

        if existing is None:
            raise RuntimeError("Idempotency race happened, but existing notification was not found")

        if self._is_same_request(existing, payload):
            return existing

        raise IdempotencyConflictError("Idempotency key is already used")

    @staticmethod
    def _is_same_request(notification: Notification, payload: NotificationCreate) -> bool:
        return (
            notification.recipient == payload.recipient
            and notification.template_code == payload.template_code
            and notification.context == payload.context
        )
