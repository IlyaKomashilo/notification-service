from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.schemas.templates import TemplateCreate, TemplateResponse, TemplateRenderResponse, TemplateRenderRequest
from src.api.dependencies import SessionDep
from src.exceptions.templates import TemplateAlreadyExistsError, TemplateNotFoundError, TemplateRenderError
from src.repositories.templates import TemplatesRepository
from src.services.template_service import TemplateService


router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post(
    "/{template_code}/render",
    response_model=TemplateRenderResponse,
)
async def render_notification_template(
        template_code: str,
        payload: TemplateRenderRequest,
        session: SessionDep,
) -> TemplateRenderResponse:
    repository = TemplatesRepository(session)
    service = TemplateService(repository)

    try:
        rendering = await service.render_template(template_code, payload.context)
    except TemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except TemplateRenderError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return rendering


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
        payload: TemplateCreate,
        session: SessionDep,
) -> TemplateResponse:
    repository = TemplatesRepository(session)
    service = TemplateService(repository)

    try:
        async with session.begin():
            created_template = await service.create_template(payload)
    except TemplateAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template already exists",
        ) from error

    return TemplateResponse.model_validate(created_template)


@router.get(
    "",
    response_model=list[TemplateResponse],
)
async def get_templates(
        session: SessionDep,
) -> list[TemplateResponse]:
    repository = TemplatesRepository(session)
    service = TemplateService(repository)

    templates = await service.get_templates()

    return [TemplateResponse.model_validate(template) for template in templates]


@router.get(
    "/{template_code}",
    response_model=TemplateResponse,
)
async def get_template(
        template_code: str,
        session: SessionDep,
) -> TemplateResponse:
    repository = TemplatesRepository(session)
    service = TemplateService(repository)

    try:
        template = await service.get_template(template_code)
    except TemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return TemplateResponse.model_validate(template)
