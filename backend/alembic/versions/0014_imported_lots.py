"""imported_lots — từng đợt khớp (mua/bán) đồng bộ từ lịch sử lệnh TCBS

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "imported_lots"):
        return
    op.create_table(
        "imported_lots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticker", sa.String(12), nullable=False),
        sa.Column("side", sa.String(4), nullable=False, server_default="buy"),
        sa.Column("quantity", sa.Float, nullable=False, server_default="0"),
        sa.Column("price", sa.Float, nullable=False, server_default="0"),
        sa.Column("fee", sa.Float, nullable=True),
        sa.Column("tax", sa.Float, nullable=True),
        sa.Column("txdate", sa.String(16), nullable=False, server_default=""),
        sa.Column("order_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("source", sa.String(16), nullable=False, server_default="TCBS"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "imported_lots"):
        op.drop_table("imported_lots")
