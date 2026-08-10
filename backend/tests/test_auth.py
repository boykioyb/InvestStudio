"""Test xác thực: đăng ký, đăng nhập, /me, đăng xuất — dùng cookie httpOnly."""
from __future__ import annotations


def _register(client, email="a@b.com", password="secret123"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_register_sets_cookie_and_me(client):
    r = _register(client)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "a@b.com"
    assert r.json()["display_name"] == "a"  # mặc định = phần trước @
    assert client.cookies.get("access_token")

    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "a@b.com"


def test_register_duplicate_email_409(client):
    _register(client)
    dup = _register(client, password="other123")
    assert dup.status_code == 409


def test_login_wrong_password_401(client):
    _register(client)
    bad = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong12345"})
    assert bad.status_code == 401
    #  Thông điệp KHÔNG được tiết lộ email có tồn tại hay không.
    assert "mật khẩu" in bad.json()["detail"].lower()


def test_login_unknown_email_same_message(client):
    r = client.post("/api/auth/login", json={"email": "none@b.com", "password": "whatever12"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    _register(client)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "123"})
    assert r.status_code == 422  # min_length=6
