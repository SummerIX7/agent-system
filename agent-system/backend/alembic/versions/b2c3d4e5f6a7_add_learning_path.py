"""add learning_path to learners

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 learning_path 字段到 learners 表"""
    bind = op.get_bind()
    bind.execute(sa.text(
        "ALTER TABLE learners ADD COLUMN learning_path JSON DEFAULT NULL COMMENT '学习路径'"
    ))


def downgrade() -> None:
    """移除 learning_path 字段"""
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE learners DROP COLUMN learning_path"))
