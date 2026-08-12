from src.exceptions.notifications import IdempotencyConflictError
from src.repositories.notifications import NotificationsRepository
from src.schemas.notifications import NotificationCreate


class NotificationService:
    def __init__(self, repository: NotificationsRepository):
        self.repository = repository

    async def create_notification(self,payload: NotificationCreate):
        if payload.idempotency_key is not None:
            existing = await self.repository.get_by_idempotency_key(payload.idempotency_key)

            if existing is not None:
                same_request = (
                        existing.recipient == payload.recipient
                        and existing.template_code == payload.template_code
                        and existing.context == payload.context
                )

                if same_request:
                    return existing

                raise IdempotencyConflictError("Idempotency key is already used")

            return await self.repository.add(payload)




