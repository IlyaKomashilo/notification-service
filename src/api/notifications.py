from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from src.schemas.notifications import NotificationCreate, NotificationRecord, NotificationResponse


notifications_storage: dict[UUID, NotificationRecord] = {}

notifications_by_idempotency_key: dict[str, UUID] = {}


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)
def to_notification_response(
        notification: NotificationRecord
) -> NotificationResponse:

    return NotificationResponse(
        id=notification.id,
        template_code=notification.template_code,
        recipient=notification.recipient,
        status=notification.status,
    )


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
        payload: NotificationCreate,
) -> NotificationResponse:
    if payload.idempotency_key is not None:
        existing_id = notifications_by_idempotency_key.get(payload.idempotency_key)

        if existing_id is not None:
            existing_notification = notifications_storage.get(existing_id)

            if existing_notification is not None:
                return to_notification_response(existing_notification)

    notification = NotificationRecord(
        id=uuid4(),
        **payload.model_dump(),
    )

    notifications_storage[notification.id] = notification
    if notification.idempotency_key is not None:
        notifications_by_idempotency_key[notification.idempotency_key] = notification.id

    return to_notification_response(notification)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
)
async def get_notification(
        notification_id: UUID,
) -> NotificationResponse:
    notification = notifications_storage.get(notification_id)

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found",
        )

    return to_notification_response(notification)