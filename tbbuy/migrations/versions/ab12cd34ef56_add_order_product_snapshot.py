"""add order product snapshot

Revision ID: ab12cd34ef56
Revises: 9c4a6b2d1e10
Create Date: 2026-04-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'ab12cd34ef56'
down_revision = '9c4a6b2d1e10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order_product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_shop_id', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('product_title', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('product_cover', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('shop_name', sa.String(length=200), nullable=False, server_default=''))


def downgrade():
    with op.batch_alter_table('order_product', schema=None) as batch_op:
        batch_op.drop_column('shop_name')
        batch_op.drop_column('product_cover')
        batch_op.drop_column('product_title')
        batch_op.drop_column('product_shop_id')
