from fastapi import FastAPI
from src.api.exception_handlers import register_exception_handlers
from src.api.health import router as health_router
from src.api.templates import router as template_router
from src.api.notifications import router as notification_router
app = FastAPI(
    title="Notification Service",
    version="0.1.0"
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(template_router)
app.include_router(notification_router)

# uvicorn src.main:app --reload --port 9000
