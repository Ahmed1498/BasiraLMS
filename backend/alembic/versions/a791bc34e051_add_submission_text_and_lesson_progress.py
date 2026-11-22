"""Add text-based assignment submissions and lesson progress.

Revision ID: a791bc34e051
Revises: c2a12f4720c6
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a791bc34e051"
down_revision: Union[str, Sequence[str], None] = "c2a12f4720c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    )
    op.alter_column("submissions", "file_url", existing_type=sa.String(), nullable=True)
    op.add_column("submissions", sa.Column("submission_text", sa.Text(), nullable=True))
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "lesson_id", name="uq_lesson_progress_student_lesson"),
    )
    op.create_unique_constraint(
        "uq_enrollment_student_course",
        "enrollments",
        ["student_id", "course_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_enrollment_student_course", "enrollments", type_="unique")
    op.drop_table("lesson_progress")
    op.drop_column("submissions", "submission_text")
    op.alter_column("submissions", "file_url", existing_type=sa.String(), nullable=False)
    op.alter_column("users", "is_active", existing_type=sa.Boolean(), nullable=True, server_default=None)
