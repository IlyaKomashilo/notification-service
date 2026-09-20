from fastapi import APIRouter, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import SessionDep, TemplateServiceDep
from src.exceptions.templates import TemplateAlreadyExistsError
from src.schemas.templates import (
    TemplateCreate,
    TemplateRenderRequest,
    TemplateRenderResponse,
    TemplateResponse,
)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post(
    "/{template_code}/render",
    response_model=TemplateRenderResponse,
)
async def render_notification_template(
    template_code: str,
    payload: TemplateRenderRequest,
    service: TemplateServiceDep,
) -> TemplateRenderResponse:
    return await service.render_template(template_code, payload.context)


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: TemplateCreate,
    session: SessionDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    try:
        async with session.begin():
            created_template = await service.create_template(payload)
    except IntegrityError as error:
        db_error = error.orig.__cause__
        if getattr(db_error, "constraint_name", None) == "pk_templates":
            raise TemplateAlreadyExistsError("Template already exists") from error
        raise

    return TemplateResponse.model_validate(created_template)


@router.get(
    "",
    response_model=list[TemplateResponse],
)
async def get_templates(
    service: TemplateServiceDep,
) -> list[TemplateResponse]:
    templates = await service.get_templates()

    return [TemplateResponse.model_validate(template) for template in templates]


@router.get(
    "/{template_code}",
    response_model=TemplateResponse,
)
async def get_template(
    template_code: str,
    service: TemplateServiceDep,
) -> TemplateResponse:
    template = await service.get_template(template_code)
    return TemplateResponse.model_validate(template)
