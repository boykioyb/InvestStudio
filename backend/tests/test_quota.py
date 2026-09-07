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
                      json={"email": "u@example.com", "password": "secret123"})
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
