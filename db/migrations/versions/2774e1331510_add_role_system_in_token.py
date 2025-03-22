"""Add role system in Token

Revision ID: 2774e1331510
Revises: 3e71250dcbf0
Create Date: 2025-03-15 17:01:29.230599

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2774e1331510'
down_revision: Union[str, None] = '3e71250dcbf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tokens', sa.Column('subscription_until', sa.DateTime(), nullable=True))
    op.add_column('tokens', sa.Column('role', sa.String(length=50), nullable=True))
    op.drop_constraint('uq_user_warehouse', 'user_warehouses', type_='unique')
    op.create_unique_constraint('uq_us er_warehouse', 'user_warehouses', ['user_id', 'warehouse_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uq_us er_warehouse', 'user_warehouses', type_='unique')
    op.create_unique_constraint('uq_user_warehouse', 'user_warehouses', ['user_id', 'warehouse_id'])
    op.drop_column('tokens', 'role')
    op.drop_column('tokens', 'subscription_until')
    # ### end Alembic commands ###
