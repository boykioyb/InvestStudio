#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phan_tich_ma.py — Crawl dữ liệu chứng khoán VN thật (vnstock) → chấm điểm → kết luận.

Nhập MÃ cổ phiếu → tool tự lấy số liệu (báo cáo tài chính + giá) → ánh xạ vào
14 tiêu chí của mô hình 100 điểm, rồi:
  1) In báo cáo tóm tắt ra terminal (sức khỏe · tầm nhìn · điểm · quyết định).
  2) Ghi `du-lieu-thuc.js` để phan-tich-ma.html hiển thị báo cáo tương tác đầy đủ
     (renderer + công thức chấm điểm giữ NGUYÊN trong HTML — một nguồn sự thật).

NGUỒN DỮ LIỆU: thư viện `vnstock` (bọc VCI/TCBS, xử lý session/Cloudflare).
  Cài:  pip install vnstock
  Chạy: python3 phan_tich_ma.py FPT              # 1 mã
        python3 phan_tich_ma.py FPT VNM HPG      # nhiều mã
        python3 phan_tich_ma.py FPT --pos 2 --mgmt 2 --cat 1   # ghi đè định tính

GIỚI HẠN TRUNG THỰC (memory: "honest about limits"):
  - 3 tiêu chí ĐỊNH TÍNH (vị thế ngành 6đ, ban lãnh đạo 5đ, catalyst 4đ = 15đ)
    KHÔNG crawl tự động được → mặc định "trung bình" (mức 1), chỉnh bằng cờ
    --pos/--mgmt/--cat (0=yếu,1=TB,2=tốt).
  - P/E ngành & P/B hợp lý (peSec/pbFair) là ƯỚC LƯỢNG theo bảng benchmark ngành,
    chỉnh bằng --pe-sec / --pb-fair.

⚠️ Công cụ hỗ trợ tư duy — KHÔNG phải khuyến nghị đầu tư.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from typing import Optional

import ssl
import urllib.request
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DATA_JS = os.path.join(HERE, "du-lieu-thuc.js")

# CafeF: endpoint JSON công khai duy nhất còn sống ổn định (đã kiểm chứng).
_CAFEF_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
_CAFEF_PRICE = "https://cafef.vn/du-lieu/ajax/pagenew/datahistory/pricehistory.ashx"

# ── Benchmark P/E · P/B theo ngành (ước lượng thị trường VN, có thể chỉnh) ────
# Dùng khi không lấy được trung vị ngành động. Nhãn rõ ràng là "ước lượng".
SECTOR_BENCHMARK: dict[str, tuple[float, float]] = {
    # ngành (khớp gần đúng, không dấu, chữ thường)  : (P/E ngành, P/B hợp lý)
    "ngan hang": (9.0, 1.6), "bank": (9.0, 1.6),
    "bat dong san": (16.0, 1.5), "real estate": (16.0, 1.5),
    "cong nghe": (18.0, 3.5), "technology": (18.0, 3.5), "information technology": (18.0, 3.5),
    "ban le": (17.0, 2.5), "retail": (17.0, 2.5),
    "thep": (12.0, 1.4), "vat lieu": (13.0, 1.6), "materials": (13.0, 1.6),
    "dau khi": (10.0, 1.3), "nang luong": (11.0, 1.4), "energy": (11.0, 1.4),
    "tien ich": (12.0, 1.6), "dien": (12.0, 1.6), "utilities": (12.0, 1.6),
    "tieu dung": (16.0, 2.8), "consumer": (16.0, 2.8),
    "chung khoan": (13.0, 1.8), "securities": (13.0, 1.8),
}
DEFAULT_PE_SEC, DEFAULT_PB_FAIR = 15.0, 2.0  # fallback nếu không rõ ngành


