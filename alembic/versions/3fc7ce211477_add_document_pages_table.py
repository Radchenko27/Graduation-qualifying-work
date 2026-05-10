"""add_document_pages_table

Revision ID: 3fc7ce211477
Revises: 2f9e6573f385
Create Date: 2026-05-09 23:37:44.019551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fc7ce211477'
down_revision: Union[str, Sequence[str], None] = '2f9e6573f385'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать таблицу document_pages"""
    op.create_table(
        'document_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('content_type', sa.String(length=50), nullable=True),
        sa.Column('page_metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_pages_id'), 'document_pages', ['id'], unique=False)
    op.create_index('ix_document_pages_document_id', 'document_pages', ['document_id'])
    op.create_index('ix_document_pages_page_number', 'document_pages', ['page_number'])


def downgrade() -> None:
    """Удалить таблицу document_pages"""
    op.drop_index('ix_document_pages_page_number', table_name='document_pages')
    op.drop_index('ix_document_pages_document_id', table_name='document_pages')
    op.drop_index(op.f('ix_document_pages_id'), table_name='document_pages')
    op.drop_table('document_pages')

