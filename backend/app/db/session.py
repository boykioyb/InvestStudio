"""Engine, session và khởi tạo cơ sở dữ liệu.

Dùng SQLAlchemy ĐỒNG BỘ (sync) cho khớp với phong cách route hiện có (các
endpoint là `def`, không phải `async def`). psycopg 3 chạy sync tốt và đơn giản
hơn khi lồng vào codebase sync.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

_settings = get_settings()

#  pool_pre_ping: kiểm tra kết nối còn sống trước khi dùng (Postgres hay đóng
#  kết nối nhàn rỗi) → tránh lỗi "server closed the connection" ngẫu nhiên.
engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """Dependency của FastAPI: mở 1 session cho mỗi request, đóng khi xong."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Tạo extension pgvector + toàn bộ bảng nếu chưa có (idempotent).

    Gọi lúc khởi động app. Import model NGAY TẠI ĐÂY để chúng đăng ký vào
    `Base.metadata` trước khi `create_all` chạy — nếu import ở đầu file sẽ
    gây import vòng với `base.py`.
    """
    from app import models  # noqa: F401  (nạp để đăng ký bảng)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
