"""Add features from TZ 3.1

Revision ID: 002_tz_features
Revises: 001_initial
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_tz_features'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add owner_id to projects (владелец проекта)
    op.add_column('projects', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_projects_owner_id', 'projects', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    
    # 2. Add category and page_count to documents (классификация документации)
    op.add_column('documents', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    
    # 3. Create drawing_calculations table (расчеты элементов чертежей)
    op.create_table(
        'drawing_calculations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('drawing_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('element_name', sa.String(length=255), nullable=True),
        sa.Column('element_type', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('calculation_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['drawing_id'], ['drawings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_drawing_calculations_id'), 'drawing_calculations', ['id'], unique=False)
    
    # 4. Create estimates table (объединенные сметы)
    op.create_table(
        'estimates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('total_quantity', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_estimates_id'), 'estimates', ['id'], unique=False)
    
    # 5. Create estimate_items table (элементы сметы)
    op.create_table(
        'estimate_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('estimate_id', sa.Integer(), nullable=True),
        sa.Column('drawing_calculation_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['estimate_id'], ['estimates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['drawing_calculation_id'], ['drawing_calculations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_estimate_items_id'), 'estimate_items', ['id'], unique=False)

    # 6. Create document_pages table (классификация страниц документов)
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
    # Drop document_pages
    op.drop_index('ix_document_pages_page_number', table_name='document_pages')
    op.drop_index('ix_document_pages_document_id', table_name='document_pages')
    op.drop_index(op.f('ix_document_pages_id'), table_name='document_pages')
    op.drop_table('document_pages')
    
    # Drop estimate_items
    op.drop_index(op.f('ix_estimate_items_id'), table_name='estimate_items')
    op.drop_table('estimate_items')
    
    # Drop estimates
    op.drop_index(op.f('ix_estimates_id'), table_name='estimates')
    op.drop_table('estimates')
    
    # Drop drawing_calculations
    op.drop_index(op.f('ix_drawing_calculations_id'), table_name='drawing_calculations')
    op.drop_table('drawing_calculations')
    
    # Drop columns from documents
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'category')
    
    # Drop column from projects
    op.drop_constraint('fk_projects_owner_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'owner_id')
