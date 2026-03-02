"""add hawkins_min to card_progress

Revision ID: b2c3d4e5f6a7
Revises: 9a56354595a2
Create Date: 2026-02-28 02:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '9a56354595a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('card_progress', sa.Column('hawkins_min', sa.Integer(), nullable=True))
    # Fill existing rows with 1000
    op.execute("UPDATE card_progress SET hawkins_min = 1000 WHERE hawkins_min IS NULL")
    op.alter_column('card_progress', 'hawkins_min', nullable=False, server_default='1000')


def downgrade() -> None:
    op.drop_column('card_progress', 'hawkins_min')
