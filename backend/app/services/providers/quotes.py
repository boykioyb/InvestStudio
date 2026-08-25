"""Facade LỊCH SỬ GIÁ — một điểm vào duy nhất, xếp ưu tiên nguồn.

Thứ tự: **DNSE trước** (nến ngày sâu ~10 năm, đủ 2 chu kỳ để đánh giá) → VCI dự
phòng. Nhờ facade này, mọi tầng đọc lịch sử giá (history/alerts/market) chỉ gọi
một chỗ; đổi thứ tự ưu tiên về sau chỉ sửa ở đây.

Hai adapter trả cùng kiểu Candle nên hoán đổi trong suốt với tầng trên. Nguồn đầu
lỗi (ProviderError) thì tự lùi sang nguồn sau.
"""
from __future__ import annotations

from app.services.providers import dnse_adapter, vci_adapter
from app.services.providers.base import Candle, ProviderError

#  Xếp theo ưu tiên: DNSE hàng đầu, VCI dự phòng. (tên nguồn, hàm lấy nến)
_OHLCV = (("DNSE", dnse_adapter.fetch_ohlcv), ("VCI", vci_adapter.fetch_ohlcv))


def fetch_ohlcv_sourced(ticker: str, days: int) -> tuple[str, list[Candle]]:
    """(tên nguồn đã dùng, nến ngày) — thử lần lượt theo ưu tiên tới khi có dữ liệu."""
    last: ProviderError | None = None
    for name, fetch in _OHLCV:
        try:
            return name, fetch(ticker, days)
        except ProviderError as exc:
            last = exc
    raise last or ProviderError(f"Không có lịch sử giá cho {ticker}")


def fetch_ohlcv(ticker: str, days: int) -> list[Candle]:
    """Lịch sử nến ngày `days` gần nhất — DNSE trước (khung dài), VCI dự phòng."""
    return fetch_ohlcv_sourced(ticker, days)[1]
