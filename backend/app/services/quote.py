"""Giá khớp GẦN REALTIME cho việc frontend poll định kỳ.

Nguyên tắc "lịch sự với nguồn" (tránh biến polling thành spam):
  · Backend là proxy DUY NHẤT có tiết chế — mọi client đọc từ cache chung, nên dù
    bao nhiêu người xem, upstream chỉ thấy tải như một người.
  · Cache PER-SYMBOL, TTL ngắn khi mở phiên (8s), dài khi đóng cửa (5 phút — giá
    không đổi thì hỏi lại làm gì).
  · GỘP LÔ: mọi mã còn "ôi" trong một request lấy qua `vci_direct.price_board`.
Giá lấy từ VCI (bảng giá gần realtime, token-free, gộp được nhiều mã). Lịch sử/điểm
vẫn do DNSE/VCI như cũ — file này chỉ lo con số nhảy trong phiên.
"""
from __future__ import annotations

import time as _time
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

from app.schemas.stock import Quote, QuoteBatch
from app.services.providers import vci_direct
from app.services.providers.vci_direct import VciError

_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_TTL_OPEN = 8.0     # giây — trong phiên, giá nhảy nên làm mới nhanh
_TTL_CLOSED = 300.0  # giây — ngoài phiên, giữ lâu (giá không đổi)

#  Cache per-symbol: mã -> (mốc monotonic, Quote). Chung cho mọi client.
_cache: dict[str, tuple[float, Quote]] = {}


def market_open(now: datetime | None = None) -> bool:
    """Đang trong giờ khớp lệnh HOSE? (T2–T6, 09:00–11:30 & 13:00–15:00 giờ VN)."""
    now = now or datetime.now(_ICT)
    if now.weekday() >= 5:  # thứ 7 / CN
        return False
    t = now.time()
    return (dtime(9, 0) <= t <= dtime(11, 30)) or (dtime(13, 0) <= t <= dtime(15, 0))


def _px(value) -> float | None:
    """Giá VCI ở ĐỒNG → nghìn đồng cho khớp phần còn lại của app."""
    try:
        return round(float(value) / 1000, 2)
    except (TypeError, ValueError):
        return None


def _hhmm(sending_time: str | None) -> str:
    """'20260825 03:34:00.133' (UTC) → 'HH:MM' giờ VN. Rỗng nếu không đọc được."""
    if not sending_time:
        return ""
    try:
        raw = str(sending_time).split(".")[0]
        dt = datetime.strptime(raw, "%Y%m%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.astimezone(_ICT).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def _to_quote(rec: dict) -> Quote:
    price = _px(rec.get("match_price"))
    ref = _px(rec.get("ref_price"))
    change = round(price - ref, 2) if price is not None and ref is not None else None
    change_pct = round(change / ref * 100, 2) if change is not None and ref else None
    vol = rec.get("accumulated_volume")
    return Quote(
        symbol=rec.get("symbol") or "",
        price=price, ref=ref, change=change, change_pct=change_pct,
        volume=round(float(vol) / 1_000_000, 2) if vol else None,
        time=_hhmm(rec.get("sending_time")),
    )


def fetch_quotes(symbols: list[str]) -> QuoteBatch:
    """Lô giá cho `symbols` — đọc cache, chỉ gọi upstream cho mã đã hết hạn (gộp 1 request)."""
    is_open = market_open()
    ttl = _TTL_OPEN if is_open else _TTL_CLOSED
    now = _time.monotonic()

    codes = list(dict.fromkeys(s.upper().strip() for s in symbols if s and s.strip()))
    stale = [c for c in codes if not (
        (hit := _cache.get(c)) and now - hit[0] < ttl)]

    if stale:
        try:
            records = vci_direct.price_board(stale)
        except VciError:
            records = []
        fresh = {r["symbol"]: _to_quote(r) for r in records if r.get("symbol")}
        for code in stale:
            if code in fresh:
                _cache[code] = (now, fresh[code])

    quotes = [_cache[c][1] for c in codes if c in _cache]
    asof = max((q.time for q in quotes if q.time), default="")
    return QuoteBatch(quotes=quotes, is_open=is_open, asof=asof)
