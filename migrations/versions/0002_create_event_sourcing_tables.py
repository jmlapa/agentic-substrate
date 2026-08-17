"""Create event sourcing tables (event_streams and domain_events)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_streams",
        sa.Column("aggregate_id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("aggregate_type", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )

    op.create_table(
        "domain_events",
        sa.Column("event_id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB(), nullable=False),
        sa.UniqueConstraint(
            "aggregate_id", "event_version", name="uq_domain_events_aggregate_version"
        ),
    )
    op.create_index(
        "idx_domain_events_aggregate_id",
        "domain_events",
        ["aggregate_id", "event_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_domain_events_aggregate_id", table_name="domain_events")
    op.drop_table("domain_events")
    op.drop_table("event_streams")
