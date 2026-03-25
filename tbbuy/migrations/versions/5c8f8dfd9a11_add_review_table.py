"""add review table

Revision ID: 5c8f8dfd9a11
Revises: 30b1f983a238
Create Date: 2026-03-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c8f8dfd9a11'
down_revision = '30b1f983a238'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'review',
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.String(length=200), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.create_index('idx_order_id', ['order_id'], unique=False)
        batch_op.create_index('idx_user_id', ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.drop_index('idx_user_id')
        batch_op.drop_index('idx_order_id')

    op.drop_table('review')
