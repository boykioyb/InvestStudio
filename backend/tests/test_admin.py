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


# ── Hạng & hạn mức riêng theo tài khoản ─────────────────────────────────────
#
#  Ba tầng: riêng người → theo hạng → mức chung. Cả nhóm test này đi qua
#  `GET /api/chat/quota` (chỉ ĐỌC) chứ không qua `POST /api/chat`: rào hạn mức
#  fail-closed nên môi trường test không có Redis sẽ trả 503 trước khi tới đâu.

def _dang_nhap(client, email: str):
    r = client.post("/api/auth/login", json={"email": email, "password": _PW})
    assert r.status_code == 200, r.text
    return r


def _uid(db, email: str) -> int:
    from app.models.user import User

    return db.query(User).filter(User.email == email).one().id


def _chuan_bi(admin_client, db, email: str = "dan@gmail.com") -> int:
    """Tạo một tài khoản thường rồi trả về đăng nhập quyền quản trị."""
    _thuong(admin_client)                    # đăng ký + đăng nhập tài khoản thường
    uid = _uid(db, email)
    _dang_nhap(admin_client, "sep@gmail.com")
    return uid


def test_han_muc_rieng_co_hieu_luc_voi_dung_tai_khoan_do(admin_client, db):
    uid = _chuan_bi(admin_client, db)
    #  Mức chung đặt KHÁC hẳn 20 để phép so dưới đây có nghĩa.
    admin_client.put("/api/admin/settings", json={"values": {"rag_daily_quota": 3}})

    r = admin_client.patch(f"/api/admin/users/{uid}", json={"chat_daily_quota": 20})
    assert r.status_code == 200, r.text
    assert r.json()["chat_quota_effective"] == 20
    assert r.json()["chat_daily_quota"] == 20

    #  Chính tài khoản đó đăng nhập → thấy 20, không phải 3 của mức chung.
    _dang_nhap(admin_client, "dan@gmail.com")
    q = admin_client.get("/api/chat/quota")
    assert q.status_code == 200, q.text
    assert q.json()["limit"] == 20


def test_xoa_han_muc_rieng_thi_quay_ve_muc_chung(admin_client, db):
    from app.core import settings_store

    uid = _chuan_bi(admin_client, db)
    admin_client.patch(f"/api/admin/users/{uid}", json={"chat_daily_quota": 20})

    #  Gửi null = XÓA hạn mức riêng. Khác hẳn việc không gửi trường đó.
    r = admin_client.patch(f"/api/admin/users/{uid}", json={"chat_daily_quota": None})
    assert r.status_code == 200, r.text
    assert r.json()["chat_daily_quota"] is None
    assert r.json()["chat_quota_effective"] == settings_store.quota("rag_daily_quota")


def test_khong_gui_truong_han_muc_thi_giu_nguyen(admin_client, db):
    """Đổi mỗi trạng thái KHÔNG được lặng lẽ xóa hạn mức đã đặt."""
    uid = _chuan_bi(admin_client, db)
    admin_client.patch(f"/api/admin/users/{uid}", json={"chat_daily_quota": 20})

    r = admin_client.patch(f"/api/admin/users/{uid}", json={"status": "active"})
    assert r.status_code == 200, r.text
    assert r.json()["chat_daily_quota"] == 20


def test_hang_doi_han_muc_va_o_trong_duoc(admin_client, db):
    """Hạng làm mức mặc định, và khóa hạng phải TRẢ VỀ MẶC ĐỊNH được.

    Trước đây `settings_store.set_value` gọi `int(value)` nên gửi null/chuỗi
    rỗng là 400 — không có cách nào bỏ đặt một khóa số.
    """
    from app.core import settings_store

    uid = _chuan_bi(admin_client, db)

    r = admin_client.put("/api/admin/settings", json={"values": {"plan_vip_chat_daily": 50}})
    assert r.status_code == 200, r.text
    r = admin_client.patch(f"/api/admin/users/{uid}", json={"plan": "vip"})
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "vip"
    assert r.json()["chat_quota_effective"] == 50

    #  Để trống ô → xóa giá trị đã lưu → hạn mức rơi về mức chung.
    r = admin_client.put("/api/admin/settings", json={"values": {"plan_vip_chat_daily": None}})
    assert r.status_code == 200, r.text
    assert settings_store.get("plan_vip_chat_daily") is None
    r = admin_client.patch(f"/api/admin/users/{uid}", json={"plan": "vip"})
    assert r.json()["chat_quota_effective"] == settings_store.quota("rag_daily_quota")


