"""Fixture cho test CẦN cơ sở dữ liệu.

Dùng một DB RIÊNG `investstudio_test` để tuyệt đối không đụng dữ liệu thật (kho
RAG, tài khoản). Test KHÔNG dùng các fixture này (VD test_scoring) sẽ không kích
hoạt kết nối DB, nên vẫn chạy được cả khi không có Postgres.
"""
from __future__ import annotations

import os

#  Trỏ sang DB test TRƯỚC khi bất kỳ module app nào đọc cấu hình (get_settings
#  cache lần gọi đầu). Chỉ đặt biến môi trường — chưa mở kết nối nào ở đây.
_BASE = os.environ.get(
    "APP_DATABASE_URL", "postgresql+psycopg://invest:invest@postgres:5432/investstudio")
_TEST_DB = "investstudio_test"
os.environ["APP_DATABASE_URL"] = _BASE.rsplit("/", 1)[0] + "/" + _TEST_DB
os.environ["APP_GEMINI_API_KEY"] = ""  # chắc chắn test không gọi Gemini thật
#  Vô hiệu hóa giới hạn tần suất trong test (nhiều lần register/login liên tiếp).
os.environ["APP_LOGIN_MAX_ATTEMPTS"] = "1000000"

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402


@pytest.fixture(scope="session")
def db_engine():
    """Tạo DB test (nếu chưa có) + toàn bộ bảng. Chỉ chạy khi có test yêu cầu."""
    import psycopg

    admin_url = (_BASE.rsplit("/", 1)[0] + "/postgres").replace("+psycopg", "")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        row = conn.execute(
            "select 1 from pg_database where datname=%s", (_TEST_DB,)).fetchone()
        if not row:
            conn.execute(f'create database "{_TEST_DB}"')

    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.db.session import engine, init_db
    init_db()
    return engine


@pytest.fixture
def _clean(db_engine):
    """Dọn sạch bảng trước mỗi test → các test độc lập, không ảnh hưởng nhau."""
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE users, watchlist_items, rag_documents, index_jobs "
                           "RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db(db_engine, _clean):
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine, _clean):
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as test_client:
        yield test_client
