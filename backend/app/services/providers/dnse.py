"""Gọi THẲNG API công khai của DNSE Senses — KHÔNG qua vnstock/vnai.

Vì sao ưu tiên DNSE: nến ngày trả về theo MẢNG song song (t/o/h/l/c/v) và có
chiều sâu **~10 năm** trong MỘT request — đủ 2 chu kỳ để đánh giá (5 năm = 1 chu
kỳ). Endpoint không cần token/cookie; đo thực tế 2026-08-25 đều HTTP 200 ~30ms.

Khác VCI ở đơn vị giá: DNSE trả nến **đã ở NGHÌN ĐỒNG** (close ~14.0 cho TPB) nên
KHÔNG chia 1000 (VCI trả ở đồng, phải chia). Volume là số cổ phiếu thô.

Phạm vi: khối GIÁ (nguồn ưu tiên hàng đầu) + tin tức + sự kiện doanh nghiệp (đều
nguồn TƯƠI, thay feed VCI đã đóng băng). KHÔNG phơi chỉ số cơ bản: `financial-index`
của DNSE trả tăng trưởng LN sai thước đo (không phải YoY năm) nên cơ bản để VCI lo.

Endpoint (rút từ chính trang senses/co-phieu-<mã>):
  · GET  api.dnse.com.vn/chart-api/v2/ohlcs/stock?symbol=&resolution=1D&from=&to=
  · POST api-bo.dnse.com.vn/senses-api/v3/news/_query   body {"symbols":[...],...}
  · GET  api-bo.dnse.com.vn/senses-api/events?symbol=       (sự kiện riêng từng mã)
  · GET  api-bo.dnse.com.vn/senses-api/corporate-actions    (lịch quyền SẮP TỚI, cả sàn)
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx

_CHART = "https://api.dnse.com.vn/chart-api"
_SENSES = "https://api-bo.dnse.com.vn/senses-api"

#  DNSE chấp nhận request ẩn danh; Origin/Referer đặt cho lịch sự + tránh WAF.
_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"),
    "Referer": "https://www.dnse.com.vn/",
    "Origin": "https://www.dnse.com.vn",
}


class DnseError(RuntimeError):
    """Lỗi khi gọi DNSE trực tiếp (mạng, 4xx/5xx). Tách khỏi ProviderError của app."""


_client = httpx.Client(headers=_HEADERS, timeout=20.0)


def _request(method: str, url: str, **kwargs: Any) -> Any:
    """Gọi có backoff nhẹ. 429/5xx thì nghỉ tăng dần rồi thử lại (êm, không chết)."""
    last = ""
    for attempt in range(4):
        try:
            resp = _client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:  # lỗi mạng
            last = str(exc)
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429 or resp.status_code >= 500:
            last = f"HTTP {resp.status_code}"
            time.sleep(2.0 * (attempt + 1))
            continue
        raise DnseError(f"DNSE {resp.status_code}: {resp.text[:150]}")
    raise DnseError(f"DNSE không phản hồi sau nhiều lần thử: {last}")


def _fnum(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ohlcv(symbol: str, days: int = 180) -> list[dict]:
    """Nến ngày trong `days` gần nhất, cũ→mới. Giá ĐÃ ở nghìn đồng (không chia).

    Mảng song song t/o/h/l/c/v. Lấy dư 5 ngày rồi cắt theo mốc lịch cho đúng cửa
    sổ. `days` lớn (vài nghìn) vẫn 1 request — đây là ưu thế chiều sâu của DNSE.
    """
    to_ts = int(time.time())
    from_ts = to_ts - (int(days) + 5) * 86_400
    data = _request("GET", f"{_CHART}/v2/ohlcs/stock", params={
        "symbol": symbol.upper(), "resolution": "1D", "from": from_ts, "to": to_ts,
    }) or {}
    ts = data.get("t") or []
    o, h, l, c, v = (data.get(k) or [] for k in ("o", "h", "l", "c", "v"))
    cutoff = date.today() - timedelta(days=days)
    out: list[dict] = []
    for i in range(len(ts)):
        day = datetime.fromtimestamp(int(ts[i]), tz=timezone.utc).date()
        if day < cutoff:
            continue
        out.append({
            "date": day.isoformat(),
            "open": _fnum(o[i]), "high": _fnum(h[i]),
            "low": _fnum(l[i]), "close": _fnum(c[i]),
            "volume": float(v[i] or 0),
        })
    return out


def news_many(symbols: list[str], limit: int = 20) -> list[dict]:
    """Tin tức của NHIỀU mã trong MỘT request (body nhận cả danh sách `symbols`).

    Quan trọng cho khối điểm nhấn trang chủ: 30 mã VN30 vẫn chỉ tốn 1 request,
    không fan-out 30 lần. Mỗi tin kèm `symbol` (mã chính do nguồn gắn) và
    `symbols` (mọi mã được nhắc) để tầng trên lọc theo rổ.
    """
    codes = [s.upper().strip() for s in symbols if s and s.strip()]
    if not codes:
        return []
    data = _request("POST", f"{_SENSES}/v3/news/_query", json={
        "symbols": codes, "limit": limit, "cursor": "",
        "tags": ["news"], "macro": False,
    }) or {}
    items: list[dict] = []
    for it in data.get("news") or []:
        title = it.get("title") or ""
        if not title:
            continue
        related = [str(s).upper() for s in (it.get("symbols") or []) if s]
        items.append({
            "title": title,
            "date": str(it.get("publishTime") or "")[:10],
            "source": it.get("domain") or it.get("author") or "",
            "link": it.get("sensesUrl") or "",
            "summary": it.get("head") or "",
            "symbol": str(it.get("symbol") or "").upper(),
            "symbols": related,
        })
    return items


def news(symbol: str, limit: int = 20) -> list[dict]:
    """Tin tức của một mã (nguồn TƯƠI, có nội dung đầy đủ). Phân trang qua `cursor`."""
    return news_many([symbol], limit)


def corporate_events(symbol: str) -> list[dict]:
    """Sự kiện doanh nghiệp RIÊNG một mã (cổ tức, ĐHCĐ, phát hành…) — nguồn TƯƠI.

    Endpoint per-symbol `senses-api/events` (khác feed corporate-actions toàn thị
    trường). Trả shape khớp `_event_items` của feed:
      · gdkhqDate → ngày GDKHQ (giao dịch không hưởng quyền) = exright_date + date
      · ndkccDate → ngày ĐKCC (đăng ký cuối cùng) = record_date
    Endpoint KHÔNG kèm tỷ lệ/giá trị cổ tức → ratio/value_per_share để None.
    """
    data = _request("GET", f"{_SENSES}/events", params={"symbol": symbol.upper()})
    rows = data if isinstance(data, list) else ((data or {}).get("data") or [])
    out: list[dict] = []
    for e in rows:
        name = e.get("name") or e.get("title") or ""
        if not name:
            continue
        exright = str(e.get("gdkhqDate") or e.get("gdkhqDateOrigin") or "")[:10]
        out.append({
            "name": name,
            "title": e.get("title") or e.get("titleEvent") or "",
            "date": exright,
            "ratio": None,
            "value_per_share": None,
            "record_date": str(e.get("ndkccDate") or e.get("ndkccDateOrigin") or "")[:10],
            "exright_date": exright,
            "payout_date": "",
            "action": "",
        })
    return out


def upcoming_corporate_actions() -> list[dict]:
    """Sự kiện doanh nghiệp SẮP TỚI của TOÀN thị trường — MỘT request cho mọi mã.

    Khác `corporate_events(symbol)` (per-symbol, và chỉ trả sự kiện ĐÃ QUA): feed
    `senses-api/corporate-actions` là lịch quyền sắp thực hiện của cả sàn — đo
    thực tế 2026-09-07 trả 72 sự kiện, GDKHQ từ hôm nay tới +30 ngày. Nhờ vậy
    dựng lịch sự kiện cho một rổ 30 mã chỉ tốn 1 request thay vì 30.

    Endpoint BỎ QUA mọi tham số (đã thử size/limit/from/to/symbols → vẫn trả y
    nguyên 72 dòng), nên việc lọc theo rổ và theo ngày làm ở tầng service.
    """
    data = _request("GET", f"{_SENSES}/corporate-actions") or {}
    rows = data.get("corporateActions") if isinstance(data, dict) else data
    out: list[dict] = []
    for e in rows or []:
        symbol = str(e.get("symbol") or "").upper()
        name = e.get("name") or e.get("titleEvent") or ""
        if not symbol or not name:
            continue
        out.append({
            "symbol": symbol,
            "name": name,
            "title": e.get("title") or e.get("titleEvent") or e.get("note") or "",
            #  GDKHQ = mốc người mua sau ngày này KHÔNG còn hưởng quyền → mốc
            #  đáng nhớ nhất với người xem; ĐKCC/ngày thực hiện chỉ là dự phòng.
            "exright_date": str(e.get("exRightsDate") or "")[:10],
            "record_date": str(e.get("recordDate") or "")[:10],
            "action_date": str(e.get("actionDate") or "")[:10],
            "url": e.get("url") or "",
        })
    return out
