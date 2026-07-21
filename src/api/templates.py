from fastapi import APIRouter, HTTPException, status
from jinja2 import UndefinedError

from src.schemas.templates import TemplateCreate, TemplateResponse, TemplateRenderResponse, TemplateRenderRequest
from src.services.template_renderer import render_template

router = APIRouter(prefix="/templates", tags=["Templates"])


templates_storage: dict[str, TemplateResponse] = {}


@router.post(
    "/{template_code}/render",
    response_model=TemplateRenderResponse
)
async def render_notification_template(
        template_code: str,
        payload: TemplateRenderRequest
) -> TemplateRenderResponse:

    template = templates_storage.get(template_code)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    try:
        rendered_subject = render_template(template_body=template.subject, context=payload.context)
        rendered_body = render_template(template_body=template.body, context=payload.context)
    except UndefinedError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template rendering error: {error}"
        ) from error

    return TemplateRenderResponse(
        subject=rendered_subject,
        body=rendered_body
    )


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(template: TemplateCreate) -> TemplateResponse:
    if template.code in templates_storage:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template with this code already exists",
        )

    new_template = TemplateResponse(
        code=template.code,
        subject=template.subject,
        body=template.body,
    )

    templates_storage[template.code] = new_template

    return new_template


@router.get("", response_model=list[TemplateResponse])
async def get_templates() -> list[TemplateResponse]:
    return list(templates_storage.values())


@router.get("/{template_code}", response_model=TemplateResponse)
async def get_template(template_code: str) -> TemplateResponse:
    template = templates_storage.get(template_code)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template