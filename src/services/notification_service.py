from uuid import UUID

from src.exceptions.notifications import IdempotencyConflictError, NotificationNotFoundError, NotificationStatusError
from src.models.notification import Notification
from src.repositories.notifications import NotificationsRepository
from src.schemas.notifications import NotificationCreate
from src.schemas.templates import TemplateRenderResponse
from src.services.template_service import TemplateService


class NotificationService:
    def __init__(self, repository: NotificationsRepository, template_service: TemplateService) -> None:
        self.repository = repository
        self.template_service = template_service

    async def create_notification(self, payload: NotificationCreate) -> Notification:
        if payload.idempotency_key is not None:
            existing = await self.repository.get_by_idempotency_key(payload.idempotency_key)

            if existing is not None:
                if self._is_same_request(existing, payload):
                    return existing
                raise IdempotencyConflictError("Idempotency key is already used")

        await self.template_service.get_template(payload.template_code)

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

    async def prepare_send(self, notification_id: UUID) -> tuple[Notification, TemplateRenderResponse]:
        notification = await self.repository.get_for_update(notification_id)

        if notification is None:
            raise NotificationNotFoundError("Notification not found")
        if notification.status != "pending":
            raise NotificationStatusError("Notification is not pending")

        rendered = await self.template_service.render_template(notification.template_code, notification.context)
        await self.repository.update_status(notification, "processing")

        return notification, rendered

    async def finish_send(self, notification_id: UUID, success: bool) -> Notification:
        notification = await self.repository.get_for_update(notification_id)

        if notification is None:
            raise NotificationNotFoundError("Notification not found")
        if notification.status != "processing":
            raise NotificationStatusError("Notification is not processing")
        if success:
            await self.repository.update_status(notification, "sent")
        else:
            await self.repository.update_status(notification, "failed")

        return notification