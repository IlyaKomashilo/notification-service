from fastapi import APIRouter
from src.schemas.health import HealthResponse


router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="notification-service",
    )