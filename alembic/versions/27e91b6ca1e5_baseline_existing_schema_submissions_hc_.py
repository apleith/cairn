"""baseline existing schema (submissions + hc_* tables)

Revision ID: 27e91b6ca1e5
Revises:
Create Date: 2026-05-22

No-op upgrade. This revision marks the database schema state at the time
Alembic was adopted. The existing tables (submissions + 17 hc_* tables)
were created by src/storage.py via CREATE TABLE IF NOT EXISTS at app
startup; they remain managed that way for backward compatibility, and
Alembic will not own them until a future revision explicitly takes them.

To adopt a fresh database into this baseline, stamp it:
    alembic stamp 27e91b6ca1e5
"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision: str = '27e91b6ca1e5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
