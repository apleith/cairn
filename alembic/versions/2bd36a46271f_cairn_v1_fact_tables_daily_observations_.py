"""cairn v1 fact tables

Adds the five canonical fact tables from the Cairn data architecture
brief (daily_observations, body_measurements, medication_events,
clinical_events, model_outputs). Additive only; does not touch the
existing submissions or hc_* tables. A separate migration script
(scripts/migrate_v0_to_v1.py, planned next) backfills daily_observations
from the existing submissions table.

Revision ID: 2bd36a46271f
Revises: 27e91b6ca1e5
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2bd36a46271f'
down_revision: Union[str, Sequence[str], None] = '27e91b6ca1e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'daily_observations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('time', sa.Time),
        sa.Column('weight_lb', sa.Float),
        sa.Column('weight_observed', sa.Boolean),
        sa.Column('weight_source', sa.Text),
        sa.Column('weight_context', sa.Text),
        sa.Column('weight_confidence', sa.Text),
        sa.Column('systolic', sa.Integer),
        sa.Column('diastolic', sa.Integer),
        sa.Column('pulse_from_bp_device', sa.Integer),
        sa.Column('bp_posture', sa.Text),
        sa.Column('resting_hr', sa.Integer),
        sa.Column('average_hr', sa.Integer),
        sa.Column('max_hr', sa.Integer),
        sa.Column('steps', sa.Integer),
        sa.Column('steps_observed', sa.Boolean),
        sa.Column('device_worn', sa.Boolean),
        sa.Column('active_minutes', sa.Integer),
        sa.Column('distance_miles', sa.Float),
        sa.Column('exercise_minutes', sa.Integer),
        sa.Column('resistance_training', sa.Boolean),
        sa.Column('protein_g', sa.Float),
        sa.Column('protein_logged', sa.Boolean),
        sa.Column('calories', sa.Float),
        sa.Column('carbs_g', sa.Float),
        sa.Column('fat_g', sa.Float),
        sa.Column('fluids_oz', sa.Float),
        sa.Column('sleep_hours', sa.Float),
        sa.Column('source', sa.Text, nullable=False),
        sa.Column(
            'import_timestamp',
            sa.DateTime,
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.Column('source_file', sa.Text),
        sa.Column('source_record_id', sa.Text),
        sa.Column('timezone', sa.Text),
        sa.Column('notes', sa.Text),
    )
    op.create_index('idx_daily_observations_date', 'daily_observations', ['date'])
    op.create_index('idx_daily_observations_source', 'daily_observations', ['source'])

    op.create_table(
        'body_measurements',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('waist_in', sa.Float),
        sa.Column('hips_in', sa.Float),
        sa.Column('neck_in', sa.Float),
        sa.Column('upper_arm_in', sa.Float),
        sa.Column('thigh_in', sa.Float),
        sa.Column('measurement_time', sa.Text),
        sa.Column('measurement_method', sa.Text),
        sa.Column('source', sa.Text, nullable=False),
        sa.Column(
            'import_timestamp',
            sa.DateTime,
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.Column('notes', sa.Text),
    )
    op.create_index('idx_body_measurements_date', 'body_measurements', ['date'])

    op.create_table(
        'medication_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('medication_name', sa.Text, nullable=False),
        sa.Column('generic_name', sa.Text),
        sa.Column('dose', sa.Text),
        sa.Column('dose_numeric', sa.Float),
        sa.Column('dose_unit', sa.Text),
        sa.Column('route', sa.Text),
        sa.Column('frequency', sa.Text),
        sa.Column('event_type', sa.Text, nullable=False),
        sa.Column('reason', sa.Text),
        sa.Column('prescribing_context', sa.Text),
        sa.Column('source', sa.Text, nullable=False),
        sa.Column(
            'import_timestamp',
            sa.DateTime,
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.Column('notes', sa.Text),
    )
    op.create_index('idx_medication_events_date', 'medication_events', ['date'])
    op.create_index('idx_medication_events_name', 'medication_events', ['medication_name'])

    op.create_table(
        'clinical_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('event_id', sa.Text, unique=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('event_type', sa.Text, nullable=False),
        sa.Column('category', sa.Text, nullable=False),
        sa.Column('label', sa.Text, nullable=False),
        sa.Column('certainty', sa.Text),
        sa.Column('source', sa.Text, nullable=False),
        sa.Column('ahi', sa.Float),
        sa.Column('cpap_pressure', sa.Text),
        sa.Column('cpap_hours', sa.Float),
        sa.Column('mask_type', sa.Text),
        sa.Column('notes', sa.Text),
    )
    op.create_index('idx_clinical_events_date', 'clinical_events', ['date'])
    op.create_index('idx_clinical_events_category', 'clinical_events', ['category'])

    op.create_table(
        'model_outputs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False, unique=True),
        sa.Column('day', sa.Integer, nullable=False),
        sa.Column('trend_weight_lb', sa.Float),
        sa.Column('trend_method', sa.Text),
        sa.Column('expected_weight_lb', sa.Float),
        sa.Column('lower_plausible_weight_lb', sa.Float),
        sa.Column('upper_plausible_weight_lb', sa.Float),
        sa.Column('pct_twl', sa.Float),
        sa.Column('pct_ewl', sa.Float),
        sa.Column('bmi', sa.Float),
        sa.Column('phase', sa.Text),
        sa.Column('segment_id', sa.Text),
        sa.Column('model_version', sa.Text, nullable=False),
        sa.Column(
            'generated_at',
            sa.DateTime,
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.Column('markers', sa.Text),
    )
    op.create_index('idx_model_outputs_date', 'model_outputs', ['date'])


def downgrade() -> None:
    op.drop_index('idx_model_outputs_date', table_name='model_outputs')
    op.drop_table('model_outputs')
    op.drop_index('idx_clinical_events_category', table_name='clinical_events')
    op.drop_index('idx_clinical_events_date', table_name='clinical_events')
    op.drop_table('clinical_events')
    op.drop_index('idx_medication_events_name', table_name='medication_events')
    op.drop_index('idx_medication_events_date', table_name='medication_events')
    op.drop_table('medication_events')
    op.drop_index('idx_body_measurements_date', table_name='body_measurements')
    op.drop_table('body_measurements')
    op.drop_index('idx_daily_observations_source', table_name='daily_observations')
    op.drop_index('idx_daily_observations_date', table_name='daily_observations')
    op.drop_table('daily_observations')
