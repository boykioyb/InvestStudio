"""Orchestrator: gộp dữ liệu nhiều nguồn → Metrics → gọi bộ chấm điểm.

Tách theo KHỐI, mỗi khối có nguồn chính + dự phòng riêng:
  · Kỹ thuật  : CafeF (JSON sạch, nhanh) → vnstock
  · Cơ bản    : vnstock VCI → vnstock KBS
Nhờ vậy hỏng một nguồn vẫn ra được phần còn lại; tiêu chí thật sự thiếu sẽ
được đánh dấu `available=False` và tính 0đ (xem scoring.py).
"""
from __future__ import annotations

from typing import Callable, Optional

from app.schemas.stock import Metrics, SourceMode, StockAnalysis
from app.services import scoring
from app.services.providers import cafef, vnstock_source
from app.services.providers.base import FundamentalData, ProviderError, TechnicalData

# P/E ngành & P/B hợp lý — ƯỚC LƯỢNG benchmark thị trường VN, không phải số crawl.
# Người dùng có thể ghi đè qua tham số pe_sec / pb_fair.
_SECTOR_BENCHMARK: dict[str, tuple[float, float]] = {
    "ngan hang": (9.0, 1.6), "bank": (9.0, 1.6),
    "bat dong san": (16.0, 1.5), "real estate": (16.0, 1.5),
    "cong nghe": (18.0, 3.5), "technology": (18.0, 3.5),
    "information technology": (18.0, 3.5),
    "ban le": (17.0, 2.5), "retail": (17.0, 2.5),
    "thep": (12.0, 1.4), "vat lieu": (13.0, 1.6), "materials": (13.0, 1.6),
    "dau khi": (10.0, 1.3), "nang luong": (11.0, 1.4), "energy": (11.0, 1.4),
    "tien ich": (12.0, 1.6), "dien": (12.0, 1.6), "utilities": (12.0, 1.6),
    "tieu dung": (16.0, 2.8), "consumer": (16.0, 2.8),
    "chung khoan": (13.0, 1.8), "securities": (13.0, 1.8),
}
_DEFAULT_BENCHMARK = (15.0, 2.0)

_FUNDAMENTAL_LABELS = ["Tăng trưởng", "ROE", "Biên LN", "D/E", "Dòng tiền", "P/E", "P/B", "Cổ tức"]


def _benchmark(sector: str) -> tuple[float, float]:
    key = (sector or "").strip().lower()
    for name, values in _SECTOR_BENCHMARK.items():
        if name in key:
            return values
    return _DEFAULT_BENCHMARK


def _first_success(
    candidates: list[tuple[str, Callable[[], object]]],
    used: list[str],
    tag: str,
) -> Optional[object]:
    """Chạy lần lượt các nguồn, lấy kết quả đầu tiên thành công."""
    for label, fetch in candidates:
        try:
            result = fetch()
            used.append(f"{label}({tag})")
            return result
        except ProviderError:
            continue
        except Exception:
            continue
    return None


#  Mốc phần trăm gắn với từng bước THẬT của quy trình (không phải đồng hồ đếm).
#  Phần trăm nhảy khi bước đó bắt đầu, nên người dùng luôn thấy việc đang chạy.
ProgressFn = Callable[[str, str, int], None]  # (mã bước, mô tả, phần trăm)


def _noop_progress(step: str, label: str, percent: int) -> None:
    """Mặc định: không báo tiến độ (dùng cho endpoint thường)."""


def analyze(
    ticker: str,
    *,
    pos: int = 1,
    mgmt: int = 1,
    cat: int = 1,
    pe_sec: Optional[float] = None,
    pb_fair: Optional[float] = None,
    source: SourceMode = "auto",
    on_progress: Optional[ProgressFn] = None,
) -> StockAnalysis:
    """Phân tích 1 mã: crawl → Metrics → chấm điểm. Raise ProviderError nếu
    không lấy nổi cả khối kỹ thuật (không có giá thì không phân tích được).

    `on_progress` được gọi khi mỗi bước THẬT bắt đầu, dùng cho endpoint stream.
    """
    progress = on_progress or _noop_progress
    ticker = ticker.upper().strip()
    used: list[str] = []

    # --- Khối kỹ thuật (bắt buộc) ---
    progress("technical", "Lấy lịch sử giá và tính chỉ báo kỹ thuật", 10)
    if source == "vnstock":
        tech_sources = [("vnstock", lambda: vnstock_source.fetch_technical(ticker))]
    elif source == "cafef":
        tech_sources = [("CafeF", lambda: cafef.fetch_technical(ticker))]
    else:
        tech_sources = [
            ("CafeF", lambda: cafef.fetch_technical(ticker)),
            ("vnstock", lambda: vnstock_source.fetch_technical(ticker)),
        ]
    technical: Optional[TechnicalData] = _first_success(tech_sources, used, "giá/kỹ thuật")  # type: ignore[assignment]
    if technical is None:
        raise ProviderError(
            f"Không lấy được dữ liệu giá cho {ticker} từ mọi nguồn. "
            "Kiểm tra mã có đúng không, hoặc thử lại sau.")

    # --- Khối cơ bản (tùy chọn — thiếu thì chấm 0đ, có ghi chú) ---
    fundamentals: Optional[FundamentalData] = None
    name, sector, hint = ticker, "—", ""
    if source == "cafef":
        hint = ("Chế độ 'cafef' chỉ lấy giá/kỹ thuật. Dùng nguồn 'auto' để có "
                "đủ chỉ số cơ bản.")
    else:
        progress("company", "Đọc hồ sơ doanh nghiệp và ngành", 45)
        name, sector = vnstock_source.fetch_company(ticker)
        progress("fundamentals", "Lấy báo cáo tài chính (KQKD, cân đối, lưu chuyển tiền)", 55)
        fundamentals = _first_success(  # type: ignore[assignment]
            [(f"vnstock/{src}", lambda src=src: vnstock_source.fetch_fundamentals(ticker, src))
             for src in ("VCI", "KBS")],
            used, "cơ bản")
        if fundamentals is None:
            hint = (f"Không lấy được báo cáo tài chính của {ticker} "
                    "(mã lạ / mới niêm yết / nguồn lỗi tạm thời).")

    progress("scoring", "Chấm điểm 14 tiêu chí và dựng kết luận", 90)
    data = fundamentals or FundamentalData()
    default_pe, default_pb = _benchmark(sector)
    metrics = Metrics(
        growth=data.growth, roe=data.roe, margin=data.margin, de=data.de, ocf=data.ocf,
        pe=data.pe,
        pe_sec=pe_sec if pe_sec is not None else default_pe,
        pb=data.pb,
        pb_fair=pb_fair if pb_fair is not None else default_pb,
        div=data.div,
        trend=technical.trend, vol=technical.vol, rsi=technical.rsi,
        pos=pos, mgmt=mgmt, cat=cat,
    )

    result = StockAnalysis(
        ticker=ticker,
        name=f"{name} — {sector}" if sector != "—" else name,
        sector=sector,
        price=technical.price,
        asof=technical.asof,
        sources=used,
        missing=[] if fundamentals else _FUNDAMENTAL_LABELS,
        hint=hint,
        prices=technical.prices,
        metrics=metrics,
        score=scoring.compute_score(ticker, metrics, technical.price),
    )
    progress("done", "Hoàn tất", 100)
    return result
