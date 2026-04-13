"""make wallet money decimal

Revision ID: 8f3a7b2c4d11
Revises: 2e5e44739a70
Create Date: 2026-04-13 01:24:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '8f3a7b2c4d11'
down_revision = '2e5e44739a70'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('wallet_money', existing_type=sa.Integer(), type_=sa.Numeric(10, 2), existing_nullable=False)
    with op.batch_alter_table('wallet_transaction', schema=None) as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Integer(), type_=sa.Numeric(10, 2), existing_nullable=False)


def downgrade():
    with op.batch_alter_table('wallet_transaction', schema=None) as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False)
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('wallet_money', existing_type=sa.Numeric(10, 2), type_=sa.Integer(), existing_nullable=False)
