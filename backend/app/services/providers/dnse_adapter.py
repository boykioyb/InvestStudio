"""Provider khối KỸ THUẬT/GIÁ — ADAPTER MỎNG trên `dnse`.

Cùng chữ ký với `vci_adapter` (trả về Candle/TechnicalData) để tầng trên xếp ưu
tiên mà không phải biết nguồn. DNSE được ưu tiên vì nến ngày sâu ~10 năm (2 chu
kỳ) trong một request — xem `providers/quotes.py`.

CỐ Ý không có `fetch_fundamentals`: chỉ số cơ bản của DNSE (`financial-index`) trả
tăng trưởng LN sai thước đo (TTM/quý, có mã ngược dấu vs YoY năm) nên khối cơ bản
vẫn do VCI đảm nhiệm — xem docstring `analyzer.py`.
"""
from __future__ import annotations

from app.services.providers import dnse
from app.services.providers.base import (
    Candle,
    ProviderError,
    TechnicalData,
    build_technical,
)
from app.services.providers.dnse import DnseError

_PRICE_LOOKBACK_DAYS = 180


def fetch_technical(ticker: str) -> TechnicalData:
    #  Khối kỹ thuật: lấy OHLCV thẳng từ DNSE (đã ở nghìn đồng, không chia).
    try:
        candles = dnse.ohlcv(ticker, _PRICE_LOOKBACK_DAYS)
    except DnseError as exc:
        raise ProviderError(f"DNSE không trả giá cho {ticker}: {exc}") from exc

    if not candles:
        raise ProviderError(f"Không có dữ liệu giá cho {ticker}")

    closes = [c["close"] for c in candles if c["close"] is not None]
    volumes = [c["volume"] for c in candles]
    return build_technical(closes, volumes, candles[-1]["date"])


def fetch_ohlcv(ticker: str, days: int) -> list[Candle]:
    """Lịch sử nến ngày trong `days` gần nhất (DNSE hỗ trợ khung dài, tới ~10 năm)."""
    try:
        rows = dnse.ohlcv(ticker, days)
    except DnseError as exc:
        raise ProviderError(f"DNSE không trả lịch sử giá cho {ticker}: {exc}") from exc

    if not rows:
        raise ProviderError(f"Không có lịch sử giá cho {ticker}")

    return [
        Candle(date=r["date"], open=r["open"], high=r["high"],
               low=r["low"], close=r["close"], volume=r["volume"])
        for r in rows
        if None not in (r["open"], r["high"], r["low"], r["close"])
    ]
