"""Add missing sphere_descriptions_json to natal_charts

Revision ID: fix_add_sphere_descriptions_json
Revises: e46b961fd4ac
Create Date: 2026-03-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'fix_add_sphere_desc'
down_revision: Union[str, None] = 'e46b961fd4ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sphere_descriptions_json column if not exists
    op.execute("""
        ALTER TABLE natal_charts 
        ADD COLUMN IF NOT EXISTS sphere_descriptions_json JSONB
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE natal_charts 
        DROP COLUMN IF EXISTS sphere_descriptions_json
    """)
