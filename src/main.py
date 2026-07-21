from fastapi import FastAPI
from src.api.health import router as health_router
from src.api.templates import router as template_router
from src.api.notifications import router as notification_router
app = FastAPI(
    title="Notification Service",
    version="0.1.0"
)

app.include_router(health_router)
app.include_router(template_router)
app.include_router(notification_router)



