from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.exceptions.notifications import IdempotencyConflictError
from src.exceptions.templates import (
    TemplateAlreadyExistsError,
    TemplateNotFoundError,
    TemplateRenderError,
)


async def template_not_found_handler(request: Request, error: TemplateNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)},
    )


async def template_exists_handler(request: Request, error: TemplateAlreadyExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )


async def template_render_handler(request: Request, error: TemplateRenderError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(error)},
    )


async def idempotency_conflict_handler(request: Request, error: IdempotencyConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(TemplateNotFoundError, template_not_found_handler)
    app.add_exception_handler(TemplateAlreadyExistsError, template_exists_handler)
    app.add_exception_handler(TemplateRenderError, template_render_handler)
    app.add_exception_handler(IdempotencyConflictError, idempotency_conflict_handler)
