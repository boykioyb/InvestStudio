"""Test khu quản trị S2: phân quyền · cần gạt khẩn cấp · audit · 2 lớp."""
from __future__ import annotations

import pytest

_PW = "matkhau-dai-hon"


@pytest.fixture
def admin_client(client, db):
    """Tài khoản quản trị đã đăng nhập (nâng quyền thẳng trong DB)."""
    from app.models.user import User

    r = client.post("/api/auth/register", json={"email": "sep@gmail.com", "password": _PW})
    assert r.status_code == 201, r.text
    user = db.query(User).filter(User.email == "sep@gmail.com").one()
    user.role = "admin"
    db.commit()
    return client


def _thuong(client):
    client.cookies.clear()
    r = client.post("/api/auth/register", json={"email": "dan@gmail.com", "password": _PW})
    assert r.status_code == 201
    return client


# ── Phân quyền ───────────────────────────────────────────────────────────────

def test_user_thuong_khong_vao_duoc_admin(client):
    _thuong(client)
    for path in ("/api/admin/overview", "/api/admin/users", "/api/admin/settings"):
        assert client.get(path).status_code == 403, path


def test_khach_khong_vao_duoc_admin(client):
    assert client.get("/api/admin/overview").status_code == 401


def test_danh_sach_ip_cho_phep_tra_404(admin_client, monkeypatch):
    """Cố ý 404 chứ không 403: đừng xác nhận với người lạ rằng ở đây có khu quản trị."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "admin_ip_allowlist", ["203.0.113.0/24"])
    assert admin_client.get("/api/admin/overview").status_code == 404


# ── Tổng quan & người dùng ───────────────────────────────────────────────────

def test_overview_tra_ve_the_so(admin_client):
    r = admin_client.get("/api/admin/overview")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["users_total"] >= 1
    assert data["gemini_cap"] > 0
    assert data["gemini_level"] in ("ok", "saving", "exhausted")


def test_danh_sach_va_tim_kiem_nguoi_dung(admin_client, db):
    from app.models.user import User
    db.add(User(email="ai@gmail.com", display_name="Ai", password_hash="x"))
    db.commit()

    r = admin_client.get("/api/admin/users?q=ai@")
    assert r.status_code == 200
    assert [u["email"] for u in r.json()["items"]] == ["ai@gmail.com"]


def test_khoa_tai_khoan_thi_phien_cua_ho_chet(admin_client, client, db):
    """Khóa phải đá người đó ra ngoài ngay, không đợi token hết hạn 7 ngày."""
    from app.models.user import User

    #  Người dùng thường tự đăng nhập ở một "trình duyệt" khác.
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as khac:
        khac.post("/api/auth/register", json={"email": "bi-khoa@gmail.com", "password": _PW})
        assert khac.get("/api/auth/me").status_code == 200

        uid = db.query(User).filter(User.email == "bi-khoa@gmail.com").one().id
        r = admin_client.patch(f"/api/admin/users/{uid}",
                               json={"status": "suspended", "reason": "spam"})
        assert r.status_code == 200 and r.json()["status"] == "suspended"

        assert khac.get("/api/auth/me").status_code == 401


def test_khong_the_tu_bo_quyen_quan_tri(admin_client, db):
    from app.models.user import User
    uid = db.query(User).filter(User.email == "sep@gmail.com").one().id
    r = admin_client.patch(f"/api/admin/users/{uid}", json={"role": "user"})
    assert r.status_code == 400


def test_moi_thao_tac_ghi_deu_de_lai_audit(admin_client, db):
    from app.models.admin import AuditLog
    from app.models.user import User

    db.add(User(email="muc-tieu@gmail.com", display_name="X", password_hash="x"))
    db.commit()
    uid = db.query(User).filter(User.email == "muc-tieu@gmail.com").one().id

    admin_client.get(f"/api/admin/users/{uid}")                       # xem dữ liệu cá nhân
    admin_client.patch(f"/api/admin/users/{uid}", json={"status": "suspended"})
    admin_client.post(f"/api/admin/users/{uid}/revoke-sessions")

    actions = [row.action for row in db.query(AuditLog).order_by(AuditLog.id).all()]
    assert actions == ["view_user_data", "update_user", "revoke_sessions"]
    #  Ghi cả trước/sau để còn đối chiếu khi có tranh chấp.
    doi = db.query(AuditLog).filter(AuditLog.action == "update_user").one()
    assert doi.before["status"] == "active" and doi.after["status"] == "suspended"


# ── Cần gạt khẩn cấp ─────────────────────────────────────────────────────────

def test_gat_tat_tro_ly_co_hieu_luc_ngay(admin_client, db):
    """Tiêu chí nghiệm thu S2: tắt trợ lý trong /admin, không cần deploy lại."""
    from app.core import settings_store

    r = admin_client.put("/api/admin/settings",
                         json={"values": {"assistant_enabled": False}, "reason": "bị lạm dụng"})
    assert r.status_code == 200
    assert settings_store.flag("assistant_enabled") is False

    hoi = admin_client.post("/api/chat", json={"question": "FPT thế nào?"})
    assert hoi.status_code == 503
    assert "tạm nghỉ" in hoi.json()["detail"].lower()

    #  Gạt lại thì dùng được ngay (không còn 503 vì cờ).
    admin_client.put("/api/admin/settings", json={"values": {"assistant_enabled": True}})
    assert settings_store.flag("assistant_enabled") is True


def test_gat_dong_dang_ky(admin_client):
    from fastapi.testclient import TestClient

    from app.main import app

    admin_client.put("/api/admin/settings", json={"values": {"registration_open": False}})
    #  Dùng "trình duyệt" riêng để không đụng vào phiên quản trị đang mở.
    with TestClient(app) as khach:
        r = khach.post("/api/auth/register", json={"email": "moi@gmail.com", "password": _PW})
        assert r.status_code == 503
    admin_client.put("/api/admin/settings", json={"values": {"registration_open": True}})


def test_doi_han_muc_trong_admin_co_hieu_luc(admin_client):
    from app.core import settings_store
    admin_client.put("/api/admin/settings", json={"values": {"rag_daily_quota": 2}})
    assert settings_store.quota("rag_daily_quota") == 2
    admin_client.put("/api/admin/settings", json={"values": {"rag_daily_quota": 5}})


def test_khoa_cau_hinh_la_khong_ghi_duoc(admin_client):
    r = admin_client.put("/api/admin/settings", json={"values": {"jwt_secret": "hack"}})
    assert r.status_code == 400


# ── Xác thực 2 lớp ───────────────────────────────────────────────────────────

def test_bat_buoc_2_lop_chan_admin_chua_bat(admin_client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "admin_require_2fa", True)

    assert admin_client.get("/api/admin/overview").status_code == 403
    #  Nhưng đúng hai đường để BẬT 2 lớp thì vẫn vào được, nếu không là tự nhốt mình.
    assert admin_client.post("/api/admin/2fa/setup").status_code == 200


def test_bat_2_lop_roi_dang_nhap_phai_co_ma(admin_client, db, monkeypatch):
    import pyotp

    from app.models.user import User

    setup = admin_client.post("/api/admin/2fa/setup").json()
    ma = pyotp.TOTP(setup["secret"]).now()
    assert admin_client.post(f"/api/admin/2fa/enable?code={ma}").status_code == 204

    db.expire_all()
    assert db.query(User).filter(User.email == "sep@gmail.com").one().totp_secret

    admin_client.cookies.clear()
    thieu = admin_client.post("/api/auth/login",
                              json={"email": "sep@gmail.com", "password": _PW})
    assert thieu.status_code == 401 and "6 số" in thieu.json()["detail"]

    du = admin_client.post("/api/auth/login", json={
        "email": "sep@gmail.com", "password": _PW,
        "totp_code": pyotp.TOTP(setup["secret"]).now()})
    assert du.status_code == 200


def test_403_thieu_2_lop_co_header_danh_dau(admin_client, monkeypatch):
    """Giao diện phải PHÂN BIỆT được "chưa bật 2 lớp" với "không có quyền":
    cái đầu tự sửa được nên đưa thẳng người dùng tới trang bật, cái sau thì không."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "admin_require_2fa", True)

    r = admin_client.get("/api/admin/overview")
    assert r.status_code == 403
    assert r.headers.get("x-admin-setup") == "totp"


def test_me_bao_da_bat_2_lop_chua(admin_client, db):
    import pyotp

    assert admin_client.get("/api/auth/me").json()["totp_enabled"] is False

    setup = admin_client.post("/api/admin/2fa/setup").json()
    admin_client.post(f"/api/admin/2fa/enable?code={pyotp.TOTP(setup['secret']).now()}")

    #  Bật xong phiên cũ chết (token_version tăng) → đăng nhập lại rồi mới hỏi.
    admin_client.cookies.clear()
    admin_client.post("/api/auth/login", json={
        "email": "sep@gmail.com", "password": _PW,
        "totp_code": pyotp.TOTP(setup["secret"]).now()})
    assert admin_client.get("/api/auth/me").json()["totp_enabled"] is True
