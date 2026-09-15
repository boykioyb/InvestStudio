"""Đăng nhập Google (OAuth2 — luồng authorization code phía server).

Không gọi Google thật: bật cấu hình bằng monkeypatch, giả lập token endpoint và
dựng sẵn `id_token` (backend không kiểm chữ ký vì token lấy trực tiếp qua TLS,
chỉ soi claim aud/iss/exp).
"""
from __future__ import annotations

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

from app.api.routes import auth_google
from app.core.config import get_settings
from app.models.user import User

_CLIENT_ID = "test-client-id.apps.googleusercontent.com"


def _enable(monkeypatch) -> None:
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", _CLIENT_ID)
    monkeypatch.setattr(s, "google_client_secret", "test-secret")


def _b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def _id_token(*, sub="g-sub-123", email="nguoimoi@gmail.com", email_verified=True,
              name="Người Mới", aud=_CLIENT_ID, iss="https://accounts.google.com",
              exp=None) -> str:
    exp = exp if exp is not None else int(time.time()) + 300
    payload = {"sub": sub, "email": email, "email_verified": email_verified,
               "name": name, "aud": aud, "iss": iss, "exp": exp}
    return f"{_b64({'alg': 'RS256'})}.{_b64(payload)}.sig"


class _FakeResp:
    def __init__(self, data: dict, status_code: int = 200) -> None:
        self._d = data
        self.status_code = status_code

    def json(self) -> dict:
        return self._d


def _patch_token(monkeypatch, id_token: str, status_code: int = 200) -> None:
    def fake_post(url, data=None, timeout=None):  # noqa: ANN001
        return _FakeResp({"id_token": id_token}, status_code)
    monkeypatch.setattr(auth_google.httpx, "post", fake_post)


def _start(client, app: str = "web") -> str:
    """Gọi /start, trả về `state` (đồng thời TestClient giữ cookie g_oauth_state)."""
    r = client.get("/api/auth/google/start", params={"next": "/", "app": app})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    return parse_qs(urlparse(url).query)["state"][0]


#  ── config ────────────────────────────────────────────────────────────────

def test_oauth_config_tat_mac_dinh(client):
    assert client.get("/api/auth/oauth-config").json() == {"google": False}


def test_start_khi_chua_cau_hinh_tra_503(client):
    assert client.get("/api/auth/google/start").status_code == 503


def test_config_bat_khi_co_du_khoa(client, monkeypatch):
    _enable(monkeypatch)
    assert client.get("/api/auth/oauth-config").json() == {"google": True}
    r = client.get("/api/auth/google/start", params={"next": "/watchlist"})
    assert r.status_code == 200
    q = parse_qs(urlparse(r.json()["url"]).query)
    assert q["client_id"][0] == _CLIENT_ID
    assert q["redirect_uri"][0].endswith("/api/auth/google/callback")


#  ── callback: tạo mới / khớp lại / liên kết ─────────────────────────────────

def test_callback_tao_tai_khoan_moi_va_dat_cookie(client, db, monkeypatch):
    _enable(monkeypatch)
    state = _start(client)
    _patch_token(monkeypatch, _id_token(email="nguoimoi@gmail.com"))

    r = client.get("/api/auth/google/callback", params={"code": "abc", "state": state})
    assert r.status_code == 200
    assert client.cookies.get("access_token")  # đã đăng nhập
    #  /me chạy được với cookie vừa nhận
    assert client.get("/api/auth/me").json()["email"] == "nguoimoi@gmail.com"

    u = db.query(User).filter_by(email="nguoimoi@gmail.com").one()
    assert u.auth_provider == "google" and u.oauth_sub == "g-sub-123"
    assert u.password_hash == ""              # tài khoản Google không có mật khẩu
    assert u.email_verified_at is not None     # Google báo đã xác minh → đánh dấu


def test_callback_khop_lai_nguoi_cu_theo_sub(client, monkeypatch):
    _enable(monkeypatch)
    #  Lần 1 tạo mới
    _patch_token(monkeypatch, _id_token(sub="g-42", email="x@gmail.com"))
    client.get("/api/auth/google/callback", params={"code": "a", "state": _start(client)})
    client.post("/api/auth/logout")
    #  Lần 2 cùng sub nhưng đổi tên hiển thị → vẫn đúng một tài khoản
    _patch_token(monkeypatch, _id_token(sub="g-42", email="x@gmail.com", name="Đổi Tên"))
    r = client.get("/api/auth/google/callback", params={"code": "b", "state": _start(client)})
    assert r.status_code == 200 and client.cookies.get("access_token")


def test_callback_lien_ket_vao_tai_khoan_mat_khau_cung_email(client, db, monkeypatch):
    #  Có sẵn tài khoản mật khẩu
    client.post("/api/auth/register", json={"email": "co@gmail.com", "password": "matkhau-that-dai"})
    client.post("/api/auth/logout")
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-link", email="co@gmail.com", email_verified=True))
    r = client.get("/api/auth/google/callback", params={"code": "c", "state": _start(client)})
    assert r.status_code == 200 and client.cookies.get("access_token")
    u = db.query(User).filter_by(email="co@gmail.com").one()
    assert u.oauth_sub == "g-link"      # đã gắn Google vào tài khoản cũ
    assert u.password_hash != ""         # mật khẩu cũ vẫn còn


