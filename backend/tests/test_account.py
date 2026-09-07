"""Test nền tài khoản S1: xác minh email · thu hồi phiên · quên mật khẩu · xóa tài khoản."""
from __future__ import annotations

import pytest

_PW = "matkhau-dai-hon"


def _register(client, email="a@b.com", password=_PW):
    return client.post("/api/auth/register", json={"email": email, "password": password})


# ── Mật khẩu ─────────────────────────────────────────────────────────────────

def test_mat_khau_ngan_bi_tu_choi(client):
    r = _register(client, password="ngan123")
    assert r.status_code == 422


# ── Xác minh email ───────────────────────────────────────────────────────────

def test_dang_ky_xong_chua_xac_minh(client):
    r = _register(client)
    assert r.status_code == 201
    assert r.json()["email_verified"] is False


def test_xac_minh_bang_token_trong_thu(client, db):
    from app.core.security import create_purpose_token
    from app.models.user import User

    _register(client)
    user = db.query(User).one()
    token = create_purpose_token(user.id, "verify-email", 60, extra={"email": user.email})

    r = client.post(f"/api/auth/verify?token={token}")
    assert r.status_code == 200 and r.json()["email_verified"] is True


def test_token_sai_muc_dich_khong_dung_de_xac_minh_duoc(client, db):
    """Token đặt-lại-mật-khẩu không được xài như token xác minh (và ngược lại)."""
    from app.core.security import create_purpose_token
    from app.models.user import User

    _register(client)
    user = db.query(User).one()
    token = create_purpose_token(user.id, "reset-password", 60)
    assert client.post(f"/api/auth/verify?token={token}").status_code == 400


def test_chua_xac_minh_thi_khong_hoi_tro_ly_duoc(client, db, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "require_verified_email", True)

    _register(client)
    r = client.post("/api/chat", json={"question": "FPT thế nào?"})
    assert r.status_code == 403
    assert "xác minh email" in r.json()["detail"].lower()


# ── Thu hồi phiên khi đổi mật khẩu ───────────────────────────────────────────

def test_doi_mat_khau_lam_phien_cu_het_hieu_luc(client):
    _register(client)
    old_cookie = client.cookies.get("access_token")

    r = client.post("/api/auth/change-password",
                    json={"old_password": _PW, "new_password": "mat-khau-moi-dai"})
    assert r.status_code == 204

    #  Dùng lại ĐÚNG token cũ (giả lập kẻ đã trộm được cookie trước đó).
    client.cookies.clear()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_cookie}"})
    assert me.status_code == 401


# ── Quên / đặt lại mật khẩu ──────────────────────────────────────────────────

def test_quen_mat_khau_khong_tiet_lo_email_ton_tai(client):
    """Trả lời phải giống hệt nhau, nếu không đây thành công cụ dò tài khoản."""
    _register(client)
    co = client.post("/api/auth/forgot-password", json={"email": "a@b.com"})
    khong = client.post("/api/auth/forgot-password", json={"email": "khong-co@b.com"})
    assert co.status_code == khong.status_code == 202
    assert co.json() == khong.json()


def test_dat_lai_mat_khau_va_link_chi_dung_duoc_mot_lan(client, db):
    from app.core.security import create_purpose_token
    from app.models.user import User

    _register(client)
    user = db.query(User).one()
    token = create_purpose_token(user.id, "reset-password", 30,
                                 extra={"pw": user.password_hash[-16:]})

    moi = {"token": token, "new_password": "mat-khau-moi-dai"}
    assert client.post("/api/auth/reset-password", json=moi).status_code == 204
    #  Token gắn với hash cũ → đổi xong là tự hỏng, không cần bảng token đã dùng.
    assert client.post("/api/auth/reset-password", json=moi).status_code == 400

    client.cookies.clear()
    dn = client.post("/api/auth/login", json={"email": "a@b.com", "password": "mat-khau-moi-dai"})
    assert dn.status_code == 200


# ── Xóa tài khoản (Nghị định 13/2023) ────────────────────────────────────────

def test_xoa_tai_khoan_can_dung_mat_khau(client):
    _register(client)
    assert client.request("DELETE", "/api/auth/me",
                          json={"password": "sai-mat-khau"}).status_code == 400
    assert client.request("DELETE", "/api/auth/me", json={"password": _PW}).status_code == 204
    client.cookies.clear()
    assert client.post("/api/auth/login",
                       json={"email": "a@b.com", "password": _PW}).status_code == 401


def test_xoa_tai_khoan_keo_theo_du_lieu_con(client, db):
    from app.models.user import User, WatchlistItem

    _register(client)
    assert client.post("/api/watchlist", json={"ticker": "FPT"}).status_code == 201
    client.request("DELETE", "/api/auth/me", json={"password": _PW})

    assert db.query(User).count() == 0
    assert db.query(WatchlistItem).count() == 0


# ── Tài khoản bị khóa ────────────────────────────────────────────────────────

def test_tai_khoan_bi_khoa_khong_dung_duoc(client, db):
    from app.models.user import User

    _register(client)
    user = db.query(User).one()
    user.status = "suspended"
    db.commit()

    assert client.get("/api/auth/me").status_code == 403
    client.cookies.clear()
    assert client.post("/api/auth/login",
                       json={"email": "a@b.com", "password": _PW}).status_code == 403
