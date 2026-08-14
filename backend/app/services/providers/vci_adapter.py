"""Provider khối cơ bản + kỹ thuật — ADAPTER MỎNG trên `vci_direct`.

Đã CAI vnstock/vnai hoàn toàn ở tầng này: kỹ thuật (OHLCV), cơ bản (chỉ số/BCTC)
và hồ sơ (tên/ngành) đều gọi thẳng API VCI qua `vci_direct` — không còn dính trần
20 req/phút hay bị vnai giết tiến trình.

Chỉ số cơ bản lấy CHUẨN (RATIO_YEAR năm gần nhất + TTM mới nhất), tránh bug cũ của
`Finance.ratio()` vnstock cũ đọc trúng dòng nhãn năm rác.
"""
from __future__ import annotations

from typing import Optional

from app.services.providers import vci_direct
from app.services.providers.base import (
    Candle,
    FundamentalData,
    ProviderError,
    TechnicalData,
    build_technical,
)
from app.services.providers.vci_direct import VciError

_PRICE_LOOKBACK_DAYS = 180


def fetch_technical(ticker: str) -> TechnicalData:
    #  Khối kỹ thuật: lấy OHLCV thẳng từ VCI (không qua vnstock/vnai).
    try:
        candles = vci_direct.ohlcv(ticker, _PRICE_LOOKBACK_DAYS)
    except VciError as exc:
        raise ProviderError(f"VCI không trả giá cho {ticker}: {exc}") from exc

    if not candles:
        raise ProviderError(f"Không có dữ liệu giá cho {ticker}")

    closes = [c["close"] for c in candles if c["close"] is not None]
    volumes = [c["volume"] for c in candles]
    return build_technical(closes, volumes, candles[-1]["date"])


def fetch_fundamentals(ticker: str, source: str = "VCI") -> FundamentalData:
    #  Đã CAI vnstock cho khối cơ bản: lấy CHUẨN từ VCI (RATIO_YEAR năm gần nhất
    #  + TTM mới nhất). Sửa luôn bug cũ của vnstock đọc nhầm cột năm rác.
    try:
        data = vci_direct.fundamentals(ticker)
    except VciError as exc:
        raise ProviderError(f"VCI không trả cơ bản cho {ticker}: {exc}") from exc
    return FundamentalData(
        growth=data["growth"], roe=data["roe"], margin=data["margin"], de=data["de"],
        ocf=data["ocf"], pe=data["pe"], pb=data["pb"], div=data["div"],
    )


def fetch_company(ticker: str) -> tuple[str, str]:
    """(tên hiển thị, ngành) — lấy thẳng VCI, fallback về chính mã."""
    try:
        profile = vci_direct.company_profile(ticker)
    except VciError:
        return ticker, "—"
    name = str(profile.get("name") or ticker)
    sector = str(profile.get("sector") or "—")
    if name.strip().lower() in ("nan", "none", ""):
        name = ticker
    if sector.strip().lower() in ("nan", "none", ""):
        sector = "—"
    return name, sector


def fetch_ohlcv(ticker: str, days: int) -> list[Candle]:
    """Lịch sử nến ngày trong `days` ngày gần nhất (dùng cho biểu đồ nhiều khung)."""
    try:
        rows = vci_direct.ohlcv(ticker, days)
    except VciError as exc:
        raise ProviderError(f"VCI không trả lịch sử giá cho {ticker}: {exc}") from exc

    if not rows:
        raise ProviderError(f"Không có lịch sử giá cho {ticker}")

    return [
        Candle(date=r["date"], open=r["open"], high=r["high"],
               low=r["low"], close=r["close"], volume=r["volume"])
        for r in rows
        if None not in (r["open"], r["high"], r["low"], r["close"])
    ]
