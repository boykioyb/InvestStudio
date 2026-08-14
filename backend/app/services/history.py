"""Lịch sử giá theo khung thời gian, cho biểu đồ 1 tháng / 1 quý / 1 năm / 3 năm.

Tách khỏi `analyzer.py` vì đây là dữ liệu để NGƯỜI DÙNG tự nhìn và đối chiếu,
không tham gia vào việc chấm điểm. Bộ chấm điểm vẫn dùng cửa sổ 180 ngày cố định
để mọi mã được so trên cùng một thước.
"""
from __future__ import annotations

from app.schemas.stock import HistoryStats, PriceHistory, PricePoint, RangeKey
from app.services.providers import vci_adapter
from app.services.providers.base import Candle, ProviderError

#  Số ngày LỊCH (không phải số phiên) cần lùi lại cho mỗi khung.
#  Dùng chung với market.py để mọi tab hiểu khung thời gian giống nhau.
RANGES: dict[str, tuple[int, str]] = {
    "1m": (30, "Một tháng"),
    "3m": (92, "Một quý"),
    "1y": (365, "Một năm"),
    "3y": (1095, "Ba năm"),
}


def _stats(candles: list[Candle]) -> HistoryStats:
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    first, last = closes[0], closes[-1]
    return HistoryStats(
        sessions=len(candles),
        low=round(min(c.low for c in candles), 2),
        high=round(max(c.high for c in candles), 2),
        first=round(first, 2),
        last=round(last, 2),
        change_pct=round((last - first) / first * 100, 2) if first else 0.0,
        avg_volume=round(sum(volumes) / len(volumes) / 1_000_000, 2),
    )


def fetch_history(ticker: str, range_key: RangeKey) -> PriceHistory:
    """Lấy nến ngày cho một khung thời gian. Raise ProviderError nếu không có dữ liệu."""
    ticker = ticker.upper().strip()
    days, label = RANGES[range_key]

    #  Chỉ vnstock nhận khoảng ngày tùy ý; CafeF phân trang 20 dòng/lần nên
    #  không thực tế cho khung dài — vì vậy khung thời gian chỉ dựa vào vnstock.
    candles = vci_adapter.fetch_ohlcv(ticker, days)
    if not candles:
        raise ProviderError(f"Không có dữ liệu giá cho {ticker} trong khung {label.lower()}.")

    return PriceHistory(
        ticker=ticker,
        range=range_key,
        label=label,
        source="VCI",
        points=[
            PricePoint(d=c.date, o=round(c.open, 2), h=round(c.high, 2),
                       l=round(c.low, 2), c=round(c.close, 2), v=c.volume)
            for c in candles
        ],
        stats=_stats(candles),
    )
