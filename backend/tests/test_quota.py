"""Test các rào chống lạm dụng hạn mức (S0).

Không cần Redis: phần đếm được monkeypatch, phần thuần logic test trực tiếp.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _req(peer: str, xff: str | None = None):
    """Request giả — `_client_ip` chỉ chạm tới `.client.host` và `.headers`."""
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)


def _settings(**kw):
    base = {"trusted_proxies": [], "trusted_proxy_hops": 1}
    base.update(kw)
    return SimpleNamespace(**base)


# ── IP thật sau proxy ────────────────────────────────────────────────────────

def test_xff_bi_lo_di_khi_nguoi_goi_khong_phai_proxy_tin_cay(monkeypatch):
    """Header client tự ghi KHÔNG được đổi được danh tính — đây là lỗ H4."""
    from app.core import ratelimit
    monkeypatch.setattr(ratelimit, "get_settings", lambda: _settings())
    #  Kẻ tấn công tự khai một IP khác để mỗi request là một "người" mới.
    assert ratelimit.client_ip(_req("9.9.9.9", "1.1.1.1")) == "9.9.9.9"


def test_lay_hop_cuoi_khi_qua_proxy_tin_cay(monkeypatch):
    """Hop CUỐI là phần proxy của mình ghi; hop đầu là phần client tự khai."""
    from app.core import ratelimit
    monkeypatch.setattr(ratelimit, "get_settings",
                        lambda: _settings(trusted_proxies=["10.0.0.5"]))
    ip = ratelimit.client_ip(_req("10.0.0.5", "1.1.1.1, 203.0.113.7"))
    assert ip == "203.0.113.7"


def test_khong_co_xff_thi_dung_ip_ket_noi(monkeypatch):
    from app.core import ratelimit
    monkeypatch.setattr(ratelimit, "get_settings",
                        lambda: _settings(trusted_proxies=["10.0.0.5"]))
    assert ratelimit.client_ip(_req("10.0.0.5")) == "10.0.0.5"


# ── Khóa cache không bị phá bằng số lẻ ───────────────────────────────────────

def test_cache_key_lam_tron_pe_va_pb():
    """`?pe_sec=9.001` rồi `9.002`… từng là cách phá cache mà không cần refresh."""
    from app.api.routes.stocks import _cache_key
    a = _cache_key("FPT", 1, 1, 1, 9.001, 2.001, "auto")
    b = _cache_key("FPT", 1, 1, 1, 9.004, 2.003, "auto")
    assert a == b
    #  Khác biệt THẬT thì vẫn là hai khóa khác nhau.
    assert a != _cache_key("FPT", 1, 1, 1, 9.5, 2.0, "auto")


def test_cache_key_giu_nguyen_none():
    from app.api.routes.stocks import _cache_key
    assert _cache_key("FPT", 1, 1, 1, None, None, "auto")[4:6] == (None, None)


# ── refresh chỉ dành cho thành viên ──────────────────────────────────────────

@pytest.mark.parametrize("refresh,user,mong_doi", [
    (True, None, False),                      # khách → bỏ qua, không báo lỗi
    (True, SimpleNamespace(id=1), True),      # thành viên → được ép crawl
    (False, SimpleNamespace(id=1), False),
])
def test_may_refresh(refresh, user, mong_doi):
    from app.api.routes.stocks import _may_refresh
    assert _may_refresh(refresh, user) is mong_doi


# ── Hạ cấp mềm theo ngân sách Gemini ─────────────────────────────────────────

@pytest.mark.parametrize("da_dung,level,dung_agent", [
    (0, "ok", True),
    (699, "ok", True),
    (700, "saving", False),      # ≥70% → tắt agent, lui về RAG một nhịp
    (950, "exhausted", False),   # ≥90% → không nhận người hỏi mới
])
def test_muc_ha_cap(monkeypatch, da_dung, level, dung_agent):
    from app.core import budget
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_daily_call_cap", 1000)
    monkeypatch.setattr(budget, "used_today", lambda: da_dung)

    assert budget.status_snapshot()["level"] == level
    assert budget.should_use_agent() is dung_agent
    assert budget.new_questions_blocked() is (level == "exhausted")


def test_redis_hong_thi_coi_nhu_can_quota(monkeypatch):
    """FAIL-CLOSED: không đọc được bộ đếm thì phải cho là đã cạn, không phải còn."""
    from app.core import budget

    class _Vo:
        def get(self, *_a, **_k):
            raise RuntimeError("redis down")

    monkeypatch.setattr(budget, "redis_client", lambda: _Vo())
    assert budget.used_today() == budget.get_settings().gemini_daily_call_cap
    assert budget.should_use_agent() is False


# ── Việc tiêu hạn mức chung chỉ dành cho quản trị ────────────────────────────

def test_reindex_tu_choi_user_thuong(client):
    """H3: trước đây ai đăng nhập cũng bấm được nút nhúng cả rổ VN30."""
    reg = client.post("/api/auth/register",
                      json={"email": "u@example.com", "password": "matkhau-dai-hon"})
    assert reg.status_code == 201, reg.text
    r = client.post("/api/chat/reindex")
    assert r.status_code == 403
    assert "quản trị" in r.json()["detail"].lower()


def test_reindex_tu_choi_khach_chua_dang_nhap(client):
    assert client.post("/api/chat/reindex").status_code == 401


# ── Tin proxy theo DẢI mạng (IP container Docker là động) ────────────────────

def test_trusted_proxy_theo_dai_cidr(monkeypatch):
    from app.core import ratelimit
    monkeypatch.setattr(ratelimit, "get_settings",
                        lambda: _settings(trusted_proxies=["172.16.0.0/12"]))
    #  Từ trong mạng nội bộ Docker → tin header proxy ghi.
    req = SimpleNamespace(client=SimpleNamespace(host="172.18.0.4"),
                          headers={"x-real-ip": "203.0.113.9",
                                   "x-forwarded-for": "1.1.1.1"})
    assert ratelimit.client_ip(req) == "203.0.113.9"
    #  Gọi thẳng từ ngoài vào cổng API → header bịa bị lờ đi.
    outside = SimpleNamespace(client=SimpleNamespace(host="203.0.113.50"),
                              headers={"x-real-ip": "9.9.9.9"})
    assert ratelimit.client_ip(outside) == "203.0.113.50"


# ── Hạn mức theo THIẾT BỊ (đăng ký email mới không nhân được lượt) ───────────

def test_ua_family_gom_theo_dong_trinh_duyet():
    """Dùng nguyên chuỗi UA thì Chrome tự cập nhật là hạn mức tự reset."""
    from app.core.fingerprint import _ua_family
    cu = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
    moi = cu.replace("130.0.0.0", "131.0.6778.86")
    assert _ua_family(cu) == _ua_family(moi) == "chrome:mac"
    assert _ua_family("Mozilla/5.0 (iPhone) ... Firefox/120") == "firefox:iphone"


def test_subnet_gom_theo_dai_24():
    from app.core.fingerprint import subnet_of
    assert subnet_of("203.0.113.7") == subnet_of("203.0.113.200") == "203.0.113.0/24"
    assert subnet_of("203.0.114.7") != subnet_of("203.0.113.7")


def test_nhieu_ro_lay_ro_nghiem_ngat_nhat(monkeypatch):
    """Rổ nào chạm trần cũng chặn, và KHÔNG trừ lượt của các rổ còn lại."""
    from fastapi import HTTPException

    from app.core import ratelimit

    da_dung = {"rag": 0, "rag:device": 5}
    da_tang: list[str] = []
    monkeypatch.setattr(ratelimit, "used_today", lambda scope, subject: da_dung.get(scope, 0))
    monkeypatch.setattr(ratelimit, "enforce_daily",
                        lambda subject, scope, limit, **kw: da_tang.append(scope))

    with pytest.raises(HTTPException) as loi:
        ratelimit.enforce_daily_buckets([("rag", "1", 5), ("rag:device", "abc", 5)])
    assert loi.value.status_code == 429
    assert "thiết bị" in loi.value.detail.lower()
    assert da_tang == []          # bị chặn thì không rổ nào bị trừ oan


def test_nhieu_ro_con_cho_thi_tang_het(monkeypatch):
    from app.core import ratelimit
    da_tang: list[str] = []
    monkeypatch.setattr(ratelimit, "used_today", lambda scope, subject: 0)
    monkeypatch.setattr(ratelimit, "enforce_daily",
                        lambda subject, scope, limit, **kw: da_tang.append(scope))
    ratelimit.enforce_daily_buckets([("rag", "1", 5), ("rag:device", "abc", 5)])
    assert da_tang == ["rag", "rag:device"]


def test_qua_nhieu_tai_khoan_tren_mot_thiet_bi_thi_chan_dang_ky(client, monkeypatch):
    """Thang leo thang: máy đã nuôi đủ N tài khoản thì không tạo thêm được."""
    from app.core import fingerprint
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_accounts_per_device", 2)
    for i in range(2):
        r = client.post("/api/auth/register",
                        json={"email": f"nguoi{i}@example.com", "password": "matkhau-dai-hon"})
        assert r.status_code == 201, r.text

    chan = client.post("/api/auth/register",
                       json={"email": "nguoi9@example.com", "password": "matkhau-dai-hon"})
    assert chan.status_code == 429
    assert "thiết bị này" in chan.json()["detail"].lower()
    assert fingerprint.accounts_on_device is not None


def test_upload_tu_choi_tep_gia_dang_anh(client):
    """Đổi Content-Type là nhét được tệp bất kỳ — phải kiểm byte đầu tệp."""
    r = client.post("/api/auth/register",
                    json={"email": "up@example.com", "password": "matkhau-dai-hon"})
    assert r.status_code == 201

    #  Nội dung không phải định dạng nào được phép.
    la = client.post("/api/chat/upload",
                     files={"file": ("hack.png", b"<html>xin chao</html>", "image/png")})
    assert la.status_code == 415
    assert "không nhận dạng" in la.json()["detail"].lower()

    #  Nội dung LÀ PDF thật nhưng khai là ảnh → vẫn chặn (khai sai định dạng).
    lech = client.post("/api/chat/upload",
                       files={"file": ("x.png", b"%PDF-1.4 noi dung", "image/png")})
    assert lech.status_code == 415
    assert "không khớp" in lech.json()["detail"].lower()

    #  Ảnh PNG thật thì qua.
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    ok = client.post("/api/chat/upload", files={"file": ("that.png", png, "image/png")})
    assert ok.status_code == 200, ok.text
