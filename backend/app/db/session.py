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
    """Đưa schema về 'head' bằng Alembic (tạo extension pgvector + áp migration).

    Migration baseline (0001) idempotent nên chạy được cả trên DB mới lẫn DB cũ
    đã có bảng. Dùng KHÓA CỐ VẤN Postgres để nhiều service (backend/worker/beat)
    khởi động cùng lúc chỉ MỘT tiến trình migrate tại một thời điểm — tránh đua.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    srv_root = Path(__file__).resolve().parents[2]  # thư mục /srv (chứa alembic.ini)
    cfg = Config(str(srv_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(srv_root / "alembic"))

    lock = engine.connect()
    try:
        lock.execute(text("SELECT pg_advisory_lock(911)"))  # khóa session cho tới khi mở
        lock.commit()
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        command.upgrade(cfg, "head")
    finally:
        lock.execute(text("SELECT pg_advisory_unlock(911)"))
        lock.commit()
        lock.close()
