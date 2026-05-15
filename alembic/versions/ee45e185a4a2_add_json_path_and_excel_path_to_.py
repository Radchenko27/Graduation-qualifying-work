"""Add json_path and excel_path to documents

Revision ID: ee45e185a4a2
Revises: f7a1c5519887
Create Date: 2026-05-15 15:37:53.377676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee45e185a4a2'
down_revision: Union[str, Sequence[str], None] = 'f7a1c5519887'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('documents', sa.Column('json_path', sa.String(length=1024), nullable=True))
    op.add_column('documents', sa.Column('excel_path', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'excel_path')
    op.drop_column('documents', 'json_path')
