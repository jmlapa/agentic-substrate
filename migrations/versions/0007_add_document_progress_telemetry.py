"""Add document progress telemetry columns to attached_documents

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-18 08:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attached_documents",
        sa.Column("progress_step", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "attached_documents",
        sa.Column(
            "progress_current",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column(
            "progress_total",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column(
            "progress_percentage",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column("progress_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attached_documents", "progress_message")
    op.drop_column("attached_documents", "progress_percentage")
    op.drop_column("attached_documents", "progress_total")
    op.drop_column("attached_documents", "progress_current")
    op.drop_column("attached_documents", "progress_step")
