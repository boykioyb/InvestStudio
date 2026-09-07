"""users: status · email_verified_at · token_version · last_login_at · last_ip

Nền cho S1: xác minh email (chống tạo tài khoản hàng loạt để nhân hạn mức),
thu hồi phiên khi đổi mật khẩu, khóa tài khoản, và dấu vết điều tra lạm dụng.

Idempotent: chỉ thêm cột nào chưa có. Tài khoản CŨ được coi là ĐÃ xác minh
(email_verified_at = created_at) — người đang dùng không bị khóa tính năng chỉ
vì hệ thống nâng cấp.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_TABLE = "users"
_COLS = {
    "status": sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    "email_verified_at": sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    "token_version": sa.Column("token_version", sa.Integer, nullable=False, server_default="0"),
    "last_login_at": sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    "last_ip": sa.Column("last_ip", sa.String(45), nullable=False, server_default=""),
}


def _existing(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    have = _existing(bind)
    added = [name for name in _COLS if name not in have]
    for name in added:
        op.add_column(_TABLE, _COLS[name])
    if "email_verified_at" in added:
        #  Người đang dùng không phải xác minh lại.
        op.execute("UPDATE users SET email_verified_at = created_at "
                   "WHERE email_verified_at IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    have = _existing(bind)
    for name in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
