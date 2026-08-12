from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import SessionDep
from src.exceptions.notifications import IdempotencyConflictError
from src.repositories.notifications import NotificationsRepository
from src.schemas.notifications import (
    NotificationCreate,
    NotificationResponse,
)
from src.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(payload: NotificationCreate, session: SessionDep) -> NotificationResponse:
    repository = NotificationsRepository(session)
    service = NotificationService(repository)

    try:
        async with session.begin():
            notification = await service.create_notification(payload)

    except IdempotencyConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from error

    return NotificationResponse.model_validate(notification)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: UUID, session: SessionDep) -> NotificationResponse:
    repository = NotificationsRepository(session)

    notification = await repository.get_by_id(notification_id)

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found",
        )

    return NotificationResponse.model_validate(notification)