"""Khóa hành vi của khối điểm nhấn trang chủ (`/api/market/highlights`).

Không chạm mạng: nạp sẵn dữ liệu thô vào cache của service rồi kiểm tra phần
BIẾN ĐỔI — lọc theo rổ, lọc sự kiện đã qua, phân loại mức độ, và ngân sách
request của bảng điểm (thứ dễ vỡ nhất vì nguồn chỉ cho ~20 req/phút).
"""
from __future__ import annotations

import time

import pytest

from app.services import highlights


@pytest.fixture(autouse=True)
def _clear_cache():
    """Mỗi test chạy trên cache trắng — không thừa hưởng dữ liệu của test trước."""
    highlights._cache.clear()
    yield
    highlights._cache.clear()


def _seed(key: str, value) -> None:
    highlights._cache[key] = (time.monotonic(), value)


# ── Phân loại mức độ ────────────────────────────────────────────────────────
@pytest.mark.parametrize("name, kind, level", [
    ("Trả cổ tức bằng tiền mặt", "Cổ tức tiền", "good"),
    ("Trả cổ tức bằng cổ phiếu", "Cổ tức cổ phiếu", "good"),
    ("Thưởng cổ phiếu", "Thưởng cổ phiếu", "good"),
    ("Họp ĐHCĐ bất thường", "ĐHCĐ bất thường", "warn"),
    ("Phát hành thêm cổ phiếu", "Phát hành thêm", "warn"),
    ("Lấy ý kiến CĐ bằng văn bản", "Lấy ý kiến cổ đông", "warn"),
    ("Hủy niêm yết", "Cảnh báo", "bad"),
])
def test_phan_loai_su_kien_theo_dung_quy_uoc(name: str, kind: str, level: str) -> None:
    """Phân loại nằm ở BACKEND — frontend chỉ tô màu theo nhãn này."""
    assert highlights._classify(name) == (kind, level)


def test_su_kien_la_khong_duoc_to_xanh() -> None:
    """Loại sự kiện chưa có luật nghĩa là NÊN ĐỌC, không phải mặc định tốt."""
    kind, level = highlights._classify("Sự kiện nguồn mới đặt tên khác")
    assert level == "warn"
    assert kind == "Sự kiện nguồn mới đặt tên khác"  # giữ nguyên chữ của nguồn


# ── Sự kiện sắp tới ─────────────────────────────────────────────────────────
def _action(symbol: str, name: str, exright: str) -> dict:
    return {"symbol": symbol, "name": name, "title": f"{name} của {symbol}",
            "exright_date": exright, "record_date": "", "action_date": "", "url": ""}


def test_chi_giu_su_kien_sap_toi_cua_ma_trong_ro() -> None:
    today = highlights._today()
    _seed("events:all", [
        _action("FPT", "Trả cổ tức bằng tiền mặt", "2099-01-02"),
        _action("VNM", "Họp ĐHCĐ bất thường", "2099-01-01"),
        _action("ZZZ", "Trả cổ tức bằng tiền mặt", "2099-01-01"),  # ngoài rổ
        _action("FPT", "Trả cổ tức bằng tiền mặt", "2000-01-01"),  # đã qua
        _action("FPT", "Trả cổ tức bằng tiền mặt", today),         # hôm nay vẫn tính
    ])

    items = highlights._events(["FPT", "VNM"], limit=10)

    assert [(i.symbol, i.date) for i in items] == [
        ("FPT", today), ("VNM", "2099-01-01"), ("FPT", "2099-01-02"),
    ]  # gần nhất trước, mã ngoài rổ và sự kiện đã qua bị loại


def test_su_kien_khong_co_ngay_thi_bo_thay_vi_hien_o_trong() -> None:
    _seed("events:all", [_action("FPT", "Trả cổ tức bằng tiền mặt", "")])
    assert highlights._events(["FPT"], limit=5) == []


def test_su_kien_ton_trong_limit() -> None:
    _seed("events:all", [_action("FPT", "Trả cổ tức bằng tiền mặt", f"2099-01-0{i}")
                         for i in range(1, 6)])
    assert len(highlights._events(["FPT"], limit=2)) == 2


def test_nguon_loi_thi_su_kien_rong_chu_khong_no() -> None:
    """Rỗng > bịa: trang chủ đã có trạng thái trống."""
    _seed("events:all", [])
    assert highlights._events(["FPT"], limit=5) == []


