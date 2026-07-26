from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    template_code: Mapped[str] = mapped_column(
        String(length=50),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )

    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(length=120),
        nullable=True,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        index=True,
        default="pending",
        server_default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )