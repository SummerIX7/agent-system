"""add practice_results and report_caches tables, drop learner.report_cache

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.database import JsonText


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """P0: 新增 practice_results 表；P1: 新增 report_caches 表 + 移除 learners.report_cache"""

    # P0: practice_results 表
    op.create_table(
        "practice_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("learner_id", sa.Integer, sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("stage", sa.Integer, nullable=True),
        sa.Column("score", sa.Integer, default=0),
        sa.Column("correct_count", sa.Integer, default=0),
        sa.Column("wrong_count", sa.Integer, default=0),
        sa.Column("question_count", sa.Integer, default=0),
        sa.Column("questions", JsonText, nullable=True),
        sa.Column("label", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True, index=True),
    )

    # P1: report_caches 表（从 learners.report_cache 拆出）
    op.create_table(
        "report_caches",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("learner_id", sa.Integer, sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("cache_data", JsonText, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # 数据迁移：learners.report_cache → report_caches
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, report_cache FROM learners WHERE report_cache IS NOT NULL")).fetchall()
    for learner_id, cache_data in rows:
        conn.execute(sa.text(
            "INSERT INTO report_caches (learner_id, cache_data, updated_at) "
            "VALUES (:lid, :cd, NOW()) "
            "ON DUPLICATE KEY UPDATE cache_data = :cd, updated_at = NOW()"
        ), {"lid": learner_id, "cd": cache_data})

    # 移除 learners.report_cache 列
    op.drop_column("learners", "report_cache")


def downgrade() -> None:
    """回滚：恢复 learners.report_cache，删除两张新表"""
    # 恢复 learners.report_cache 列
    op.add_column("learners", sa.Column("report_cache", JsonText, nullable=True, comment="报告指标快照"))

    # 数据回迁：report_caches → learners.report_cache
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT learner_id, cache_data FROM report_caches")).fetchall()
    for learner_id, cache_data in rows:
        conn.execute(sa.text("UPDATE learners SET report_cache = :cd WHERE id = :lid"), {"lid": learner_id, "cd": cache_data})

    op.drop_table("report_caches")
    op.drop_table("practice_results")
