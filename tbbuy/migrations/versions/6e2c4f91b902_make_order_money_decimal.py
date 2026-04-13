"""make order money decimal

Revision ID: 6e2c4f91b902
Revises: 5c8f8dfd9a11
Create Date: 2026-04-13 01:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '6e2c4f91b902'
down_revision = '5c8f8dfd9a11'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.alter_column('pay_amount', existing_type=sa.Integer(), type_=sa.Numeric(10, 2), existing_nullable=False)
    with op.batch_alter_table('order_product', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.Integer(), type_=sa.Numeric(10, 2), existing_nullable=False)


def downgrade():
    with op.batch_alter_table('order_product', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.alter_column('pay_amount', existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False)