def test_hang_khong_hop_le_thi_tu_choi(admin_client, db):
    uid = _chuan_bi(admin_client, db)
    r = admin_client.patch(f"/api/admin/users/{uid}", json={"plan": "bac"})
    assert r.status_code == 400
    assert "hạng" in r.json()["detail"].lower()


def test_doi_han_muc_de_lai_audit(admin_client, db):
    from app.models.admin import AuditLog

    uid = _chuan_bi(admin_client, db)
    admin_client.patch(f"/api/admin/users/{uid}",
                       json={"chat_daily_quota": 7, "plan": "vip",
                             "reason": "khách trả phí"})

    row = (db.query(AuditLog).filter(AuditLog.action == "update_user")
           .order_by(AuditLog.id.desc()).first())
    assert row is not None
    assert row.after["chat_daily_quota"] == 7
    assert row.after["plan"] == "vip"
    assert row.before["chat_daily_quota"] is None


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


# ── S3: các trang vận hành ───────────────────────────────────────────────────

def test_xem_noi_dung_hoi_thoai_luon_ghi_audit(admin_client, db):
    """Đọc dữ liệu riêng tư thì phải để lại vết — bất biến của khu quản trị."""
    from app.models.admin import AuditLog
    from app.models.rag import ChatMessage, Conversation
    from app.models.user import User

    user = db.query(User).filter(User.email == "sep@gmail.com").one()
    conv = Conversation(user_id=user.id, title="Thử", ticker="FPT")
    db.add(conv)
    db.flush()
    db.add(ChatMessage(user_id=user.id, conversation_id=conv.id, ticker="FPT",
                       question="FPT thế nào?", answer="Câu trả lời mẫu."))
    db.commit()

    r = admin_client.get(f"/api/admin/conversations/{conv.id}/messages")
    assert r.status_code == 200
    assert r.json()[0]["question"] == "FPT thế nào?"

    vet = db.query(AuditLog).filter(AuditLog.action == "view_user_data",
                                    AuditLog.target_type == "conversation").all()
    assert len(vet) == 1 and vet[0].target_id == str(conv.id)


def test_tim_toan_van_tra_ve_doan_khop(admin_client, db):
    from app.models.rag import ChatMessage
    from app.models.user import User

    user = db.query(User).filter(User.email == "sep@gmail.com").one()
    db.add(ChatMessage(user_id=user.id, question="Cổ tức VCB năm nay ra sao?",
                       answer="VCB chia cổ tức bằng cổ phiếu."))
    db.commit()

    hits = admin_client.get("/api/admin/chat/search?q=cổ tức").json()
    assert hits and "cổ tức" in hits[0]["snippet"].lower()
    assert hits[0]["user_email"] == "sep@gmail.com"


def test_chan_thiet_bi_thi_thiet_bi_do_khong_dung_duoc_nua(admin_client, db):
    from app.core import fingerprint
    from app.models.device import DeviceFingerprint

    db.add(DeviceFingerprint(fp_hash="a" * 64))
    db.commit()

    r = admin_client.post("/api/admin/devices/" + "a" * 64 + "/block",
                          json={"reason": "tạo tài khoản hàng loạt"})
    assert r.status_code == 204

    bi_chan, ly_do = fingerprint.is_blocked(db, "a" * 64)
    assert bi_chan and "hàng loạt" in ly_do

    assert admin_client.post("/api/admin/devices/" + "a" * 64 + "/unblock").status_code == 204
    assert fingerprint.is_blocked(db, "a" * 64)[0] is False


def test_thong_bao_he_thong_chi_gui_cho_tai_khoan_da_xac_minh(admin_client, db):
    from app.models.user import Notification, User

    db.add(User(email="chua-xac-minh@gmail.com", display_name="X", password_hash="x"))
    db.commit()

    kq = admin_client.post("/api/admin/broadcast",
                           json={"message": "Bảo trì 22:00 hôm nay.", "only_verified": True})
    assert kq.status_code == 200
    #  Chỉ tài khoản admin (đã xác minh trong fixture) nhận được.
    nhan = db.query(Notification).all()
    assert kq.json()["sent"] == len(nhan)
    assert all(n.kind == "system" for n in nhan)


def test_bao_cao_cache_noi_ro_gioi_han(admin_client):
    """Con số cache chỉ đúng cho MỘT tiến trình — phải nói ra, không để hiểu nhầm."""
    r = admin_client.get("/api/admin/cache").json()
    assert len(r["caches"]) == 3
    assert "tiến trình" in r["note"]
