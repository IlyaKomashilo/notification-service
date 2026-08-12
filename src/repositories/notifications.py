from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import Notification
from src.schemas.notifications import NotificationCreate


class NotificationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add (self, payload: NotificationCreate) -> Notification:
        notification = Notification(**payload.model_dump())
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        return await self.session.get(Notification, notification_id)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Notification | None:
        stmt = select(Notification).where(Notification.idempotency_key == idempotency_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()