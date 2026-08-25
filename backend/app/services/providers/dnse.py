"""Gọi THẲNG API công khai của DNSE Senses — KHÔNG qua vnstock/vnai.

Vì sao ưu tiên DNSE: nến ngày trả về theo MẢNG song song (t/o/h/l/c/v) và có
chiều sâu **~10 năm** trong MỘT request — đủ 2 chu kỳ để đánh giá (5 năm = 1 chu
kỳ). Endpoint không cần token/cookie; đo thực tế 2026-08-25 đều HTTP 200 ~30ms.

Khác VCI ở đơn vị giá: DNSE trả nến **đã ở NGHÌN ĐỒNG** (close ~14.0 cho TPB) nên
KHÔNG chia 1000 (VCI trả ở đồng, phải chia). Volume là số cổ phiếu thô.

Phạm vi: khối GIÁ (đã wired làm nguồn ưu tiên hàng đầu) + tin tức (nguồn tươi, sẵn
để cắm vào feed). KHÔNG phơi chỉ số cơ bản: `financial-index` của DNSE trả tăng
trưởng LN sai thước đo (không phải YoY năm) nên khối cơ bản vẫn để VCI đảm nhiệm.

Endpoint (rút từ chính trang senses/co-phieu-<mã>):
  · GET  api.dnse.com.vn/chart-api/v2/ohlcs/stock?symbol=&resolution=1D&from=&to=
  · POST api-bo.dnse.com.vn/senses-api/v3/news/_query   body {"symbols":[...],...}
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


def news(symbol: str, limit: int = 20) -> list[dict]:
    """Tin tức của một mã (nguồn TƯƠI, có nội dung đầy đủ). Phân trang qua `cursor`."""
    data = _request("POST", f"{_SENSES}/v3/news/_query", json={
        "symbols": [symbol.upper()], "limit": limit, "cursor": "",
        "tags": ["news"], "macro": False,
    }) or {}
    items: list[dict] = []
    for it in data.get("news") or []:
        title = it.get("title") or ""
        if not title:
            continue
        items.append({
            "title": title,
            "date": str(it.get("publishTime") or "")[:10],
            "source": it.get("domain") or it.get("author") or "",
            "link": it.get("sensesUrl") or "",
            "summary": it.get("head") or "",
        })
    return items
