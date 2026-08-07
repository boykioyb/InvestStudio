"""Khóa hành vi sắp xếp của danh sách mã.

Không chạm mạng: chỉ kiểm tra hàm sắp xếp và hàm dựng dòng.
"""
from __future__ import annotations

from app.schemas.stock import ScreenerRow
from app.services import screener


def _row(symbol: str, **kwargs) -> ScreenerRow:
    return ScreenerRow(symbol=symbol, name=symbol, **kwargs)


def test_o_trong_luon_xuong_cuoi_du_sap_tang_hay_giam() -> None:
    """None nghĩa là THIẾU dữ liệu — để lẫn vào giữa bảng sẽ bị đọc thành sai số."""
    rows = [_row("AAA", value=None), _row("BBB", value=5.0), _row("CCC", value=1.0)]

    giam = [r.symbol for r in screener.sort_rows(rows, "value", "desc")]
    tang = [r.symbol for r in screener.sort_rows(rows, "value", "asc")]

    assert giam == ["BBB", "CCC", "AAA"]
    assert tang == ["CCC", "BBB", "AAA"]


def test_gia_tri_bang_nhau_van_cho_thu_tu_xac_dinh() -> None:
    """Không được phụ thuộc thứ tự đầu vào (bảng có thể đến từ cache đã sắp khác)."""
    a = [_row("CCC", value=1.0), _row("AAA", value=1.0), _row("BBB", value=1.0)]
    b = list(reversed(a))

    assert [r.symbol for r in screener.sort_rows(a, "value", "desc")] == \
           [r.symbol for r in screener.sort_rows(b, "value", "desc")] == ["AAA", "BBB", "CCC"]


def test_cot_toan_o_trong_van_xep_theo_ma() -> None:
    rows = [_row("VNM"), _row("ACB"), _row("FPT")]
    assert [r.symbol for r in screener.sort_rows(rows, "volume", "desc")] == ["ACB", "FPT", "VNM"]


def test_cot_chu_sap_theo_bang_chu_cai() -> None:
    rows = [_row("VNM"), _row("ACB"), _row("FPT")]
    assert [r.symbol for r in screener.sort_rows(rows, "symbol", "asc")] == ["ACB", "FPT", "VNM"]
    assert [r.symbol for r in screener.sort_rows(rows, "symbol", "desc")] == ["VNM", "FPT", "ACB"]


def test_so_am_sap_dung_thu_tu() -> None:
    """Khối ngoại bán ròng là số âm — phải nhỏ hơn 0, không được coi như thiếu."""
    rows = [_row("AAA", foreign_net=-9.0), _row("BBB", foreign_net=2.0), _row("CCC", foreign_net=0.0)]
    assert [r.symbol for r in screener.sort_rows(rows, "foreign_net", "desc")] == ["BBB", "CCC", "AAA"]


def test_gia_tri_0_cua_nguon_duoc_hieu_la_thieu_du_lieu() -> None:
    """Nguồn dùng 0 để nói 'chưa có số liệu' — không được hiển thị thành giá 0đ."""
    row = screener._row({"symbol": "FPT", "organ_name": "FPT Corp", "exchange": "HSX",
                         "ref_price": 71500, "match_price": 0, "accumulated_volume": 0,
                         "accumulated_value": 0, "listed_share": 1_000_000})
    assert row is not None
    assert row.price == 71.5          # rơi về giá tham chiếu
    assert row.change_pct is None     # chưa khớp thì không có % thay đổi
    assert row.volume is None and row.value is None


def test_moi_cot_deu_sap_xep_duoc() -> None:
    """Khóa sắp xếp công bố ra ngoài phải thật sự dùng được, không có nút chết."""
    rows = [_row("AAA", price=1.0), _row("BBB", price=2.0)]
    for key in screener.SORT_KEYS:
        assert len(screener.sort_rows(rows, key, "desc")) == 2
