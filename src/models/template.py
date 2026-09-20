from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Template(Base):
    __tablename__ = "templates"

    code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    subject: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        String(5000),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
