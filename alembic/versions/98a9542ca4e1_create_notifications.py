"""create notifications

Revision ID: 98a9542ca4e1
Revises: 
Create Date: 2026-07-26 14:13:43.958639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '98a9542ca4e1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('template_code', sa.String(length=50), nullable=False),
    sa.Column('recipient', sa.String(length=255), nullable=False),
    sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('idempotency_key', sa.String(length=120), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    sa.UniqueConstraint('idempotency_key', name=op.f('uq_notifications_idempotency_key'))
    )
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_table('notifications')
