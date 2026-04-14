"""add search keywords to product_extra

Revision ID: c3d9a7b5e201
Revises: 7a4f2a98d421
Create Date: 2026-04-14 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d9a7b5e201'
down_revision = '7a4f2a98d421'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product_extra', schema=None) as batch_op:
        batch_op.add_column(sa.Column('search_keywords', sa.String(length=1000), nullable=False, server_default=''))


def downgrade():
    with op.batch_alter_table('product_extra', schema=None) as batch_op:
        batch_op.drop_column('search_keywords')
