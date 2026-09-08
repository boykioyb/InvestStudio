"""users.alert_email — bật/tắt email cảnh báo ngưỡng

Mặc định BẬT: người dùng đã tự đặt ngưỡng thì hiển nhiên muốn được báo.

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _has(bind) -> bool:
    return "alert_email" in {c["name"] for c in sa.inspect(bind).get_columns("users")}


def upgrade() -> None:
    if not _has(op.get_bind()):
        op.add_column("users", sa.Column("alert_email", sa.Boolean, nullable=False,
                                         server_default="true"))


def downgrade() -> None:
    if _has(op.get_bind()):
        op.drop_column("users", "alert_email")
