"""thêm bảng conversations + cột chat_messages.conversation_id

Cho phép nhóm hỏi–đáp thành nhiều 'câu chuyện' (thread) như ChatGPT/Messenger.
KHÔNG gom lịch sử phẳng cũ (theo quyết định) — tin nhắn cũ giữ conversation_id NULL.

Idempotent: tạo bảng bằng create_all(checkfirst=True); thêm cột/FK/index nếu chưa có.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_TABLE = "chat_messages"
_COL = "conversation_id"
_FK = "fk_chat_messages_conversation"
_IDX = "ix_chat_messages_conversation_id"


def _cols(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}


def _idx(bind) -> set[str]:
    return {i["name"] for i in sa.inspect(bind).get_indexes(_TABLE)}


def _fks(bind) -> set[str]:
    return {f["name"] for f in sa.inspect(bind).get_foreign_keys(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    import app.models  # noqa: F401 - đăng ký bảng
    from app.db.base import Base
    #  Tạo 'conversations' nếu chưa có (bỏ qua bảng đã tồn tại).
    Base.metadata.create_all(bind=bind, checkfirst=True)

    if _COL not in _cols(bind):
        op.add_column(_TABLE, sa.Column(_COL, sa.Integer(), nullable=True))
    if _FK not in _fks(bind):
        op.create_foreign_key(_FK, _TABLE, "conversations", [_COL], ["id"], ondelete="CASCADE")
    if _IDX not in _idx(bind):
        op.create_index(_IDX, _TABLE, [_COL])


def downgrade() -> None:
    bind = op.get_bind()
    if _IDX in _idx(bind):
        op.drop_index(_IDX, table_name=_TABLE)
    if _FK in _fks(bind):
        op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    if _COL in _cols(bind):
        op.drop_column(_TABLE, _COL)
    op.execute("DROP TABLE IF EXISTS conversations")