# ── Tin mới ─────────────────────────────────────────────────────────────────
def test_tin_gan_ve_ma_thuoc_ro_du_ma_chinh_nam_ngoai_ro() -> None:
    """Tin ngành hay gắn mã chính là mã nhỏ ngoài rổ — phải quy về mã trong rổ."""
    _seed("news:VN30", [
        {"title": "Tin ngành", "date": "2026-09-06", "link": "https://a",
         "symbol": "ZZZ", "symbols": ["ZZZ", "FPT"]},
    ])
    items = highlights._news("VN30", ["FPT", "VNM"], limit=5)
    assert [(i.symbol, i.url) for i in items] == [("FPT", "https://a")]


def test_tin_khong_lien_quan_ro_nao_thi_bo() -> None:
    _seed("news:VN30", [{"title": "Tin mã khác", "date": "2026-09-06", "link": "",
                         "symbol": "ZZZ", "symbols": ["ZZZ"]}])
    assert highlights._news("VN30", ["FPT"], limit=5) == []


def test_tin_thieu_link_thi_url_la_none_khong_phai_chuoi_rong() -> None:
    _seed("news:VN30", [{"title": "Không có link", "date": "2026-09-06", "link": "",
                         "symbol": "FPT", "symbols": ["FPT"]}])
    assert highlights._news("VN30", ["FPT"], limit=5)[0].url is None


def test_tin_moi_nhat_len_dau_va_loc_trung_tieu_de() -> None:
    _seed("news:VN30", [
        {"title": "Tin cũ", "date": "2026-09-01", "link": "", "symbol": "FPT", "symbols": []},
        {"title": "Tin mới", "date": "2026-09-06", "link": "", "symbol": "FPT", "symbols": []},
        {"title": "Tin mới", "date": "2026-09-05", "link": "", "symbol": "FPT", "symbols": []},
    ])
    items = highlights._news("VN30", ["FPT"], limit=5)
    assert [i.title for i in items] == ["Tin mới", "Tin cũ"]


# ── Bảng điểm ───────────────────────────────────────────────────────────────
class _FakeAnalysis:
    def __init__(self, total: int) -> None:
        self.score = type("S", (), {"total": total})()


def test_bang_diem_sap_theo_diem_giam_va_ton_trong_limit() -> None:
    for symbol, total in (("AAA", 60), ("BBB", 90), ("CCC", 75)):
        _seed(f"score:{symbol}", total)

    rows = highlights._leaders(["AAA", "BBB", "CCC"], limit=2)
    assert [(r.symbol, r.score) for r in rows] == [("BBB", 90), ("CCC", 75)]


def test_moi_lan_goi_chi_cham_them_toi_da_hai_ma() -> None:
    """Ràng buộc SỐNG CÒN: mỗi mã ≈ 4 request VCI, hạn mức nguồn ~20 req/phút.

    Cache lạnh mà chấm cả rổ là bắn 100+ request và treo endpoint.
    """
    calls: list[str] = []

    def fake_analyze(symbol: str, **_):
        calls.append(symbol)
        return _FakeAnalysis(50)

    original = highlights.analyzer.analyze
    highlights.analyzer.analyze = fake_analyze  # type: ignore[assignment]
    try:
        rows = highlights._leaders(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"], limit=10)
    finally:
        highlights.analyzer.analyze = original  # type: ignore[assignment]

    assert len(calls) == highlights._LEADERS_PER_CALL
    assert len(rows) == highlights._LEADERS_PER_CALL  # bảng đầy dần ở các lần gọi sau


def test_ma_loi_nguon_bi_bo_qua_chu_khong_lam_sap_bang_diem() -> None:
    def fake_analyze(symbol: str, **_):
        raise RuntimeError("nguồn lỗi")

    original = highlights.analyzer.analyze
    highlights.analyzer.analyze = fake_analyze  # type: ignore[assignment]
    try:
        _seed("score:AAA", 70)
        rows = highlights._leaders(["AAA", "BBB"], limit=5)
    finally:
        highlights.analyzer.analyze = original  # type: ignore[assignment]

    assert [(r.symbol, r.score) for r in rows] == [("AAA", 70)]


def test_diem_da_cham_khong_bi_cham_lai_trong_han_cache() -> None:
    def boom(symbol: str, **_):
        raise AssertionError(f"không được gọi lại nguồn cho {symbol}")

    for symbol in ("AAA", "BBB"):
        _seed(f"score:{symbol}", 80)

    original = highlights.analyzer.analyze
    highlights.analyzer.analyze = boom  # type: ignore[assignment]
    try:
        assert len(highlights._leaders(["AAA", "BBB"], limit=5)) == 2
    finally:
        highlights.analyzer.analyze = original  # type: ignore[assignment]
