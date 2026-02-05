"""add ai task state machine fields

Revision ID: add_ai_task_state_machine
Revises: add_billing_tables
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_ai_task_state_machine"
down_revision = "add_billing_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ai_tasks",
        sa.Column("retry_count", sa.Integer(), server_default="0")
    )
    op.add_column(
        "ai_tasks",
        sa.Column(
            "depends_on",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb")
        )
    )
    op.alter_column(
        "ai_tasks",
        "status",
        existing_type=sa.String(length=50),
        server_default="queued"
    )

    op.execute("UPDATE ai_tasks SET retry_count = 0 WHERE retry_count IS NULL")
    op.execute("UPDATE ai_tasks SET depends_on = '[]'::jsonb WHERE depends_on IS NULL")


def downgrade():
    op.alter_column(
        "ai_tasks",
        "status",
        existing_type=sa.String(length=50),
        server_default="pending"
    )
    op.drop_column("ai_tasks", "depends_on")
    op.drop_column("ai_tasks", "retry_count")
