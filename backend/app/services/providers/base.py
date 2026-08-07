"""Kiểu dữ liệu chung + các chỉ báo kỹ thuật dùng lại giữa mọi provider."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class ProviderError(RuntimeError):
    """Provider không lấy được dữ liệu (mạng lỗi, mã không tồn tại, nguồn đổi API...)."""


@dataclass(slots=True)
class TechnicalData:
    """Khối kỹ thuật: suy ra từ lịch sử giá."""

    price: float
    trend: str
    rsi: float
    vol: float
    asof: str
    prices: list[float] = field(default_factory=list)


@dataclass(slots=True)
class FundamentalData:
    """Khối cơ bản: từ báo cáo tài chính."""

    growth: Optional[float] = None
    roe: Optional[float] = None
    margin: Optional[float] = None
    de: Optional[float] = None
    ocf: Optional[str] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    div: Optional[float] = None


def rsi(closes: list[float], period: int = 14) -> float:
    """RSI theo phương pháp Wilder (0–100)."""
    if len(closes) <= period:
        return 50.0
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_gain / avg_loss), 0)


def trend(closes: list[float]) -> str:
    """Xu hướng theo tương quan giá với MA20/MA50."""
    if len(closes) < 20:
        return "side"
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ma20
    last = closes[-1]
    if last > ma50 and ma20 >= ma50:
        return "up"
    if last < ma50 and ma20 <= ma50:
        return "down"
    return "side"


def build_technical(closes: list[float], volumes: list[float], asof: str) -> TechnicalData:
    """Gộp giá + khối lượng thành khối kỹ thuật (giá tính bằng nghìn đồng)."""
    if not closes:
        raise ProviderError("Không có dữ liệu giá")
    window = min(20, len(volumes)) or 1
    return TechnicalData(
        price=round(closes[-1], 2),
        trend=trend(closes),
        rsi=rsi(closes),
        vol=round(sum(volumes[-window:]) / window / 1_000_000, 2),
        asof=asof,
        prices=[round(c, 2) for c in closes[-30:]],
    )


@dataclass(slots=True)
class Candle:
    """Một phiên: ngày + giá mở/cao/thấp/đóng + khối lượng."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
