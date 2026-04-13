"""make product price decimal

Revision ID: 7a4f2a98d421
Revises: 1b7d7e5d7d2c
Create Date: 2026-04-13 01:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '7a4f2a98d421'
down_revision = '1b7d7e5d7d2c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.Integer(), type_=sa.Numeric(10, 2), existing_nullable=False)


def downgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False)
