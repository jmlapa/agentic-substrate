"""Add recovery_attempt to attached_documents

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-23 12:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attached_documents",
        sa.Column(
            "recovery_attempt",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("attached_documents", "recovery_attempt")
