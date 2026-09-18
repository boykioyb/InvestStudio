"""product_events — sự kiện hành vi để đo North Star Metric

Bảng TÁCH RIÊNG khỏi usage_events (usage_events đo chi phí/quota; bảng này đo giá
trị/hành vi). Xem app/models/analytics.py để biết lý do tách.

Idempotent: kiểm tra bảng đã tồn tại chưa trước khi tạo, để chạy được cả trên DB
mới lẫn DB đã có.

Revision ID: 0016
Revises: 0015
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("product_events"):
        return
    op.create_table(
        "product_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("fp_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("ticker", sa.String(12), nullable=False, server_default=""),
        sa.Column("ref", sa.String(48), nullable=False, server_default=""),
    )
    op.create_index("ix_product_events_event_at", "product_events", ["event", "at"])
    op.create_index("ix_product_events_user_at", "product_events", ["user_id", "at"])


def downgrade() -> None:
    if not _has_table("product_events"):
        return
    op.drop_index("ix_product_events_user_at", table_name="product_events")
    op.drop_index("ix_product_events_event_at", table_name="product_events")
    op.drop_table("product_events")
