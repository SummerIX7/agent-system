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
    op.add_column("learners", sa.Column("knowledge_points", sa.JSON, nullable=True, comment="知识点评分列表"))
    op.add_column("learners", sa.Column("blind_spots", sa.JSON, nullable=True, comment="知识盲区列表"))
    op.add_column("learners", sa.Column("overall_level", sa.String(20), nullable=True, comment="整体水平"))
    op.add_column("learners", sa.Column("recommended_difficulty", sa.String(20), nullable=True, comment="推荐难度"))


def downgrade() -> None:
    """移除诊断结果字段"""
    op.drop_column("learners", "recommended_difficulty")
    op.drop_column("learners", "overall_level")
    op.drop_column("learners", "blind_spots")
    op.drop_column("learners", "knowledge_points")
