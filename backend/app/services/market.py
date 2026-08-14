"""Dữ liệu thị trường cho tab Giao dịch · Dòng tiền · Thống kê.

Tất cả suy ra từ giá và khối lượng THẬT. Không tham gia chấm điểm.

Lưu ý về "dòng tiền": nguồn KHÔNG cho áp lực mua/bán cả phiên (`Quote.intraday`
chỉ trả 100 lệnh khớp cuối ≈ 10 giây, phân trang không lùi được). Vì vậy tab này
dùng chỉ báo dòng tiền theo NGÀY — số liệu đủ dài để kết luận có ý nghĩa — cộng
với khối ngoại của phiên hiện tại lấy từ bảng giá.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.stock import (
    FlowPoint,
    ForeignFlow,
    Highlight,
    Level,
    MoneyFlow,
    QuoteLevel,
    RangeKey,
    StatGroup,
    StockStats,
    TradingBoard,
)
from app.services.history import RANGES
from app.services.providers import vci_adapter
from app.services.providers.base import Candle, ProviderError

_BILLION = 1_000_000_000
_MILLION = 1_000_000
_MFI_PERIOD = 14


def _f(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _price(value: Any) -> Optional[float]:
    """Nguồn trả giá theo ĐỒNG → quy về nghìn đồng cho khớp phần còn lại của app."""
    number = _f(value)
    return None if number is None else round(number / 1000, 2)


# ── Tab Giao dịch ────────────────────────────────────────────────────────────
def fetch_board(ticker: str) -> TradingBoard:
    """Ảnh chụp bảng giá của phiên hiện tại (giá, bước giá, khối ngoại)."""
    #  Đã CAI vnstock: bảng giá lấy thẳng VCI (getList) — bid/ask + khối ngoại + room.
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()
    try:
        row = vci_direct.board(ticker)
    except VciError as exc:
        raise ProviderError(f"Không lấy được bảng giá của {ticker}: {exc}") from exc

    if not row:
        raise ProviderError(f"Không có bảng giá cho {ticker}.")

    reference = _price(row.get("ref"))
    match = _price(row.get("match_price"))
    change = round(match - reference, 2) if (match is not None and reference) else None

    def levels(pairs: list) -> list[QuoteLevel]:
        result: list[QuoteLevel] = []
        for raw_price, raw_volume in pairs:
            price, volume = _price(raw_price), _f(raw_volume)
            if price is not None or volume is not None:
                result.append(QuoteLevel(price=price, volume=volume))
        return result

    #  Phiên chưa khớp lệnh nào thì số khối ngoại chắc chắn là của phiên TRƯỚC —
    #  nguồn không reset trường này khi mở phiên mới.
    traded = _f(row.get("accumulated_volume")) or 0
    stale = traded <= 0

    buy_vol, sell_vol = _f(row.get("foreign_buy_volume")), _f(row.get("foreign_sell_volume"))
    buy_val, sell_val = _f(row.get("foreign_buy_value")), _f(row.get("foreign_sell_value"))
    room_left, room_total = _f(row.get("current_room")), _f(row.get("total_room"))
    foreign = ForeignFlow(
        buy_volume=buy_vol,
        sell_volume=sell_vol,
        net_volume=(buy_vol - sell_vol) if (buy_vol is not None and sell_vol is not None) else None,
        buy_value=round(buy_val / _BILLION, 2) if buy_val is not None else None,
        sell_value=round(sell_val / _BILLION, 2) if sell_val is not None else None,
        net_value=(round((buy_val - sell_val) / _BILLION, 2)
                   if (buy_val is not None and sell_val is not None) else None),
        room_left=round(room_left / _MILLION, 2) if room_left is not None else None,
        room_total=round(room_total / _MILLION, 2) if room_total is not None else None,
        stale=stale,
        note=("Đây là số của PHIÊN GẦN NHẤT ĐÃ GIAO DỊCH, không phải phiên đang mở: "
              "phiên này chưa khớp lệnh nào mà nguồn vẫn giữ nguyên số cũ."
              if stale else
              "Lũy kế trong phiên đang diễn ra. Đầu phiên con số có thể vẫn là của "
              "phiên trước vì nguồn không xóa khi mở phiên mới."),
    )

    return TradingBoard(
        ticker=ticker,
        asof=str(row.get("sending_time") or "")[:19],
        reference=reference,
        ceiling=_price(row.get("ceiling")),
        floor=_price(row.get("floor")),
        open=_price(row.get("open")),
        high=_price(row.get("high")),
        low=_price(row.get("low")),
        match_price=match,
        match_volume=_f(row.get("match_vol")),
        avg_price=_price(row.get("avg_price")),
        change=change,
        change_pct=round(change / reference * 100, 2) if (change is not None and reference) else None,
        bids=levels(row.get("bids") or []),
        asks=levels(row.get("asks") or []),
        foreign=foreign,
        note=("Ảnh chụp bảng giá. Giá quy về nghìn đồng. "
              + ("Phiên này chưa có giá khớp." if match is None
                 else "Phiên này đã có giá khớp.")),
    )


# ── Tab Dòng tiền ────────────────────────────────────────────────────────────
def _mfi_series(candles: list[Candle], period: int = _MFI_PERIOD) -> list[Optional[float]]:
    """MFI (Money Flow Index) — như RSI nhưng có nhân khối lượng, thang 0–100."""
    typical = [(c.high + c.low + c.close) / 3 for c in candles]
    raw_flow = [typical[i] * candles[i].volume for i in range(len(candles))]

    result: list[Optional[float]] = [None] * len(candles)
    for i in range(period, len(candles)):
        positive = negative = 0.0
        for j in range(i - period + 1, i + 1):
            if typical[j] > typical[j - 1]:
                positive += raw_flow[j]
            elif typical[j] < typical[j - 1]:
                negative += raw_flow[j]
        if negative == 0:
            result[i] = 100.0
        else:
            result[i] = round(100 - 100 / (1 + positive / negative), 1)
    return result


def _obv_series(candles: list[Candle]) -> list[float]:
    """OBV (On-Balance Volume) — cộng dồn KL phiên tăng, trừ KL phiên giảm."""
    obv = [0.0]
    for i in range(1, len(candles)):
        if candles[i].close > candles[i - 1].close:
            obv.append(obv[-1] + candles[i].volume)
        elif candles[i].close < candles[i - 1].close:
            obv.append(obv[-1] - candles[i].volume)
        else:
            obv.append(obv[-1])
    return obv


def _mfi_state(value: Optional[float]) -> tuple[str, Level]:
    if value is None:
        return "Chưa đủ dữ liệu", "warn"
    if value >= 80:
        return "Trên 80 — tiền vào rất mạnh, dễ quá mua", "bad"
    if value >= 60:
        return "60–80 — dòng tiền đang vào", "good"
    if value >= 40:
        return "40–60 — cân bằng", "warn"
    if value >= 20:
        return "20–40 — dòng tiền đang rút ra", "warn"
    return "Dưới 20 — bị bán mạnh, dễ quá bán", "bad"


def fetch_money_flow(ticker: str, range_key: RangeKey) -> MoneyFlow:
    """Dòng tiền theo ngày: MFI, OBV, khối lượng phiên tăng/giảm + khối ngoại hôm nay."""
    ticker = ticker.upper().strip()
    days, label = RANGES[range_key]

    #  Cần thêm lịch sử phía trước để MFI có đủ 14 phiên khởi động.
    candles = vci_adapter.fetch_ohlcv(ticker, days + 40)
    if len(candles) < 2:
        raise ProviderError(f"Không đủ dữ liệu giá cho {ticker} để tính dòng tiền.")

    mfi = _mfi_series(candles)
    obv = _obv_series(candles)

    #  Chỉ hiển thị đúng khung người dùng chọn (phần dư chỉ để khởi động chỉ báo).
    keep = min(len(candles), max(2, int(days * 0.75)))
    window = list(range(len(candles) - keep, len(candles)))

    def point(i: int) -> FlowPoint:
        candle = candles[i]
        previous = candles[i - 1].close if i > 0 else None
        #  Giá trị khớp ước tính từ giá đóng cửa × khối lượng — nguồn không trả sẵn
        #  giá trị theo ngày, nên đây là XẤP XỈ (giá thật mỗi lệnh khác nhau).
        return FlowPoint(
            d=candle.date,
            mfi=mfi[i],
            obv=round(obv[i] / _MILLION, 2),
            close=round(candle.close, 2),
            change_pct=(round((candle.close - previous) / previous * 100, 2)
                        if previous else None),
            volume=round(candle.volume / _MILLION, 2),
            value=round(candle.close * candle.volume / _MILLION, 2),
        )

    points = [point(i) for i in window]

    up_sessions = down_sessions = 0
    up_volume = down_volume = 0.0
    for i in window:
        if i == 0:
            continue
        if candles[i].close > candles[i - 1].close:
            up_sessions += 1
            up_volume += candles[i].volume
        elif candles[i].close < candles[i - 1].close:
            down_sessions += 1
            down_volume += candles[i].volume

    first_obv, last_obv = obv[window[0]], obv[window[-1]]
    obv_change = (round((last_obv - first_obv) / abs(first_obv) * 100, 1)
                  if first_obv else None)

    latest_mfi = next((mfi[i] for i in reversed(window) if mfi[i] is not None), None)
    state, level = _mfi_state(latest_mfi)

    foreign: Optional[ForeignFlow] = None
    try:
        foreign = fetch_board(ticker).foreign
    except ProviderError:
        foreign = None  # bảng giá lỗi thì vẫn hiển thị phần chỉ báo theo ngày

    return MoneyFlow(
        ticker=ticker,
        range=range_key,
        label=label,
        points=points,
        mfi_latest=latest_mfi,
        mfi_state=state,
        mfi_level=level,
        obv_change_pct=obv_change,
        up_sessions=up_sessions,
        down_sessions=down_sessions,
        up_volume=round(up_volume / _MILLION, 2),
        down_volume=round(down_volume / _MILLION, 2),
        foreign=foreign,
        note=("Chỉ báo tính theo NGÀY. Nguồn không cung cấp áp lực mua/bán cả phiên "
              "(chỉ có 100 lệnh khớp cuối ≈ 10 giây) nên không dùng dữ liệu đó. "
              "Phần khối ngoại ghi rõ thuộc phiên nào ngay trong ô của nó."),
    )


# ── Tab Thống kê ─────────────────────────────────────────────────────────────
def fetch_stats(ticker: str, range_key: RangeKey) -> StockStats:
    """Thống kê tự tính từ lịch sử giá: biên độ, biến động, phiên tăng/giảm."""
    ticker = ticker.upper().strip()
    days, label = RANGES[range_key]
    candles = vci_adapter.fetch_ohlcv(ticker, days)
    if len(candles) < 2:
        raise ProviderError(f"Không đủ dữ liệu giá cho {ticker} trong khung {label.lower()}.")

    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    high = max(c.high for c in candles)
    low = min(c.low for c in candles)
    last = closes[-1]

    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))
               if closes[i - 1]]
    mean = sum(returns) / len(returns) if returns else 0.0
    variance = sum((r - mean) ** 2 for r in returns) / len(returns) if returns else 0.0
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5) * 100

    up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
    down = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i - 1])
    flat = len(closes) - 1 - up - down

    best = max(returns) * 100 if returns else 0.0
    worst = min(returns) * 100 if returns else 0.0

    groups = [
        StatGroup(name="Biên độ giá", items=[
            Highlight(label="Cao nhất khung", value=f"{high:,.2f}", note="nghìn đ/cp"),
            Highlight(label="Thấp nhất khung", value=f"{low:,.2f}", note="nghìn đ/cp"),
            Highlight(label="Cách đỉnh khung",
                      value=f"{(last - high) / high * 100:,.2f}%" if high else "—",
                      note="giá hiện tại so với đỉnh"),
            Highlight(label="Cách đáy khung",
                      value=f"+{(last - low) / low * 100:,.2f}%" if low else "—",
                      note="giá hiện tại so với đáy"),
        ]),
        StatGroup(name="Biến động", items=[
            Highlight(label="Biến động ngày", value=f"{daily_vol * 100:,.2f}%",
                      note="độ lệch chuẩn của mức thay đổi mỗi phiên"),
            Highlight(label="Biến động quy năm", value=f"{annual_vol:,.1f}%",
                      note="quy đổi theo 252 phiên/năm — càng cao càng rung lắc"),
            Highlight(label="Phiên tăng mạnh nhất", value=f"+{best:,.2f}%"),
            Highlight(label="Phiên giảm mạnh nhất", value=f"{worst:,.2f}%"),
        ]),
        StatGroup(name="Nhịp giao dịch", items=[
            Highlight(label="Số phiên", value=f"{len(candles)}"),
            Highlight(label="Phiên tăng / giảm", value=f"{up} / {down}",
                      note=f"{flat} phiên đi ngang"),
            Highlight(label="Tỷ lệ phiên tăng",
                      value=f"{up / (up + down) * 100:,.1f}%" if (up + down) else "—"),
            Highlight(label="KL trung bình",
                      value=f"{sum(volumes) / len(volumes) / _MILLION:,.2f}",
                      note="triệu cp/phiên"),
        ]),
    ]

    return StockStats(
        ticker=ticker, range=range_key, label=label, groups=groups,
        note="Tự tính từ lịch sử giá thật của khung đang chọn.",
    )
