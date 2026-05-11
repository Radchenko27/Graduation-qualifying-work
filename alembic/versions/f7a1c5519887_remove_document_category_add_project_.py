"""remove_document_category_add_project_created_at

Revision ID: f7a1c5519887
Revises: 3fc7ce211477
Create Date: 2026-05-11 14:21:25.875222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a1c5519887'
down_revision: Union[str, Sequence[str], None] = '3fc7ce211477'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
