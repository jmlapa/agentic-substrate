"""Expand attached_documents relational read model with OCR, chunk and graph stats

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-17 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attached_documents",
        sa.Column(
            "enable_ocr",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column("ocr_instructions", sa.Text(), nullable=True),
    )
    op.add_column(
        "attached_documents",
        sa.Column("total_parents", sa.Integer(), nullable=True),
    )
    op.add_column(
        "attached_documents",
        sa.Column("total_children", sa.Integer(), nullable=True),
    )
    op.add_column(
        "attached_documents",
        sa.Column(
            "indexed_nodes_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column(
            "indexed_edges_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "attached_documents",
        sa.Column("error_step", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "attached_documents",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attached_documents", "error_message")
    op.drop_column("attached_documents", "error_step")
    op.drop_column("attached_documents", "indexed_edges_count")
    op.drop_column("attached_documents", "indexed_nodes_count")
    op.drop_column("attached_documents", "total_children")
    op.drop_column("attached_documents", "total_parents")
    op.drop_column("attached_documents", "ocr_instructions")
    op.drop_column("attached_documents", "enable_ocr")
