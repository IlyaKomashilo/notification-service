"""add template foreign key

Revision ID: e4f6f51795e8
Revises: 6c69645e7530
Create Date: 2026-09-16 18:39:10.555143

"""

from typing import Sequence, Union

from alembic import op

revision: str = "e4f6f51795e8"
down_revision: Union[str, Sequence[str], None] = "6c69645e7530"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        op.f("fk_notifications_template_code_templates"),
        "notifications",
        "templates",
        ["template_code"],
        ["code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_notifications_template_code_templates"),
        "notifications",
        type_="foreignkey",
    )
