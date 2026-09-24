"""Create partial index on attached_documents for zombie recovery

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-23 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_attached_documents_zombie_recovery",
        "attached_documents",
        ["status", "updated_at"],
        postgresql_where=sa.text("status IN ('UPLOADED', 'PARSED', 'CHUNKED')"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_attached_documents_zombie_recovery",
        table_name="attached_documents",
    )
