"""Test tổng quan danh mục: số học lãi/lỗ và cách xử lý khi thiếu giá.

Không gọi mạng — `vci_direct` được monkeypatch. Thứ cần khóa ở đây là: cộng đúng,
và khi nguồn không trả giá thì vẫn hiện được vốn/số lượng thay vì trắng bảng.
"""
from __future__ import annotations

import pytest

from app.schemas.stock import PortfolioHolding, PortfolioLot, PortfolioRequest
from app.services import portfolio


def _yeu_cau(account=None):
    return PortfolioRequest(
        holdings=[
            PortfolioHolding(ticker="fpt", lots=[PortfolioLot(price=100.0, quantity=100),
                                                 PortfolioLot(price=120.0, quantity=100)]),
            PortfolioHolding(ticker="VCB", lots=[PortfolioLot(price=60.0, quantity=200)]),
        ],
        account_value=account,
    )


@pytest.fixture
def gia_gia(monkeypatch):
    """Bảng giá giả: FPT khớp 130, VCB chưa khớp nên chỉ có giá tham chiếu 50."""
    from app.services.providers import vci_direct
    monkeypatch.setattr(vci_direct, "price_board", lambda codes: [
        {"symbol": "FPT", "match_price": 130_000, "ref_price": 125_000},
        {"symbol": "VCB", "match_price": 0, "ref_price": 50_000},
    ])
    monkeypatch.setattr(vci_direct, "symbol_directory", lambda: {"FPT": {"name": "FPT Corp"}})


def test_cong_dung_von_va_lai_lo(gia_gia):
    kq = portfolio.review(_yeu_cau())

    fpt = next(r for r in kq.rows if r.ticker == "FPT")
    assert fpt.quantity == 200
    assert fpt.avg_cost == 110.0                    # (100×100 + 120×100) / 200
    assert fpt.total_cost == 22_000.0
    assert fpt.current_price == 130.0               # 130.000đ → 130 nghìn đ
    assert fpt.market_value == 26_000.0
    assert fpt.pnl == 4_000.0
    assert fpt.name == "FPT Corp"

    vcb = next(r for r in kq.rows if r.ticker == "VCB")
    assert vcb.price_is_ref is True                 # chưa khớp lệnh → là giá tham chiếu
    assert vcb.pnl == -2_000.0                      # (50 − 60) × 200

    assert kq.totals.total_cost == 34_000.0
    assert kq.totals.market_value == 36_000.0
    assert kq.totals.pnl == 2_000.0
    assert (kq.totals.winners, kq.totals.losers) == (1, 1)


def test_ty_trong_chi_tinh_khi_biet_quy_mo_tai_khoan(gia_gia):
    khong_khai = portfolio.review(_yeu_cau())
    assert all(r.weight_pct is None for r in khong_khai.rows)

    co_khai = portfolio.review(_yeu_cau(account=100_000.0))
    fpt = next(r for r in co_khai.rows if r.ticker == "FPT")
    assert fpt.weight_pct == 26.0                   # 26.000 / 100.000


def test_nguon_hong_van_giu_duoc_von_va_so_luong(monkeypatch):
    """Mất giá thị trường thì lãi/lỗ để TRỐNG, không được suy ra số bừa."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    def _hong(_codes):
        raise VciError("nguồn sập")

    monkeypatch.setattr(vci_direct, "price_board", _hong)
    monkeypatch.setattr(vci_direct, "symbol_directory", lambda: {})

    kq = portfolio.review(_yeu_cau())
    assert kq.errors and kq.errors[0].ticker == "*"
    assert kq.totals.total_cost == 34_000.0         # vốn vẫn tính được từ đợt mua
    assert all(r.current_price is None and r.pnl is None for r in kq.rows)
