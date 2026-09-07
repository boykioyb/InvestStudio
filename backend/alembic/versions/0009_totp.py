"""users.totp_secret — xác thực 2 lớp cho tài khoản quản trị

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _has(bind) -> bool:
    return "totp_secret" in {c["name"] for c in sa.inspect(bind).get_columns("users")}


def upgrade() -> None:
    if not _has(op.get_bind()):
        op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=False,
                                         server_default=""))


def downgrade() -> None:
    if _has(op.get_bind()):
        op.drop_column("users", "totp_secret")