# ── Cấu trúc object `s` (khớp shape trong phan-tich-ma.html) ─────────────────
@dataclass
class Stock:
    t: str            # mã
    name: str         # "Tên — Ngành"
    sector: str
    price: float      # nghìn đồng/cp
    growth: float     # % tăng trưởng LN YoY
    roe: float        # %
    margin: float     # % biên LN ròng
    de: float         # nợ vay / vốn chủ
    ocf: str          # "+" | "±" | "-"
    pe: float
    peSec: float      # P/E trung bình ngành (ước lượng)
    pb: float
    pbFair: float     # P/B hợp lý (ước lượng)
    div: float        # % cổ tức
    trend: str        # "up" | "side" | "down"
    vol: float        # triệu cp/phiên (TB)
    rsi: float
    pos: int = 1      # vị thế ngành 0/1/2 (định tính)
    mgmt: int = 1     # ban lãnh đạo 0/1/2 (định tính)
    cat: int = 1      # catalyst 0/1/2 (định tính)
    seed: float = 0.1
    real: bool = True
    asof: str = ""    # ngày dữ liệu
    src: str = ""     # nguồn dữ liệu đã dùng
    missing: str = "" # tiêu chí không lấy được (nếu có)
    hint: str = ""    # gợi ý nguyên nhân/cách sửa khi thiếu dữ liệu
    px: list = field(default_factory=list)  # ~30 giá đóng cửa THẬT gần nhất (vẽ biểu đồ)


