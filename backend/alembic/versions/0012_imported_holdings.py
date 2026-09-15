"""imported_holdings — danh mục cổ phiếu đồng bộ từ công ty chứng khoán (TCBS…)

Lưu số lượng + giá vốn từng mã người dùng đang giữ, đẩy về từ extension qua
`POST /api/portfolio/import`. KHÔNG lưu token/thông tin đăng nhập TCBS.

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "imported_holdings"):
        return
    op.create_table(
        "imported_holdings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticker", sa.String(12), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_price", sa.Float, nullable=True),
        sa.Column("market_price", sa.Float, nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="TCBS"),
        sa.Column("account_no", sa.String(24), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "imported_holdings"):
        op.drop_table("imported_holdings")
