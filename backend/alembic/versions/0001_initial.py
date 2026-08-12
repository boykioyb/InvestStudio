"""baseline schema

Baseline dựng TỪ CHÍNH models (Base.metadata) — đảm bảo đúng 100% cả cột
Vector(768) lẫn index HNSW, thứ mà autogenerate của Alembic hay dựng thiếu với
pgvector. Các migration SAU này dùng `alembic revision --autogenerate` bình thường.

Idempotent: `create_all(checkfirst=True)` bỏ qua bảng đã có → an toàn khi áp lên
DB đã tạo sẵn bằng create_all trước đây (chỉ thêm bảng thiếu + đánh dấu version).

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    import app.models  # noqa: F401 - đăng ký toàn bộ bảng
    from app.db.base import Base
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    import app.models  # noqa: F401
    from app.db.base import Base
    Base.metadata.drop_all(bind=op.get_bind())
