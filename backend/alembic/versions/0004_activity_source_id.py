"""add activity source_id latitude longitude estimated_attendees

Revision ID: 0004_activity_source_id
Revises: 0003_reports_and_push
Create Date: 2026-04-09 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_activity_source_id"
down_revision = "0003_reports_and_push"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns one by one to avoid SQLite batch circular dependency
    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.String(length=255), nullable=True))

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.add_column(sa.Column("latitude", sa.String(length=32), nullable=True))

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.add_column(sa.Column("longitude", sa.String(length=32), nullable=True))

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.add_column(sa.Column("estimated_attendees", sa.Integer(), nullable=True))

    # Add unique constraint separately
    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.create_unique_constraint("uq_source_source_id", ["source", "source_id"])


def downgrade() -> None:
    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.drop_constraint("uq_source_source_id", type_="unique")
        batch_op.drop_column("estimated_attendees")

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.drop_column("longitude")

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.drop_column("latitude")

    with op.batch_alter_table("surrounding_activities") as batch_op:
        batch_op.drop_column("source_id")
