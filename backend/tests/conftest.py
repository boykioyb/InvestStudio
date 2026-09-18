"""Fixture cho test CẦN cơ sở dữ liệu.

Dùng một DB RIÊNG `phantichma_test` để tuyệt đối không đụng dữ liệu thật (kho
RAG, tài khoản). Test KHÔNG dùng các fixture này (VD test_scoring) sẽ không kích
hoạt kết nối DB, nên vẫn chạy được cả khi không có Postgres.
"""
from __future__ import annotations

import os

#  Trỏ sang DB test TRƯỚC khi bất kỳ module app nào đọc cấu hình (get_settings
#  cache lần gọi đầu). Chỉ đặt biến môi trường — chưa mở kết nối nào ở đây.
_BASE = os.environ.get(
    "APP_DATABASE_URL", "postgresql+psycopg://invest:invest@postgres:5432/phantichma")
_TEST_DB = "phantichma_test"
os.environ["APP_DATABASE_URL"] = _BASE.rsplit("/", 1)[0] + "/" + _TEST_DB
os.environ["APP_GEMINI_API_KEY"] = ""  # chắc chắn test không gọi Gemini thật
#  Google OAuth phải TẮT theo mặc định trong test: các test luồng đăng nhập tự bật
#  bằng monkeypatch.setattr trên settings (xem tests/test_auth_google.py::_enable).
#  Xoá env kế thừa từ container để test "tắt mặc định / trả 503" không bị lộ khoá thật.
os.environ.pop("APP_GOOGLE_CLIENT_ID", None)
os.environ.pop("APP_GOOGLE_CLIENT_SECRET", None)
#  Vô hiệu hóa giới hạn tần suất trong test (nhiều lần register/login liên tiếp,
#  và cả bộ test bắn hơn 120 request/phút từ cùng một "IP").
os.environ["APP_LOGIN_MAX_ATTEMPTS"] = "1000000"
os.environ["APP_API_RATE_LIMIT_PER_MINUTE"] = "1000000"
#  Khu quản trị: test chạy không có ứng dụng xác thực nên tắt bắt buộc 2 lớp;
#  có test riêng bật lại để kiểm đúng rào này (tests/test_admin.py).
os.environ["APP_ADMIN_REQUIRE_2FA"] = "false"
#  Test chạy KHÔNG có SMTP: mặc định không bắt xác minh email, test nào cần kiểm
#  rào này thì tự bật lại bằng monkeypatch (xem tests/test_account.py).
os.environ["APP_REQUIRE_VERIFIED_EMAIL"] = "false"

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
    #  Bảng app_settings vừa bị xóa → phải bỏ cache trong tiến trình, nếu không
    #  cờ của test trước còn hiệu lực tới 30 giây sang test sau.
    from app.core import settings_store
    settings_store.invalidate()

    with db_engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE users, watchlist_items, rag_documents, index_jobs, "
            "device_fingerprints, device_accounts, usage_events, usage_daily, "
            "audit_logs, app_settings RESTART IDENTITY CASCADE"))
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
