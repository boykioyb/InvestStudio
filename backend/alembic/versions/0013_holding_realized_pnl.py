"""imported_holdings.realized_pnl — lãi/lỗ đã thực hiện đồng bộ từ TCBS

Revision ID: 0013
Revises: 0012
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _cols(bind) -> set[str]:
    if not sa.inspect(bind).has_table("imported_holdings"):
        return set()
    return {c["name"] for c in sa.inspect(bind).get_columns("imported_holdings")}


def upgrade() -> None:
    bind = op.get_bind()
    if "realized_pnl" not in _cols(bind):
        op.add_column("imported_holdings", sa.Column("realized_pnl", sa.Float, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if "realized_pnl" in _cols(bind):
        op.drop_column("imported_holdings", "realized_pnl")
