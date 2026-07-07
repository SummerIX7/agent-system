"""add current_level field to learners

Revision ID: c3d4e5f6a7b8
Revises: 452e4ae865be
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = '452e4ae865be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加用户自评当前水平字段到 learners 表"""
    op.add_column("learners", sa.Column("current_level", sa.String(20), nullable=True, comment="用户自评当前水平: beginner/intermediate/advanced/expert"))


def downgrade() -> None:
    """移除 current_level 字段"""
    op.drop_column("learners", "current_level")
