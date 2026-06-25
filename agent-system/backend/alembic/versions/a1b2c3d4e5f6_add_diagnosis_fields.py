"""add diagnosis fields to learners

Revision ID: a1b2c3d4e5f6
Revises: d92840797b02
Create Date: 2026-06-24 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd92840797b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加诊断结果字段到 learners 表"""
    # 使用 raw SQL 添加列，避免 SQLAlchemy 类型检测问题
    bind = op.get_bind()
    bind.execute(sa.text(
        "ALTER TABLE learners ADD COLUMN knowledge_points JSON DEFAULT NULL COMMENT '知识点评分列表'"
    ))
    bind.execute(sa.text(
        "ALTER TABLE learners ADD COLUMN blind_spots JSON DEFAULT NULL COMMENT '知识盲区列表'"
    ))
    bind.execute(sa.text(
        "ALTER TABLE learners ADD COLUMN overall_level VARCHAR(20) DEFAULT NULL COMMENT '整体水平'"
    ))
    bind.execute(sa.text(
        "ALTER TABLE learners ADD COLUMN recommended_difficulty VARCHAR(20) DEFAULT NULL COMMENT '推荐难度'"
    ))


def downgrade() -> None:
    """移除诊断结果字段"""
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE learners DROP COLUMN knowledge_points"))
    bind.execute(sa.text("ALTER TABLE learners DROP COLUMN blind_spots"))
    bind.execute(sa.text("ALTER TABLE learners DROP COLUMN overall_level"))
    bind.execute(sa.text("ALTER TABLE learners DROP COLUMN recommended_difficulty"))
