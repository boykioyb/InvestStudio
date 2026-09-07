"""thêm cột users.role (phân quyền quản trị)

Mở đường cho `require_admin`: việc TỐN HẠN MỨC CHUNG (lập chỉ mục RAG) không
còn để mọi tài khoản đã đăng nhập bấm được.

Idempotent: chỉ thêm cột nếu chưa có; server_default 'user' để hàng cũ hợp lệ.
Cấp admin đầu tiên bằng tay:
    UPDATE users SET role='admin' WHERE email='...';

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_TABLE = "users"
_COL = "role"


def _has_column(bind) -> bool:
    return _COL in {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind):
        op.add_column(_TABLE, sa.Column(
            _COL, sa.String(16), nullable=False, server_default="user"))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind):
        op.drop_column(_TABLE, _COL)
