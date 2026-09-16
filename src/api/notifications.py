from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import SessionDep
from src.exceptions.notifications import IdempotencyConflictError
from src.exceptions.templates import TemplateNotFoundError
from src.repositories.notifications import NotificationsRepository
from src.repositories.templates import TemplatesRepository
from src.schemas.notifications import (
    NotificationCreate,
    NotificationResponse,
)
from src.services.notification_service import NotificationService
from src.services.template_service import TemplateService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(payload: NotificationCreate, session: SessionDep) -> NotificationResponse:
    template_repository = TemplatesRepository(session)
    template_service = TemplateService(template_repository)
    repository = NotificationsRepository(session)
    service = NotificationService(repository, template_service)

    try:
        try:
            async with session.begin():
                notification = await service.create_notification(payload)
        except IntegrityError as error:
            db_error = error.orig.__cause__
            constraint_name = getattr(db_error, "constraint_name", None)

            if constraint_name == "uq_notifications_idempotency_key":
                if payload.idempotency_key is None:
                    raise
                notification = await service.get_existing_idempotent_notification(payload)
            elif constraint_name == "fk_notifications_template_code_templates":
                raise TemplateNotFoundError("Template not found") from error
            else:
                raise

    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except TemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

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
