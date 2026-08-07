"""Provider vnstock — nguồn DUY NHẤT cho khối cơ bản, và dự phòng cho khối kỹ thuật.

vnstock gọi API JSON/GraphQL nội bộ của Vietcap (VCI) kèm header trình duyệt
xoay vòng + proxy, nên qua được WAF mà curl trần bị chặn.

Lưu ý format: `Finance.ratio()` của VCI trả bảng "long" với nhãn cột năm TRÙNG
NHAU → phải truy cập theo VỊ TRÍ (cột cuối = kỳ gần nhất), không dùng tên cột.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.services.providers.base import (
    Candle,
    FundamentalData,
    ProviderError,
    TechnicalData,
    build_technical,
)

_PRICE_LOOKBACK_DAYS = 180
_NET_PROFIT_ROW = "Net profit/(loss) after tax"
_OCF_ROW = "Net cash inflows/(outflows) from operating activities"


def _to_float(value: object, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        number = float(value)  # type: ignore[arg-type]
        return default if number != number else number  # loại NaN
    except (TypeError, ValueError):
        return default


def fetch_technical(ticker: str) -> TechnicalData:
    try:
        from vnstock import Quote
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    today = date.today()
    try:
        history = Quote(symbol=ticker, source="VCI").history(
            start=(today - timedelta(days=_PRICE_LOOKBACK_DAYS)).isoformat(),
            end=today.isoformat(),
            interval="1D",
        )
    except Exception as exc:
        raise ProviderError(f"vnstock không trả giá cho {ticker}: {exc}") from exc

    if history is None or len(history) == 0:
        raise ProviderError(f"vnstock không có dữ liệu giá cho {ticker}")

    closes = [float(x) for x in history["close"].tolist()]
    volumes = [float(x) for x in history["volume"].tolist()]
    return build_technical(closes, volumes, str(history["time"].iloc[-1])[:10])


def _latest_ratios(finance) -> dict[str, Optional[float]]:
    """Bộ chỉ số kỳ gần nhất (TTM), lấy theo vị trí cột cuối."""
    frame = finance.ratio(period="year", lang="en", dropna=False)
    label_index = list(frame.columns).index("item_en")
    return {
        str(frame.iloc[row, label_index]).strip(): _to_float(frame.iloc[row, -1])
        for row in range(len(frame))
    }


def _profit_growth_yoy(finance) -> Optional[float]:
    """Tăng trưởng LN sau thuế (% YoY) từ 2 năm gần nhất của KQKD."""
    frame = finance.income_statement(period="year", lang="en", dropna=False)
    year_columns = [c for c in frame.columns if str(c).isdigit()]
    if len(year_columns) < 2:
        return None
    rows = frame[frame["item_en"].astype(str).str.contains(_NET_PROFIT_ROW, regex=False, na=False)]
    if rows.empty:
        rows = frame[frame["item_en"].astype(str).str.contains("Attributable to parent", na=False)]
    if rows.empty:
        return None
    current = _to_float(rows.iloc[0][year_columns[0]])
    previous = _to_float(rows.iloc[0][year_columns[1]])
    if current is None or not previous:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def _ocf_sign(finance) -> Optional[str]:
    """'+' dương nhiều năm · '±' thất thường · '-' âm kỳ gần nhất."""
    frame = finance.cash_flow(period="year", lang="en", dropna=False)
    year_columns = [c for c in frame.columns if str(c).isdigit()]
    rows = frame[frame["item_en"].astype(str).str.contains(_OCF_ROW, regex=False, na=False)]
    if rows.empty or not year_columns:
        return None
    values = [v for v in (_to_float(rows.iloc[0][c]) for c in year_columns) if v]
    if not values:
        return None
    if values[0] <= 0:
        return "-"
    return "+" if all(v > 0 for v in values) else "±"


def fetch_fundamentals(ticker: str, source: str = "VCI") -> FundamentalData:
    try:
        from vnstock import Finance
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    try:
        finance = Finance(symbol=ticker, source=source)
        ratios = _latest_ratios(finance)
        roe = ratios.get("ROE (%)")
        margin = ratios.get("After-tax Profit Margin (%)")
        dividend = ratios.get("Dividend Yield (%)")
        return FundamentalData(
            growth=_profit_growth_yoy(finance),
            roe=round(roe * 100, 1) if roe is not None else None,
            margin=round(margin * 100, 1) if margin is not None else None,
            de=round(ratios["Debt/Equity"], 2) if ratios.get("Debt/Equity") is not None else None,
            ocf=_ocf_sign(finance),
            pe=round(ratios["P/E"], 1) if ratios.get("P/E") is not None else None,
            pb=round(ratios["P/B"], 2) if ratios.get("P/B") is not None else None,
            div=round(dividend * 100, 2) if dividend is not None else None,
        )
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(f"vnstock/{source} không trả cơ bản cho {ticker}: {exc}") from exc


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
        from vnstock import Quote
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    today = date.today()
    try:
        frame = Quote(symbol=ticker, source="VCI").history(
            start=(today - timedelta(days=days)).isoformat(),
            end=today.isoformat(),
            interval="1D",
        )
    except Exception as exc:
        raise ProviderError(f"vnstock không trả lịch sử giá cho {ticker}: {exc}") from exc

    if frame is None or len(frame) == 0:
        raise ProviderError(f"vnstock không có lịch sử giá cho {ticker}")

    return [
        Candle(
            date=str(row.time)[:10],
            open=float(row.open), high=float(row.high),
            low=float(row.low), close=float(row.close),
            volume=float(row.volume),
        )
        for row in frame.itertuples()
    ]
