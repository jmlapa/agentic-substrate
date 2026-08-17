"""Create event sourcing tables (events and snapshots)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stream_id", sa.String(length=255), nullable=False),
        sa.Column("stream_type", sa.String(length=255), nullable=False),
        sa.Column("stream_position", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("event_data", JSONB(), nullable=False),
        sa.Column("event_metadata", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("stream_id", "stream_position", name="uq_events_stream_position"),
    )
    op.create_index("ix_events_stream_id", "events", ["stream_id"])
    op.create_index("ix_events_stream_type_event_type", "events", ["stream_type", "event_type"])

    op.create_table(
        "snapshots",
        sa.Column("stream_id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("stream_type", sa.String(length=255), nullable=False),
        sa.Column("stream_position", sa.Integer(), nullable=False),
        sa.Column("state", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("snapshots")
    op.drop_index("ix_events_stream_type_event_type", table_name="events")
    op.drop_index("ix_events_stream_id", table_name="events")
    op.drop_table("events")
