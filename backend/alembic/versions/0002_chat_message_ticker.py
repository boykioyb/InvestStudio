"""thêm cột ticker vào chat_messages

Cho phép widget nổi tải lại lịch sử ĐÚNG theo mã đang xem (không lẫn mã khác).

Idempotent: baseline 0001 dựng bảng bằng `create_all` từ models — nếu DB tạo
MỚI sau khi model đã có `ticker` thì cột đã tồn tại, migration này bỏ qua; nếu
DB CŨ (bảng chưa có cột) thì thêm vào. Nhờ vậy áp được cho cả hai trường hợp.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TABLE = "chat_messages"
_COLUMN = "ticker"
_INDEX = "ix_chat_messages_ticker"


def _columns(bind) -> set[str]:
    return {col["name"] for col in sa.inspect(bind).get_columns(_TABLE)}


def _indexes(bind) -> set[str]:
    return {idx["name"] for idx in sa.inspect(bind).get_indexes(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    if _COLUMN not in _columns(bind):
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(length=12), nullable=True))
    if _INDEX not in _indexes(bind):
        op.create_index(_INDEX, _TABLE, [_COLUMN])


def downgrade() -> None:
    bind = op.get_bind()
    if _INDEX in _indexes(bind):
        op.drop_index(_INDEX, table_name=_TABLE)
    if _COLUMN in _columns(bind):
        op.drop_column(_TABLE, _COLUMN)
