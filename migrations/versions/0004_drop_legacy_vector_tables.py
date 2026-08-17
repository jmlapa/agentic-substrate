"""Drop legacy vector store tables (node_embeddings and document_chunks)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_hnsw;")
    op.drop_index("idx_document_chunks_kb_doc", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("idx_node_embeddings_kb_id", table_name="node_embeddings")
    op.drop_table("node_embeddings")


def downgrade() -> None:
    op.create_table(
        "node_embeddings",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("node_type", sa.String(length=255), nullable=False),
        sa.Column("properties", JSONB(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("kb_id", "id", name="pk_node_embeddings"),
    )
    op.create_index("idx_node_embeddings_kb_id", "node_embeddings", ["kb_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("kb_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("parent_chunk_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("header_path", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "metadata",
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
        sa.PrimaryKeyConstraint("kb_id", "id", name="pk_document_chunks"),
    )
    op.create_index(
        "idx_document_chunks_kb_doc",
        "document_chunks",
        ["kb_id", "document_id"],
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
    )