# =============================================================================
# PHẦN 1 — CRAWL & TÍNH TOÁN CHỈ SỐ
# =============================================================================
def _to_float(x, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        return default if v != v else v  # loại NaN
    except (TypeError, ValueError):
        return default


def _ratio_ttm(fin) -> dict[str, float]:
    """Lấy bộ chỉ số TTM (cột cuối, format long của VCI) theo item_en."""
    df = fin.ratio(period="year", lang="en", dropna=False)
    ie = list(df.columns).index("item_en")
    out: dict[str, float] = {}
    for i in range(len(df)):
        key = str(df.iloc[i, ie]).strip()
        out[key] = _to_float(df.iloc[i, -1])  # cột cuối = TTM/gần nhất
    return out


def _profit_growth_yoy(fin) -> float:
    """Tăng trưởng LN sau thuế YoY (%) từ 2 năm gần nhất của KQKD."""
    df = fin.income_statement(period="year", lang="en", dropna=False)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    if len(year_cols) < 2:
        return 0.0
    y0, y1 = year_cols[0], year_cols[1]  # mới nhất, kề trước
    row = df[df["item_en"].astype(str).str.contains("Net profit/(loss) after tax", regex=False, na=False)]
    if row.empty:
        row = df[df["item_en"].astype(str).str.contains("Attributable to parent", na=False)]
    if row.empty:
        return 0.0
    cur, prev = _to_float(row.iloc[0][y0]), _to_float(row.iloc[0][y1])
    if prev == 0:
        return 0.0
    return round((cur - prev) / abs(prev) * 100, 1)


def _ocf_sign(fin) -> str:
    """Dấu dòng tiền KD nhiều năm: '+' bền, '±' thất thường, '-' âm."""
    df = fin.cash_flow(period="year", lang="en", dropna=False)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    row = df[df["item_en"].astype(str).str.contains(
        "Net cash inflows/(outflows) from operating activities", regex=False, na=False)]
    if row.empty or not year_cols:
        return "±"
    vals = [_to_float(row.iloc[0][c]) for c in year_cols]
    vals = [v for v in vals if v != 0.0]
    if not vals:
        return "±"
    latest = vals[0]
    if latest <= 0:
        return "-"
    return "+" if all(v > 0 for v in vals) else "±"


def _rsi(closes: list[float], period: int = 14) -> float:
    """RSI Wilder (0–100)."""
    if len(closes) <= period:
        return 50.0
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return round(100 - 100 / (1 + rs), 0)


def _trend(closes: list[float]) -> str:
    """Xu hướng theo MA20/MA50: up | side | down."""
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


def _sector_benchmark(sector: str) -> tuple[float, float]:
    key = (sector or "").strip().lower()
    for k, v in SECTOR_BENCHMARK.items():
        if k in key:
            return v
    return DEFAULT_PE_SEC, DEFAULT_PB_FAIR


def _company_info(ticker: str) -> tuple[str, str]:
    """(tên hiển thị, ngành). Best-effort — fallback về mã nếu thiếu."""
    try:
        from vnstock import Company
        ov = Company(symbol=ticker, source="VCI").overview()
        d = ov.to_dict("records")[0] if len(ov) else {}
        name = str(d.get("short_name") or d.get("company_name") or d.get("organ_name") or ticker)
        sector = str(d.get("industry") or d.get("icb_name3") or d.get("icb_name2") or "—")
        if name.lower() in ("nan", "none", ""):
            name = ticker
        if sector.lower() in ("nan", "none", ""):
            sector = "—"
        return name, sector
    except Exception:
        return ticker, "—"


# ── ADAPTER CafeF (stdlib thuần — chạy được cả khi CHƯA cài vnstock) ─────────
def _ssl_context() -> Optional[ssl.SSLContext]:
    """Ưu tiên CA bundle của certifi (venv Python.framework hay thiếu CA hệ thống);
    fallback về context mặc định. KHÔNG tắt verify."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _http_json(url: str, params: dict) -> dict:
    """GET JSON với header trình duyệt (né WAF) — dùng urllib, không cần requests."""
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={
        "User-Agent": _CAFEF_UA, "Referer": "https://cafef.vn/",
        "Accept": "application/json, text/plain, */*"})
    with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def _cafef_history(ticker: str, max_rows: int = 120) -> tuple[list[float], list[float], str]:
    """Lịch sử giá ĐIỀU CHỈNH từ CafeF (phân trang 20 dòng/trang) → cũ→mới."""
    closes: list[float] = []
    vols: list[float] = []
    dates: list[str] = []
    for page in range(1, max_rows // 20 + 2):
        d = _http_json(_CAFEF_PRICE, {"Symbol": ticker, "StartDate": "", "EndDate": "",
                                      "PageIndex": page, "PageSize": 20})
        block = (d.get("Data") or {})
        rows = block.get("Data") or []
        if not rows:
            break
        for row in rows:
            px = row.get("GiaDieuChinh") or row.get("GiaDongCua")
            if px:
                closes.append(float(px))
                vols.append(float(row.get("KhoiLuongKhopLenh") or 0))
                dates.append(str(row.get("Ngay", "")))
        if page * 20 >= int(block.get("TotalCount", 0)) or len(closes) >= max_rows:
            break
    if not closes:
        raise RuntimeError("CafeF không trả dữ liệu giá")
    closes.reverse(); vols.reverse(); dates.reverse()  # CafeF trả mới→cũ
    asof = dates[-1]
    try:  # dd/mm/yyyy → yyyy-mm-dd
        dd, mm, yy = asof.split("/")
        asof = f"{yy}-{mm}-{dd}"
    except ValueError:
        pass
    return closes, vols, asof


def _technical_block(closes: list[float], vols: list[float], asof: str) -> dict:
    """Từ giá/khối lượng → 3 tiêu chí kỹ thuật + giá hiện tại."""
    return {
        "price": round(closes[-1], 2),
        "trend": _trend(closes),
        "rsi": _rsi(closes),
        "vol": round(sum(vols[-20:]) / min(20, len(vols)) / 1_000_000, 2),  # triệu cp/phiên
        "asof": asof,
        "px": [round(c, 2) for c in closes[-30:]],  # 30 phiên gần nhất — giá THẬT để vẽ
    }


# ── Nguồn KỸ THUẬT & CƠ BẢN ──────────────────────────────────────────────────
def _technical_cafef(ticker: str) -> dict:
    return _technical_block(*_cafef_history(ticker))


def _technical_vnstock(ticker: str) -> dict:
    from vnstock import Quote
    end = date.today()
    hist = Quote(symbol=ticker, source="VCI").history(
        start=(end - timedelta(days=180)).isoformat(), end=end.isoformat(), interval="1D")
    if hist is None or len(hist) == 0:
        raise RuntimeError("vnstock không trả giá")
    closes = [float(x) for x in hist["close"].tolist()]
    vols = [float(x) for x in hist["volume"].tolist()]
    return _technical_block(closes, vols, str(hist["time"].iloc[-1])[:10])


def _fundamentals_vnstock(ticker: str, source: str = "VCI") -> dict:
    """8 tiêu chí cơ bản từ ratio-TTM + KQKD + LCTT."""
    from vnstock import Finance
    fin = Finance(symbol=ticker, source=source)
    r = _ratio_ttm(fin)
    return {
        "roe": round(r.get("ROE (%)", 0) * 100, 1),
        "margin": round(r.get("After-tax Profit Margin (%)", 0) * 100, 1),
        "de": round(r.get("Debt/Equity", 0), 2),
        "pe": round(r.get("P/E", 0), 1),
        "pb": round(r.get("P/B", 0), 2),
        "div": round(r.get("Dividend Yield (%)", 0) * 100, 2),
        "growth": _profit_growth_yoy(fin),
        "ocf": _ocf_sign(fin),
    }


def fetch_stock(ticker: str, *, pos: int, mgmt: int, cat: int,
                pe_sec: Optional[float], pb_fair: Optional[float],
                source: str = "auto") -> Stock:
    """Orchestrator: gộp KỸ THUẬT (CafeF↔vnstock) + CƠ BẢN (vnstock VCI→KBS).

    source: 'auto' (mặc định) · 'vnstock' (chỉ vnstock) · 'cafef' (chỉ CafeF,
    khối cơ bản sẽ trống & được gắn cờ — minh họa đường đi thuần CafeF).
    Luôn trả về đủ 14 tiêu chí; tiêu chí không lấy được ghi vào Stock.missing.
    """
    ticker = ticker.upper().strip()
    used: list[str] = []
    missing: list[str] = []

    # --- KHỐI KỸ THUẬT + GIÁ (ưu tiên CafeF: JSON sạch; vnstock dự phòng) ---
    if source == "vnstock":
        tech_order = [("vnstock", _technical_vnstock)]
    elif source == "cafef":
        tech_order = [("CafeF", _technical_cafef)]
    else:
        tech_order = [("CafeF", _technical_cafef), ("vnstock", _technical_vnstock)]
    tech: Optional[dict] = None
    for label, fn in tech_order:
        try:
            tech = fn(ticker)
            used.append(f"{label}(giá/kỹ thuật)")
            break
        except Exception:
            continue
    if tech is None:
        raise RuntimeError(f"Không lấy được giá cho {ticker} từ mọi nguồn kỹ thuật")

    # --- KHỐI CƠ BẢN (fundamentals): vnstock VCI → KBS. Bỏ nếu source=cafef ---
    fund: Optional[dict] = None
    name, sector = ticker, "—"
    hint = ""
    if source == "cafef":
        hint = "Chế độ --source cafef chỉ lấy giá/kỹ thuật. Dùng mặc định (bỏ cờ) để có cơ bản."
    else:
        try:
            import vnstock  # noqa: F401
            name, sector = _company_info(ticker)
            for fsrc in ("VCI", "KBS"):
                try:
                    fund = _fundamentals_vnstock(ticker, fsrc)
                    used.append(f"vnstock/{fsrc}(cơ bản)")
                    break
                except Exception:
                    continue
            if fund is None:
                hint = f"vnstock không trả cơ bản cho {ticker} (mã lạ / mới niêm yết / nguồn lỗi tạm thời)."
        except ImportError:
            hint = "Chưa cài vnstock → chạy: pip install vnstock"
    if fund is None:
        # Không verify được → KHÔNG cho điểm: gán sentinel để mọi tiêu chí cơ bản = 0đ
        # (không phải số thật; hiển thị "N/A"). Trung thực hơn là chấm điểm số 0 thành "tốt".
        fund = {"roe": 0, "margin": 0, "de": 99.0, "pe": 99.0, "pb": 99.0, "div": 0, "growth": 0, "ocf": "-"}
        missing = ["Tăng trưởng", "ROE", "Biên LN", "D/E", "Dòng tiền", "P/E", "P/B", "Cổ tức"]

    bpe, bpb = _sector_benchmark(sector)
    trend = tech["trend"]
    return Stock(
        t=ticker, name=f"{name} — {sector}" if sector != "—" else name, sector=sector,
        price=tech["price"], growth=fund["growth"], roe=fund["roe"], margin=fund["margin"],
        de=fund["de"], ocf=fund["ocf"], pe=fund["pe"],
        peSec=round(pe_sec if pe_sec is not None else bpe, 1),
        pb=fund["pb"], pbFair=round(pb_fair if pb_fair is not None else bpb, 2),
        div=fund["div"], trend=trend, vol=tech["vol"], rsi=tech["rsi"],
        pos=pos, mgmt=mgmt, cat=cat,
        seed=0.8 if trend == "up" else -0.8 if trend == "down" else 0.1,
        real=True, asof=tech["asof"], src=" · ".join(used), missing=", ".join(missing), hint=hint,
        px=tech.get("px", []),
    )


# =============================================================================
# PHẦN 2 — MÔ HÌNH CHẤM ĐIỂM (bản port CLI)
# ⚠️ PHẢI KHỚP phan-tich-ma.html dòng 135–183. Sửa 1 nơi → sửa nơi kia.
# =============================================================================
def _jround(x: float) -> int:
    """Làm tròn NỬA LÊN như JS Math.round (x không âm) — để khớp bản JS trong HTML.
    KHÁC round() của Python (banker's rounding): round(2.5)=2 còn Math.round(2.5)=3."""
    import math
    return math.floor(x + 0.5)


def _lvl_pts(lvl: int, mx: int) -> int:
    return mx if lvl == 2 else _jround(mx / 2) if lvl == 1 else 0


def _ocf_lvl(o: str) -> int:
    return 2 if o == "+" else 1 if o == "±" else 0


def _vol_lvl(v: float) -> int:
    return 0 if v < 0.5 else 1 if v < 2 else 2


def breakdown(s: Stock) -> dict:
    g = 0 if s.growth <= 0 else 1 if s.growth < 20 else 2
    r = 0 if s.roe < 10 else 1 if s.roe <= 15 else 2
    m = 0 if s.margin < 8 else 1 if s.margin <= 15 else 2
    d = 0 if s.de > 1.5 else 1 if s.de >= 0.5 else 2
    o = _ocf_lvl(s.ocf)
    pe_r = s.pe / s.peSec if s.peSec else 1
    pe = 0 if pe_r > 1.1 else 2 if pe_r < 0.9 else 1
    pb_r = s.pb / s.pbFair if s.pbFair else 1
    pb = 0 if pb_r > 1.1 else 2 if pb_r < 0.9 else 1
    dv = 0 if s.div <= 0 else 1 if s.div < 3 else 2
    tr = 2 if s.trend == "up" else 1 if s.trend == "side" else 0
    lq = _vol_lvl(s.vol)
    rs = 0 if (s.rsi > 80 or s.rsi < 30) else 1 if s.rsi > 70 else 2

    cats = [
        ("Nền tảng & tài chính", 45, [
            ("Tăng trưởng LN", f"{s.growth}% YoY", g, 12),
            ("ROE", f"{s.roe}%", r, 10),
            ("Biên lợi nhuận", f"{s.margin}%", m, 8),
            ("Nợ vay D/E", f"{s.de:.1f}", d, 8),
            ("Dòng tiền KD", {"+": "Dương bền", "±": "Thất thường"}.get(s.ocf, "Âm"), o, 7),
        ]),
        ("Định giá", 20, [
            ("P/E vs ngành", f"{s.pe} / ngành {s.peSec}", pe, 10),
            ("P/B", f"{s.pb} / hợp lý {s.pbFair}", pb, 5),
            ("Cổ tức", f"{s.div}%", dv, 5),
        ]),
        ("Kỹ thuật & xu hướng", 20, [
            ("Xu hướng giá", {"up": "Trên MA, tăng", "side": "Đi ngang"}.get(s.trend, "Dưới MA, giảm"), tr, 8),
            ("Thanh khoản", f"{s.vol} tr cp/phiên", lq, 6),
            ("Động lượng RSI", f"RSI {s.rsi:.0f}", rs, 6),
        ]),
        ("Định tính & vĩ mô", 15, [
            ("Vị thế ngành", ["Yếu", "Trung bình", "Dẫn đầu"][s.pos], s.pos, 6),
            ("Ban lãnh đạo", ["Kém", "Ổn", "Uy tín"][s.mgmt], s.mgmt, 5),
            ("Catalyst", ["Không rõ", "Tiềm năng", "Rõ ràng"][s.cat], s.cat, 4),
        ]),
    ]
    parsed, sums = [], []
    for cat, mx, items in cats:
        it2, ssum = [], 0
        for label, raw, lvl, imax in items:
            pts = _lvl_pts(lvl, imax)
            ssum += pts
            it2.append({"l": label, "raw": raw, "lvl": lvl, "pts": pts, "max": imax})
        parsed.append({"cat": cat, "max": mx, "sum": ssum, "items": it2})
        sums.append(ssum)
    total = sum(sums)
    faP, valP, taP, qP = sums[0] / 45, sums[1] / 20, sums[2] / 20, sums[3] / 15
    horizons = {
        "short": _jround((taP * 0.6 + faP * 0.2 + qP * 0.2) * 100),
        "mid": _jround((faP * 0.35 + taP * 0.35 + valP * 0.15 + qP * 0.15) * 100),
        "long": _jround((faP * 0.5 + valP * 0.25 + qP * 0.25) * 100),
    }
    return {"cats": parsed, "sums": sums, "total": total, "horizons": horizons}


def verdict(total: int) -> str:
    if total >= 80:
        return "Xuất sắc — ưu tiên giải ngân"
    if total >= 65:
        return "Tốt — có thể đầu tư, canh điểm mua"
    if total >= 50:
        return "Trung bình — theo dõi / thăm dò nhỏ"
    return "Yếu — nên tránh"


# =============================================================================
# PHẦN 3 — XUẤT KẾT QUẢ
# =============================================================================
class C:  # màu terminal
    G, Y, R, B, DIM, BOLD, END = "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[2m", "\033[1m", "\033[0m"


def _col(pts: int, mx: int) -> str:
    return C.G if pts == mx else C.R if pts == 0 else C.Y


def print_cli(s: Stock) -> None:
    b = breakdown(s)
    total = b["total"]
    vcol = C.G if total >= 65 else C.Y if total >= 50 else C.R
    h = b["horizons"]
    best = max([("Ngắn hạn", h["short"]), ("Trung hạn", h["mid"]), ("Dài hạn", h["long"])], key=lambda x: x[1])
    size = "15–20%" if total >= 80 else "8–12%" if total >= 65 else "≤5% (thăm dò)" if total >= 50 else "0% (loại)"

    print(f"\n{C.BOLD}{'═'*58}{C.END}")
    print(f"  {C.BOLD}{s.t}{C.END}  {C.DIM}{s.name}{C.END}")
    print(f"  Giá {C.BOLD}{s.price}{C.END} nghìn đ/cp   {C.DIM}· dữ liệu {s.asof}{C.END}")
    if s.src:
        print(f"  {C.DIM}Nguồn: {s.src}{C.END}")
    if s.missing:
        print(f"  {C.Y}⚠ Chưa lấy được: {s.missing} → nhóm nền tảng/định giá tính 0đ.{C.END}")
        if s.hint:
            print(f"  {C.Y}↳ {s.hint}{C.END}")
    print(f"{C.BOLD}{'═'*58}{C.END}")
    print(f"  ĐIỂM TỔNG: {vcol}{C.BOLD}{total}/100{C.END}  →  {vcol}{verdict(total)}{C.END}\n")

    print(f"  {C.DIM}🕒 TẦM NHÌN{C.END}")
    for lbl, v in [("Ngắn hạn", h["short"]), ("Trung hạn", h["mid"]), ("Dài hạn", h["long"])]:
        bar = "█" * (v // 5) + "░" * (20 - v // 5)
        vc = C.G if v >= 70 else C.Y if v >= 50 else C.R
        star = " ⭐" if (lbl, v) == best else ""
        print(f"    {lbl:<10} {vc}{bar}{C.END} {v}/100{star}")

    fund_labels = {"Tăng trưởng LN", "ROE", "Biên lợi nhuận", "Nợ vay D/E",
                   "Dòng tiền KD", "P/E vs ngành", "P/B", "Cổ tức"}
    print(f"\n  {C.DIM}🧮 CHI TIẾT ĐIỂM{C.END}")
    for c in b["cats"]:
        print(f"    {C.B}{c['cat']:<24}{C.END} {c['sum']}/{c['max']}đ")
        for it in c["items"]:
            cc = _col(it["pts"], it["max"])
            raw = "N/A (chưa lấy được)" if (s.missing and it["l"] in fund_labels) else it["raw"]
            print(f"      {it['l']:<20}{C.DIM}{raw:<22}{C.END}{cc}{it['pts']}/{it['max']}{C.END}")

    print(f"\n  {C.DIM}✅ QUYẾT ĐỊNH{C.END}")
    print(f"    Khung hợp nhất : {C.B}{best[0]}{C.END}")
    print(f"    Tỷ trọng tối đa: {size}    Cắt lỗ: {C.R}−8%{C.END}")
    print(f"    {C.DIM}Định tính (pos/mgmt/cat) đang = {s.pos}/{s.mgmt}/{s.cat} — chỉnh bằng cờ nếu cần.{C.END}")
    print(f"  {C.DIM}⚠️ Hỗ trợ tư duy, không phải khuyến nghị đầu tư.{C.END}\n")


def write_real_data_js(stocks: list[Stock]) -> None:
    """Ghi/gộp du-lieu-thuc.js để phan-tich-ma.html nạp số liệu thật."""
    existing: dict[str, dict] = {}
    if os.path.exists(REAL_DATA_JS):
        try:
            with open(REAL_DATA_JS, encoding="utf-8") as f:
                txt = f.read()
            start, end = txt.find("["), txt.rfind("]")
            if start >= 0 and end > start:
                for row in json.loads(txt[start:end + 1]):
                    existing[row["t"]] = row
        except Exception:
            pass
    for s in stocks:
        existing[s.t] = asdict(s)
    rows = json.dumps(list(existing.values()), ensure_ascii=False, indent=2)
    with open(REAL_DATA_JS, "w", encoding="utf-8") as f:
        f.write("/* Sinh tự động bởi phan_tich_ma.py — số liệu THẬT (vnstock). */\n")
        f.write(f"window.REAL_DB = {rows};\n")
    print(f"  {C.G}✓{C.END} Đã ghi {C.B}{os.path.basename(REAL_DATA_JS)}{C.END} "
          f"({len(existing)} mã) — mở phan-tich-ma.html, gõ mã để xem báo cáo đầy đủ.")


# =============================================================================
# CLI
# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="Crawl + chấm điểm cổ phiếu VN theo mô hình InvestStudio 100 điểm.")
    ap.add_argument("tickers", nargs="+", help="Mã cổ phiếu, VD: FPT VNM HPG")
    ap.add_argument("--pos", type=int, choices=[0, 1, 2], default=1, help="Vị thế ngành (định tính)")
    ap.add_argument("--mgmt", type=int, choices=[0, 1, 2], default=1, help="Ban lãnh đạo (định tính)")
    ap.add_argument("--cat", type=int, choices=[0, 1, 2], default=1, help="Catalyst (định tính)")
    ap.add_argument("--pe-sec", type=float, default=None, help="Ghi đè P/E ngành")
    ap.add_argument("--pb-fair", type=float, default=None, help="Ghi đè P/B hợp lý")
    ap.add_argument("--source", choices=["auto", "vnstock", "cafef"], default="auto",
                    help="Nguồn: auto (CafeF↔vnstock) · vnstock · cafef (chỉ giá/kỹ thuật)")
    ap.add_argument("--no-html", action="store_true", help="Không ghi du-lieu-thuc.js")
    ap.add_argument("--json", action="store_true", help="In JSON thô thay vì báo cáo")
    args = ap.parse_args()

    if args.source == "vnstock":
        try:
            import vnstock  # noqa: F401
        except ImportError:
            print(f"{C.R}Thiếu thư viện vnstock.{C.END} Cài: {C.B}pip install vnstock{C.END} "
                  f"(hoặc dùng {C.B}--source cafef{C.END}).", file=sys.stderr)
            return 1

    results: list[Stock] = []
    for tk in args.tickers:
        try:
            print(f"{C.DIM}… đang crawl {tk.upper()} (nguồn: {args.source}){C.END}", file=sys.stderr)
            s = fetch_stock(tk, pos=args.pos, mgmt=args.mgmt, cat=args.cat,
                            pe_sec=args.pe_sec, pb_fair=args.pb_fair, source=args.source)
            results.append(s)
            if args.json:
                print(json.dumps(asdict(s), ensure_ascii=False, indent=2))
            else:
                print_cli(s)
        except Exception as e:
            print(f"{C.R}✗ {tk.upper()}: {e}{C.END}", file=sys.stderr)

    full = [s for s in results if not s.missing]
    if full and not args.no_html:
        write_real_data_js(full)
        skipped = [s.t for s in results if s.missing]
        if skipped:
            print(f"  {C.Y}⚠ Bỏ ghi web (thiếu cơ bản): {', '.join(skipped)} — chạy --source auto để đủ.{C.END}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
