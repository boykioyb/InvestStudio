"""Provider vnstock — nguồn DUY NHẤT cho khối cơ bản, và dự phòng cho khối kỹ thuật.

vnstock gọi API JSON/GraphQL nội bộ của Vietcap (VCI) kèm header trình duyệt
xoay vòng + proxy, nên qua được WAF mà curl trần bị chặn.

Lưu ý format: `Finance.ratio()` của VCI trả bảng "long" với nhãn cột năm TRÙNG
NHAU → phải truy cập theo VỊ TRÍ (cột cuối = kỳ gần nhất), không dùng tên cột.
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
    #  Đã CAI vnstock cho khối kỹ thuật: lấy OHLCV thẳng từ VCI (không qua vnai).
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
    """(tên hiển thị, ngành) — best effort, fallback về chính mã."""
    try:
        from vnstock import Company

        overview = Company(symbol=ticker, source="VCI").overview()
        record = overview.to_dict("records")[0] if len(overview) else {}
        name = str(record.get("short_name") or record.get("company_name")
                   or record.get("organ_name") or ticker)
        sector = str(record.get("industry") or record.get("icb_name3")
                     or record.get("icb_name2") or "—")
        if name.lower() in ("nan", "none", ""):
            name = ticker
        if sector.lower() in ("nan", "none", ""):
            sector = "—"
        return name, sector
    except Exception:
        return ticker, "—"


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
