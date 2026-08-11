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


_IQ_COMPANY = f"{_IQ}/v1/company"
_handshaken = False


def _ensure_handshake() -> None:
    """Các endpoint tài chính cần cookie từ /priceboard — lấy một lần rồi giữ."""
    global _handshaken
    if _handshaken:
        return
    try:
        _client.get("https://trading.vietcap.com.vn/priceboard", timeout=15.0)
    except httpx.HTTPError:
        pass
    _handshaken = True


def _fnum(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fin_years(base: str, section: str) -> list[dict]:
    data = (_request("GET", f"{base}/financial-statement", params={"section": section}) or {})
    return ((data.get("data") or {}).get("years")) or []


def _profit_growth(base: str) -> Optional[float]:
    """Tăng trưởng LN sau thuế (% YoY) — 2 năm gần nhất (isa20, fallback isa22)."""
    years = sorted(_fin_years(base, "INCOME_STATEMENT"), key=lambda r: r.get("yearReport") or 0)
    if len(years) < 2:
        return None
    prof = [(_fnum(r.get("isa20")) if _fnum(r.get("isa20")) is not None else _fnum(r.get("isa22")))
            for r in years]
    cur, prev = prof[-1], prof[-2]
    if cur is None or not prev:
        return None
    return round((cur - prev) / abs(prev) * 100, 1)


def _ocf_sign(base: str) -> Optional[str]:
    """'+' dương nhiều năm · '±' thất thường · '-' âm kỳ gần nhất (cfa18)."""
    years = sorted(_fin_years(base, "CASH_FLOW"), key=lambda r: r.get("yearReport") or 0)
    vals = [v for v in (_fnum(r.get("cfa18")) for r in years) if v is not None][::-1]
    if not vals:
        return None
    if vals[0] <= 0:
        return "-"
    return "+" if all(v > 0 for v in vals) else "±"


def fundamentals(symbol: str) -> dict:
    """Chỉ số cơ bản CHUẨN từ VCI (thay Finance của vnstock, vốn đọc nhầm cột).

    ROE/biên/D-E/cổ tức lấy **năm gần nhất** (RATIO_YEAR, nhãn năm đúng); P/E-P/B
    lấy **TTM mới nhất** (phản ánh giá hiện tại); tăng trưởng + dấu OCF từ BCTC.
    Trả dict khớp các trường FundamentalData; thiếu số nào thì None.
    """
    _ensure_handshake()
    base = f"{_IQ_COMPANY}/{symbol.upper()}"
    rows = (_request("GET", f"{base}/statistics-financial") or {}).get("data") or []
    years = [r for r in rows if r.get("ratioType") == "RATIO_YEAR"]
    #  Loại các dòng TTM bị dán nhãn năm rác (year < 2020) để lấy đúng kỳ mới nhất.
    ttms = [r for r in rows if r.get("ratioType") == "RATIO_TTM" and int(r.get("year") or 0) >= 2020]

    out: dict = {"growth": None, "roe": None, "margin": None, "de": None,
                 "ocf": None, "pe": None, "pb": None, "div": None}
    if years:
        a = max(years, key=lambda r: int(r.get("year") or 0))
        roe, margin = _fnum(a.get("roe")), _fnum(a.get("afterTaxProfitMargin"))
        de, div = _fnum(a.get("debtPerEquity")), _fnum(a.get("dividendYield"))
        out["roe"] = round(roe * 100, 1) if roe is not None else None
        out["margin"] = round(margin * 100, 1) if margin is not None else None
        out["de"] = round(de, 2) if de is not None else None
        out["div"] = round(div * 100, 2) if div is not None else None
    if ttms:
        t = max(ttms, key=lambda r: (int(r.get("year") or 0), r.get("quarter") or 0))
        pe, pb = _fnum(t.get("pe")), _fnum(t.get("pb"))
        out["pe"] = round(pe, 1) if pe is not None else None
        out["pb"] = round(pb, 2) if pb is not None else None
    out["growth"] = _profit_growth(base)
    out["ocf"] = _ocf_sign(base)
    return out


def board(symbol: str) -> dict:
    """Bảng giá đầy đủ MỘT mã (giá, bước giá 3 mức, khối ngoại, room) — 1 request.

    Trả số THÔ (đồng / cp / đồng) — tầng market.py tự quy đổi đơn vị như cũ.
    """
    recs = _request("POST", f"{_TRADING}/price/symbols/getList",
                    json={"symbols": [symbol.upper()]})
    if not recs:
        return {}
    r = recs[0]
    li, mp, ba = r.get("listingInfo") or {}, r.get("matchPrice") or {}, r.get("bidAsk") or {}
    return {
        "ref": li.get("refPrice"), "ceiling": li.get("ceiling"), "floor": li.get("floor"),
        "open": mp.get("openPrice"), "high": mp.get("highest"), "low": mp.get("lowest"),
        "match_price": mp.get("matchPrice"), "match_vol": mp.get("matchVol"),
        "avg_price": mp.get("avgMatchPrice"),
        "accumulated_volume": mp.get("accumulatedVolume"),
        "foreign_buy_volume": mp.get("foreignBuyVolume"),
        "foreign_sell_volume": mp.get("foreignSellVolume"),
        "foreign_buy_value": mp.get("foreignBuyValue"),
        "foreign_sell_value": mp.get("foreignSellValue"),
        "current_room": mp.get("currentRoom"), "total_room": mp.get("totalRoom"),
        "bids": [(b.get("price"), b.get("volume")) for b in (ba.get("bidPrices") or [])[:3]],
        "asks": [(a.get("price"), a.get("volume")) for a in (ba.get("askPrices") or [])[:3]],
        "sending_time": mp.get("sendingTime") or li.get("sendingTime") or "",
    }


def company_profile(symbol: str) -> dict:
    """Tên + ngành + vài chỉ số hồ sơ. `sector` để TIẾNG ANH vì benchmark P/E của
    analyzer khớp theo key không dấu (technology/bank…); `sector_vn` để hiển thị."""
    _ensure_handshake()
    d = (_request("GET", f"{_IQ_COMPANY}/details", params={"ticker": symbol.upper()}) or {}).get("data") or {}
    #  Trả nguyên field thô (camelCase) + vài khóa chuẩn hóa cho tiện dùng.
    return {
        **d,
        "name": d.get("viOrganName") or d.get("viOrganShortName") or symbol.upper(),
        "sector": d.get("sector") or "",
        "sector_vn": d.get("sectorVn") or "",
    }


def shareholders(symbol: str) -> list[dict]:
    """Danh sách cổ đông + người nội bộ (cùng nguồn). percentage là phân số 0–1."""
    _ensure_handshake()
    rows = (_request("GET", f"{_IQ_COMPANY}/{symbol.upper()}/shareholder") or {}).get("data") or []
    return [{
        "name": r.get("ownerName") or r.get("ownerNameEn") or "",
        "position": r.get("positionName") or "",
        "quantity": _fnum(r.get("quantity")),
        "percent": _fnum(r.get("percentage")),
        "type": r.get("ownerType") or "",
    } for r in rows if (r.get("ownerName") or r.get("ownerNameEn"))]


def relationships(symbol: str) -> dict:
    """{subsidiaries:[...], affiliates:[...]} — công ty con và liên kết."""
    _ensure_handshake()
    d = (_request("GET", f"{_IQ_COMPANY}/{symbol.upper()}/relationship") or {}).get("data") or {}

    def _map(items):
        return [{
            "name": r.get("rightOrganNameVi") or r.get("rightOrganNameEn") or "",
            "code": r.get("rightTicker") or r.get("rightOrganCode") or "",
            "percent": _fnum(r.get("ownedPercentage")),
        } for r in (items or []) if (r.get("rightOrganNameVi") or r.get("rightOrganNameEn"))]

    return {"subsidiaries": _map(d.get("subsidiaries")), "affiliates": _map(d.get("affiliates"))}


def events(symbol: str, days: int = 540, size: int = 20) -> list[dict]:
    """Sự kiện doanh nghiệp (cổ tức, phát hành, nội bộ…).

    LƯU Ý: endpoint events có trần page size kỳ quặc — size lớn (≥50) lại trả
    RỖNG; size=20 trả đủ. Đừng nâng size mà không đo lại.
    """
    _ensure_handshake()
    to = date.today()
    frm = to - timedelta(days=days)
    data = _request("GET", f"{_IQ}/v1/events", params={
        "ticker": symbol.upper(), "fromDate": frm.isoformat(), "toDate": to.isoformat(),
        "page": 1, "size": size,
    })
    content = ((data or {}).get("data") or {}).get("content") or []
    out = []
    for e in content:
        name = e.get("eventNameVi") or e.get("eventNameEn") or ""
        if not name:
            continue
        ratio = _fnum(e.get("exerciseRatio") or e.get("ratio"))
        out.append({
            "name": name,
            "title": e.get("eventTitleVi") or e.get("eventTitleEn") or "",
            "date": (e.get("publicDate") or e.get("displayDate1") or "")[:10],
            "ratio": round(ratio * 100, 2) if ratio is not None else None,
            "value_per_share": _fnum(e.get("valuePerShare")),
            "record_date": (e.get("recordDate") or "")[:10],
            "exright_date": (e.get("exrightDate") or e.get("exerciseDate") or "")[:10],
            "payout_date": (e.get("paymentDate") or e.get("issueDate") or "")[:10],
            "action": e.get("actionTypeVi") or "",
        })
    return out


def _statement_labels(base: str) -> dict:
    """Bản đồ field-code → nhãn tiếng Việt cho một mã (dùng chung 3 báo cáo)."""
    data = (_request("GET", f"{base}/financial-statement/metrics") or {}).get("data") or {}
    labels: dict[str, str] = {}
    for section in data.values():
        for f in section if isinstance(section, list) else []:
            field, title = f.get("field"), (f.get("titleVi") or f.get("titleEn"))
            if field and title:
                labels[field.lower()] = title
    return labels


def financial_statement(symbol: str, section: str, periods: int = 4) -> dict:
    """Một báo cáo (INCOME_STATEMENT|BALANCE_SHEET|CASH_FLOW): {periods:[năm], rows:[{label,values}]}.

    Nhãn lấy thẳng từ API (titleVi). Trả số THÔ — tầng details tự quy tỷ đồng.
    """
    _ensure_handshake()
    base = f"{_IQ_COMPANY}/{symbol.upper()}"
    years = sorted(_fin_years(base, section), key=lambda r: r.get("yearReport") or 0, reverse=True)
    years = years[:periods]
    if not years:
        return {"periods": [], "rows": []}
    labels = _statement_labels(base)
    #  Field codes theo thứ tự trong báo cáo (bỏ cột hành chính).
    skip = {"organcode", "ticker", "createdate", "updatedate", "yearreport",
            "lengthreport", "publicdate"}
    codes = [k for k in years[0].keys() if k.lower() not in skip]
    period_labels = [str(y.get("yearReport")) for y in years]
    rows = []
    for code in codes:
        vals = [_fnum(y.get(code)) for y in years]
        if any(v is not None for v in vals):
            rows.append({"label": labels.get(code.lower(), code), "values": vals})
    return {"periods": period_labels, "rows": rows}


def ratios_latest(symbol: str) -> dict:
    """{field: value} của kỳ NĂM gần nhất (+ P/E, P/B từ TTM) cho tab Chỉ số."""
    _ensure_handshake()
    rows = (_request("GET", f"{_IQ_COMPANY}/{symbol.upper()}/statistics-financial") or {}).get("data") or []
    years = [r for r in rows if r.get("ratioType") == "RATIO_YEAR"]
    ttms = [r for r in rows if r.get("ratioType") == "RATIO_TTM" and int(r.get("year") or 0) >= 2020]
    out: dict = {}
    if years:
        out.update({k: _fnum(v) for k, v in max(years, key=lambda r: int(r.get("year") or 0)).items()
                    if isinstance(v, (int, float))})
    if ttms:
        t = max(ttms, key=lambda r: (int(r.get("year") or 0), r.get("quarter") or 0))
        out["pe"], out["pb"] = _fnum(t.get("pe")), _fnum(t.get("pb"))
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
