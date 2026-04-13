"""add product_id to review

Revision ID: 9c4a6b2d1e10
Revises: 6e2c4f91b902
Create Date: 2026-04-13 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c4a6b2d1e10'
down_revision = '6e2c4f91b902'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_id', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('idx_product_id', ['product_id'], unique=False)


def downgrade():
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.drop_index('idx_product_id')
        batch_op.drop_column('product_id')