def test_callback_khong_lien_ket_khi_email_google_chua_xac_minh(client, db, monkeypatch):
    client.post("/api/auth/register", json={"email": "co2@gmail.com", "password": "matkhau-that-dai"})
    client.post("/api/auth/logout")
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-x", email="co2@gmail.com", email_verified=False))
    r = client.get("/api/auth/google/callback", params={"code": "d", "state": _start(client)})
    #  Không đặt cookie đăng nhập; đưa về /login kèm lỗi
    assert client.cookies.get("access_token") is None
    assert "oauth_error" in r.text
    assert db.query(User).filter_by(email="co2@gmail.com").one().oauth_sub is None


#  ── chống giả mạo & claim sai ───────────────────────────────────────────────

def test_callback_state_sai_bi_tu_choi(client, monkeypatch):
    _enable(monkeypatch)
    _start(client)  # có cookie state hợp lệ
    _patch_token(monkeypatch, _id_token())
    r = client.get("/api/auth/google/callback", params={"code": "abc", "state": "bia-dat"})
    assert client.cookies.get("access_token") is None
    assert "oauth_error" in r.text


def test_callback_tu_choi_khi_aud_khong_khop(client, monkeypatch):
    _enable(monkeypatch)
    state = _start(client)
    _patch_token(monkeypatch, _id_token(aud="ung-dung-khac"))
    r = client.get("/api/auth/google/callback", params={"code": "abc", "state": state})
    assert client.cookies.get("access_token") is None
    assert "oauth_error" in r.text


def test_callback_tu_choi_khi_token_het_han(client, monkeypatch):
    _enable(monkeypatch)
    state = _start(client)
    _patch_token(monkeypatch, _id_token(exp=int(time.time()) - 10))
    r = client.get("/api/auth/google/callback", params={"code": "abc", "state": state})
    assert client.cookies.get("access_token") is None


#  ── tài khoản Google đăng nhập bằng mật khẩu thì được chỉ đúng nút ──────────

def test_login_mat_khau_vao_tai_khoan_google_bi_chi_sang_nut_google(client, monkeypatch):
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-pw", email="chigoogle@gmail.com"))
    client.get("/api/auth/google/callback", params={"code": "a", "state": _start(client)})
    client.post("/api/auth/logout")
    bad = client.post("/api/auth/login",
                      json={"email": "chigoogle@gmail.com", "password": "doan-mo-ho-123"})
    assert bad.status_code == 401
    assert "google" in bad.json()["detail"].lower()


#  ── luồng QUẢN TRỊ (app=admin): chỉ cho admin đã có, KHÔNG tự tạo ────────────

def test_start_admin_dung_redirect_uri_rieng(client, monkeypatch):
    _enable(monkeypatch)
    r = client.get("/api/auth/google/start", params={"next": "/", "app": "admin"})
    assert r.status_code == 200
    redirect = parse_qs(urlparse(r.json()["url"]).query)["redirect_uri"][0]
    #  Origin admin (:3020), KHÔNG phải origin công khai (:3010).
    assert redirect == get_settings().google_admin_redirect_uri
    assert redirect != get_settings().google_redirect_uri


def _make_user(db, *, email, role="user", oauth_sub=None, email_verified=True):
    from datetime import datetime, timezone
    u = User(email=email, display_name=email.split("@")[0], password_hash="x",
             role=role, oauth_sub=oauth_sub,
             email_verified_at=datetime.now(timezone.utc) if email_verified else None)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_callback_admin_cho_vao_khi_la_admin(client, db, monkeypatch):
    _make_user(db, email="sep@gmail.com", role="admin", oauth_sub="g-admin")
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-admin", email="sep@gmail.com"))
    r = client.get("/api/auth/google/callback",
                   params={"code": "a", "state": _start(client, app="admin")})
    assert r.status_code == 200
    assert client.cookies.get("access_token")
    assert client.get("/api/auth/me").json()["role"] == "admin"


def test_callback_admin_lien_ket_admin_cu_theo_email(client, db, monkeypatch):
    #  Admin cũ đăng nhập mật khẩu (chưa gắn Google), email đã kiểm chứng.
    _make_user(db, email="sep2@gmail.com", role="admin", oauth_sub=None)
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-new", email="sep2@gmail.com", email_verified=True))
    r = client.get("/api/auth/google/callback",
                   params={"code": "a", "state": _start(client, app="admin")})
    assert r.status_code == 200 and client.cookies.get("access_token")
    assert db.query(User).filter_by(email="sep2@gmail.com").one().oauth_sub == "g-new"


def test_callback_admin_tu_choi_va_khong_tao_tai_khoan(client, db, monkeypatch):
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-la", email="nguoila@gmail.com"))
    r = client.get("/api/auth/google/callback",
                   params={"code": "a", "state": _start(client, app="admin")})
    #  Không đặt cookie, về /login kèm lỗi, và TUYỆT ĐỐI không đẻ tài khoản mới.
    assert client.cookies.get("access_token") is None
    assert "oauth_error" in r.text
    assert db.query(User).filter_by(email="nguoila@gmail.com").first() is None


def test_callback_admin_tu_choi_user_thuong_da_ton_tai(client, db, monkeypatch):
    #  Tài khoản thường (role=user) khớp email → vẫn bị chặn, KHÔNG gắn Google.
    _make_user(db, email="thuong@gmail.com", role="user", oauth_sub=None)
    _enable(monkeypatch)
    _patch_token(monkeypatch, _id_token(sub="g-thuong", email="thuong@gmail.com"))
    r = client.get("/api/auth/google/callback",
                   params={"code": "a", "state": _start(client, app="admin")})
    assert client.cookies.get("access_token") is None
    assert "oauth_error" in r.text
    assert db.query(User).filter_by(email="thuong@gmail.com").one().oauth_sub is None
