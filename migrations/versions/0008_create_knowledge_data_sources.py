"""Create knowledge_data_sources and knowledge_data_source_runs tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-21 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Tabela knowledge_data_sources
    op.create_table(
        "knowledge_data_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "kb_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("data_source_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="IDLE",
        ),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column(
            "sync_interval_minutes",
            sa.Integer(),
            nullable=False,
            server_default="15",
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "config",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_knowledge_data_sources_kb_id",
        "knowledge_data_sources",
        ["kb_id"],
    )
    op.create_index(
        "idx_knowledge_data_sources_status",
        "knowledge_data_sources",
        ["status"],
    )

    # 2. Tabela knowledge_data_source_runs
    op.create_table(
        "knowledge_data_source_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "data_source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_data_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kb_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="EXTRACTING",
        ),
        sa.Column(
            "total_files_discovered",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "indexed_files_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failed_files_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failure_summary",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_knowledge_data_source_runs_ds_id",
        "knowledge_data_source_runs",
        ["data_source_id"],
    )
    op.create_index(
        "idx_knowledge_data_source_runs_status",
        "knowledge_data_source_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("knowledge_data_source_runs")
    op.drop_table("knowledge_data_sources")
