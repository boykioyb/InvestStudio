"""PROTOTYPE — gọi THẲNG API công khai của VCI/Vietcap, KHÔNG qua vnstock/vnai.

Vì sao có file này: `vnai` (đi kèm vnstock) tự đặt trần ~20 request/phút và
GIẾT tiến trình khi chạm trần — thủ phạm làm job lập chỉ mục chết giữa chừng.

Đo thực tế trong container (2026-08-11): gọi thẳng 15 request trong 0.9 giây vẫn
100% HTTP 200, không bị chặn → **trần là của vnai (client-side), không phải server
VCI**. Gọi thẳng vừa thoát trần, vừa lấy được NHIỀU dữ liệu hơn (tin tức kèm
nguồn + link + tóm tắt, thứ vnstock không phơi ra).

Phạm vi prototype: đúng 3 endpoint mà luồng reindex cần — danh sách rổ, bảng giá,
tin tức. Tự backoff nhẹ nếu lỡ gặp 429/5xx (thay vì để vnai giết tiến trình).

Endpoint (rút từ chính source vnstock đang cài):
  · GET  trading.vietcap.com.vn/api/price/symbols/getByGroup?group=VN30
  · POST trading.vietcap.com.vn/api/price/symbols/getList   body {"symbols":[...]}
  · GET  iq.vietcap.com.vn/api/iq-insight-service/v1/news?ticker=&fromDate=&toDate=&...
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import httpx

_TRADING = "https://trading.vietcap.com.vn/api"
_IQ = "https://iq.vietcap.com.vn/api/iq-insight-service"

#  Header tối thiểu VCI chấp nhận (Origin/Referer phải là trading.vietcap.com.vn).
_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"),
    "Referer": "https://trading.vietcap.com.vn/",
    "Origin": "https://trading.vietcap.com.vn/",
}


class VciError(RuntimeError):
    """Lỗi khi gọi VCI trực tiếp (mạng, 4xx/5xx). Tách khỏi ProviderError của app."""


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
        raise VciError(f"VCI {resp.status_code}: {resp.text[:150]}")
    raise VciError(f"VCI không phản hồi sau nhiều lần thử: {last}")


def constituents(group: str = "VN30") -> list[str]:
    """Danh sách mã của một rổ (VN30, VN100, HNX30…). Một request."""
    data = _request("GET", f"{_TRADING}/price/symbols/getByGroup", params={"group": group})
    return [row["symbol"] for row in data if isinstance(row, dict) and row.get("symbol")]


#  Sàn VCI ghi "HSX"; phần còn lại của app quen "HOSE".
_BOARD_MAP = {"HSX": "HOSE", "HOSE": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}


def symbol_directory() -> dict[str, dict]:
    """Bản đồ mã → {name, exchange} cho TOÀN thị trường trong MỘT request.

    Dùng để bù tên công ty + sàn cho bảng giá (bảng giá VCI không kèm tên).
    """
    rows = _request("GET", f"{_TRADING}/price/symbols/getAll")
    out: dict[str, dict] = {}
    for r in rows or []:
        sym = r.get("symbol")
        if not sym:
            continue
        out[sym] = {
            "name": r.get("organName") or r.get("organShortName") or sym,
            "exchange": _BOARD_MAP.get(r.get("board", ""), r.get("board") or ""),
        }
    return out


def price_board(symbols: Iterable[str]) -> list[dict]:
    """Bảng giá cho một loạt mã (một request cho cả rổ). Trả bản ghi đã làm phẳng."""
    records = _request("POST", f"{_TRADING}/price/symbols/getList",
                       json={"symbols": [s.upper() for s in symbols]})
    out: list[dict] = []
    for rec in records or []:
        li = rec.get("listingInfo") or {}
        mp = rec.get("matchPrice") or {}
        out.append({
            "symbol": li.get("symbol"),
            "ref_price": li.get("refPrice"),
            "ceiling": li.get("ceiling"),
            "floor": li.get("floor"),
            "listed_share": li.get("listedShare"),
            "match_price": mp.get("matchPrice"),
            "open": mp.get("openPrice"),
            "high": mp.get("highest"),
            "low": mp.get("lowest"),
            "accumulated_volume": mp.get("accumulatedVolume"),
            "accumulated_value": mp.get("accumulatedValue"),
            "foreign_buy_value": mp.get("foreignBuyValue"),
            "foreign_sell_value": mp.get("foreignSellValue"),
        })
    return out


def _px(value: Any) -> Optional[float]:
    """Giá VCI ở ĐỒNG → quy về NGHÌN ĐỒNG cho khớp phần còn lại của app."""
    try:
        return round(float(value) / 1000, 2)
    except (TypeError, ValueError):
        return None


def ohlcv(symbol: str, days: int = 180) -> list[dict]:
    """Nến ngày trong `days` gần nhất, cũ→mới. Giá đã quy về nghìn đồng.

    Endpoint OHLC dạng MẢNG song song (t/o/h/l/c/v). `to` là mốc unix hiện tại,
    `countBack` là số nến lấy ngược về — lấy dư rồi cắt theo ngày cho đúng cửa sổ.
    """
    count_back = max(30, int(days) + 5)
    data = _request("POST", f"{_TRADING}/chart/OHLCChart/gap-chart", json={
        "timeFrame": "ONE_DAY", "symbols": [symbol.upper()],
        "to": int(time.time()), "countBack": count_back,
    })
    if not data:
        return []
    el = data[0] or {}
    ts, o, h, l, c, v = (el.get(k) or [] for k in ("t", "o", "h", "l", "c", "v"))
    cutoff = date.today() - timedelta(days=days)
    out: list[dict] = []
    for i in range(len(ts)):
        day = datetime.fromtimestamp(int(ts[i]), tz=timezone.utc).date()
        if day < cutoff:
            continue
        out.append({
            "date": day.isoformat(),
            "open": _px(o[i]), "high": _px(h[i]), "low": _px(l[i]), "close": _px(c[i]),
            "volume": float(v[i] or 0),
        })
    return out


def news(symbol: str, days: int = 180, size: int = 50) -> list[dict]:
    """Tin tức của một mã. Giàu hơn vnstock: kèm nguồn, link bài gốc, tóm tắt."""
    to = date.today()
    frm = to - timedelta(days=days)
    data = _request("GET", f"{_IQ}/v1/news", params={
        "ticker": symbol.upper(), "fromDate": frm.isoformat(), "toDate": to.isoformat(),
        "languageId": 1, "page": 1, "size": size,
    })
    content = ((data or {}).get("data") or {}).get("content") or []
    items: list[dict] = []
    for it in content:
        title = it.get("newsTitle") or it.get("friendlyTitle") or ""
        if not title:
            continue
        items.append({
            "title": title,
            "date": (it.get("publicDate") or "")[:10],
            "source": it.get("newsSource") or "",
            "link": it.get("newsSourceLink") or "",
            "summary": it.get("newsShortContent") or "",
        })
    return items
