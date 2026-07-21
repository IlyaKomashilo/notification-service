from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from src.schemas.notifications import NotificationCreate, NotificationRecord, NotificationResponse


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

notifications_storage: dict[UUID, NotificationRecord] = {}


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

    notification = NotificationRecord(
        id=uuid4(),
        **payload.model_dump(),
    )

    notifications_storage[notification.id] = notification

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