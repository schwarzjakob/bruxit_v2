"""Rename tables for clarity (e.g. ssd → sleep_stage_segment)

Revision ID: f19ff5675a63
Revises:
Create Date: 2025-05-23 08:06:59.416973

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f19ff5675a63"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("prediction", "event_prediction")
    op.rename_table("mvc", "maximum_voluntary_contraction")
    op.rename_table("threshold", "sensor_threshold")
    op.rename_table("ssd", "sleep_stage_segment")

    # Column rename: threshold → threshold_value
    op.alter_column("sensor_threshold", "threshold", new_column_name="threshold_value")


def downgrade():
    # Reverse column rename first
    op.alter_column("sensor_threshold", "threshold_value", new_column_name="threshold")

    op.rename_table("event_prediction", "prediction")
    op.rename_table("maximum_voluntary_contraction", "mvc")
    op.rename_table("sensor_threshold", "threshold")
    op.rename_table("sleep_stage_segment", "ssd")
