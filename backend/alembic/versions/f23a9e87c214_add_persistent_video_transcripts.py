"""Add persistent video transcripts and searchable transcript chunks.

Revision ID: f23a9e87c214
Revises: d8b4d3f2a610
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR


revision: str = "f23a9e87c214"
down_revision: Union[str, Sequence[str], None] = "d8b4d3f2a610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_transcripts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.String(length=32), nullable=False),
        sa.Column("video_url", sa.String(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_transcripts_video_id", "video_transcripts", ["video_id"], unique=True)
    op.create_table(
        "video_transcript_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transcript_id", sa.UUID(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", VECTOR(1536), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["video_transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("video_transcript_chunks")
    op.drop_index("ix_video_transcripts_video_id", table_name="video_transcripts")
    op.drop_table("video_transcripts")
