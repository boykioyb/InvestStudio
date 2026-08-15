"""thêm bảng attachments + cột chat_messages.attachments

Hỗ trợ đính kèm ảnh/PDF cho trợ lý (multimodal). Tệp lưu trên đĩa (volume),
DB giữ metadata.

Idempotent: tạo bảng bằng create_all(checkfirst=True); thêm cột nếu chưa có
(server_default '[]' để hàng cũ có giá trị hợp lệ).

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_TABLE = "chat_messages"
_COL = "attachments"


def _cols(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    import app.models  # noqa: F401 - đăng ký bảng
    from app.db.base import Base
    Base.metadata.create_all(bind=bind, checkfirst=True)  # tạo 'attachments' nếu chưa có

    if _COL not in _cols(bind):
        op.add_column(_TABLE, sa.Column(
            _COL, pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    bind = op.get_bind()
    if _COL in _cols(bind):
        op.drop_column(_TABLE, _COL)
    op.execute("DROP TABLE IF EXISTS attachments")
