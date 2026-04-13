"""add category to product_extra

Revision ID: 1b7d7e5d7d2c
Revises: 88445d27b636
Create Date: 2026-04-12 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b7d7e5d7d2c'
down_revision = '88445d27b636'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product_extra', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=False, server_default=''))


def downgrade():
    with op.batch_alter_table('product_extra', schema=None) as batch_op:
        batch_op.drop_column('category')
