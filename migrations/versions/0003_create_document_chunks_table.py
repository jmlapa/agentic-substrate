"""Create document chunks table with HNSW vector index

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-16 00:02:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("breadcrumb", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_document_chunks_kb_doc",
        "document_chunks",
        ["knowledge_base_id", "document_id"],
    )
    op.create_index(
        "idx_document_chunks_parent_id",
        "document_chunks",
        ["parent_id"],
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding;")
    op.drop_index("idx_document_chunks_parent_id", table_name="document_chunks")
    op.drop_index("idx_document_chunks_kb_doc", table_name="document_chunks")
    op.drop_table("document_chunks")
