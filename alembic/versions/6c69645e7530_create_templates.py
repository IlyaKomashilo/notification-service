"""create templates

Revision ID: 6c69645e7530
Revises: 98a9542ca4e1
Create Date: 2026-08-31 20:05:08.518292

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6c69645e7530"
down_revision: Union[str, Sequence[str], None] = "98a9542ca4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("body", sa.String(length=5000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_templates")),
    )


def downgrade() -> None:
    op.drop_table("templates")
