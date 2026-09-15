"""users.auth_provider + users.oauth_sub — đăng nhập Google (OAuth2)

Tài khoản Google không có mật khẩu (`password_hash` để rỗng). `oauth_sub` là
`sub` ổn định của Google, dùng khớp lại người dùng cũ kể cả khi đổi email.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _cols(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns("users")}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _cols(bind)
    if "auth_provider" not in cols:
        op.add_column("users", sa.Column("auth_provider", sa.String(16), nullable=False,
                                         server_default="password"))
    if "oauth_sub" not in cols:
        op.add_column("users", sa.Column("oauth_sub", sa.String(64), nullable=True))
        #  Postgres cho phép nhiều NULL trong ràng buộc unique → an toàn với tài
        #  khoản mật khẩu (oauth_sub = NULL) mà vẫn chặn hai người trùng sub Google.
        op.create_unique_constraint("uq_users_oauth_sub", "users", ["oauth_sub"])


def downgrade() -> None:
    bind = op.get_bind()
    cols = _cols(bind)
    if "oauth_sub" in cols:
        op.drop_constraint("uq_users_oauth_sub", "users", type_="unique")
        op.drop_column("users", "oauth_sub")
    if "auth_provider" in cols:
        op.drop_column("users", "auth_provider")
