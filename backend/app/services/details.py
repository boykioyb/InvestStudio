"""Dữ liệu chi tiết cho các tab: Hồ sơ · Tài chính · Chỉ số.

Đây là dữ liệu để NGƯỜI DÙNG tự đọc và đối chiếu, KHÔNG tham gia chấm điểm.
Vì vậy để riêng khỏi `analyzer.py` và chỉ tải khi người dùng mở tab tương ứng.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.stock import (
    AnalystView,
    CompanyProfile,
    FinancialStatement,
    Highlight,
    Person,
    RatioGroup,
    RatioItem,
    RatioTable,
    RelatedCompany,
    StatementKey,
    StatementRow,
)
from app.services.providers.base import ProviderError

_BILLION = 1_000_000_000

_STATEMENTS: dict[str, tuple[str, str]] = {
    "income": ("income_statement", "Kết quả kinh doanh"),
    "balance": ("balance_sheet", "Cân đối kế toán"),
    "cashflow": ("cash_flow", "Lưu chuyển tiền tệ"),
}

#  Gộp 54 chỉ số thành nhóm dễ đọc. Khóa là tên tiếng Anh do nguồn trả về.
_RATIO_GROUPS: list[tuple[str, list[str]]] = [
    ("Định giá", ["P/E", "P/B", "P/S", "Price/Cash Flow", "EV/EBITDA",
                  "Market Cap", "Outstanding Shares (mil)", "Dividend Yield (%)"]),
    ("Khả năng sinh lời", ["ROE (%)", "ROA (%)", "ROIC", "Gross Margin (%)", "EBIT Margin (%)",
                           "Pre-tax Profit Margin (%)", "After-tax Profit Margin (%)",
                           "EBIT", "EBITDA"]),
    ("Thanh khoản & đòn bẩy", ["Cash Ratio", "Quick Ratio", "Current Ratio", "Debt/Equity",
                               "Debt to Equity", "Financial Leverage", "Owners Equity"]),
    ("Hiệu quả hoạt động", ["Asset Turnover", "Fixed Asset Turnover", "Cash Cycle",
                            "Days Sales Outstanding", "Days Inventory Outstanding",
                            "Days Payable Outstanding"]),
    ("Riêng ngành ngân hàng", ["Net Interest Margin", "LDR (%)", "NPL (%)", "CIR", "CAR",
                               "Loans Growth (%)", "Deposit Growth (%)", "CASA Ratio",
                               "Loan Loss Reserves/NPLs", "Loan Loss Reserve/Loans",
                               "Provision/Outstanding Loans", "Equity/Total Liabilities",
                               "Equity/Loans", "Equity/Total Assets",
                               "Avg Yield on Earning Assets", "Avg Cost of Financing",
                               "Non-interest Income", "Cost/Income Ratio"]),
]

#  Chỉ số vốn là tỷ lệ 0–1 ở nguồn → hiển thị dạng phần trăm.
_PERCENT_RATIOS = {
    "ROE (%)", "ROA (%)", "ROIC", "Gross Margin (%)", "EBIT Margin (%)",
    "Pre-tax Profit Margin (%)", "After-tax Profit Margin (%)", "Dividend Yield (%)",
    "Net Interest Margin", "LDR (%)", "NPL (%)", "CASA Ratio",
    "Loans Growth (%)", "Deposit Growth (%)",
}

#  Dòng kỹ thuật của nguồn, không phải chỉ số tài chính → ẩn đi.
_RATIO_SKIP = {"Ratio TTM Id", "Ratio Type", "Ratio Year Id"}

#  Chỉ số có giá trị rất lớn → quy về đơn vị đọc được (hệ số chia, hậu tố).
_RATIO_SCALE: dict[str, tuple[float, str]] = {
    "Market Cap": (_BILLION, "tỷ đồng"),
    "EBIT": (_BILLION, "tỷ đồng"),
    "EBITDA": (_BILLION, "tỷ đồng"),
    "Outstanding Shares (mil)": (1_000_000, "triệu cp"),
    "Non-interest Income": (_BILLION, "tỷ đồng"),
}


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number  # loại NaN
    except (TypeError, ValueError):
        return None


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return fallback if text.lower() in ("", "nan", "none") else text


def _percent(value: Any, digits: int = 2) -> Optional[float]:
    """Nguồn trả tỷ lệ dạng 0–1 → đổi sang phần trăm."""
    number = _to_float(value)
    return None if number is None else round(number * 100, digits)


def fetch_profile(ticker: str) -> CompanyProfile:
    """Hồ sơ doanh nghiệp: tổng quan, lãnh đạo, cổ đông, công ty con/liên kết."""
    try:
        from vnstock import Company
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    ticker = ticker.upper().strip()
    try:
        company = Company(symbol=ticker, source="VCI")
        overview = company.overview()
    except Exception as exc:
        raise ProviderError(f"Không lấy được hồ sơ của {ticker}: {exc}") from exc

    if overview is None or len(overview) == 0:
        raise ProviderError(f"Không có hồ sơ doanh nghiệp cho {ticker}.")

    row: dict[str, Any] = overview.iloc[0].to_dict()

    highlights: list[Highlight] = []

    def add(label: str, value: Optional[str], note: str = "") -> None:
        if value:
            highlights.append(Highlight(label=label, value=value, note=note))

    high_1y, low_1y = _to_float(row.get("highest_price1_year")), _to_float(row.get("lowest_price1_year"))
    if high_1y and low_1y:
        add("Đỉnh / đáy 1 năm", f"{high_1y / 1000:,.2f} / {low_1y / 1000:,.2f}", "nghìn đ/cp")

    avg_vol = _to_float(row.get("average_match_volume1_month"))
    if avg_vol:
        add("KL khớp TB 1 tháng", f"{avg_vol / 1_000_000:,.2f} triệu cp/phiên")

    avg_val = _to_float(row.get("average_match_value1_month"))
    if avg_val:
        add("GT khớp TB 1 tháng", f"{avg_val / _BILLION:,.0f} tỷ đồng/phiên")

    foreign = _percent(row.get("foreigner_percentage"))
    room = _percent(row.get("maximum_foreign_percentage"))
    if foreign is not None:
        add("Sở hữu nước ngoài", f"{foreign}%",
            f"trần cho phép {room}%" if room is not None else "")

    state = _percent(row.get("state_percentage"))
    if state is not None:
        add("Sở hữu nhà nước", f"{state}%")

    free_float = _percent(row.get("free_float_percentage"))
    if free_float is not None:
        add("Tỷ lệ cổ phiếu tự do chuyển nhượng", f"{free_float}%",
            "phần thực sự giao dịch trên sàn")

    analyst: Optional[AnalystView] = None
    rating = _clean(row.get("rating"))
    if rating:
        target = _to_float(row.get("target_price"))
        analyst = AnalystView(
            source="Vietcap (VCI) — khuyến nghị của công ty chứng khoán, không phải của công cụ này",
            rating=rating,
            target_price=round(target / 1000, 2) if target else None,
            upside_pct=_percent(row.get("upside_to_target_percent"), 1),
            analyst=_clean(row.get("analyst")),
            as_of=_clean(row.get("rating_as_of")),
        )

    def people(frame, name_col: str, position_col: str = "") -> list[Person]:
        if frame is None or len(frame) == 0:
            return []
        result: list[Person] = []
        for record in frame.to_dict("records"):
            name = _clean(record.get(name_col))
            if not name:
                continue
            result.append(Person(
                name=name,
                position=_clean(record.get(position_col)) if position_col else "",
                percent=_percent(record.get("officer_own_percent") or record.get("share_own_percent")),
                quantity=_to_float(record.get("officer_own_quantity") or record.get("quantity")),
            ))
        return result

    def safe(getter) -> Any:
        try:
            return getter()
        except Exception:
            return None

    officers = people(safe(company.officers), "officer_name", "officer_position")
    shareholders = people(safe(company.shareholders), "share_holder")

    subsidiaries: list[RelatedCompany] = []
    subs = safe(company.subsidiaries)
    if subs is not None and len(subs):
        subsidiaries = [
            RelatedCompany(name=_clean(r.get("organ_name")), code=_clean(r.get("sub_organ_code")),
                           percent=_percent(r.get("ownership_percent")))
            for r in subs.to_dict("records") if _clean(r.get("organ_name"))
        ]

    affiliates: list[RelatedCompany] = []
    affs = safe(company.affiliate)
    if affs is not None and len(affs):
        affiliates = [
            RelatedCompany(name=_clean(r.get("right_organ_name_vi") or r.get("right_organ_name_en")),
                           code=_clean(r.get("right_ticker") or r.get("right_organ_code")),
                           percent=_percent(r.get("owned_percentage")))
            for r in affs.to_dict("records")
            if _clean(r.get("right_organ_name_vi") or r.get("right_organ_name_en"))
        ]

    return CompanyProfile(
        ticker=ticker,
        name=_clean(row.get("organ_name"), ticker),
        short_name=_clean(row.get("organ_short_name")),
        sector=_clean(row.get("sector") or row.get("industry")),
        exchange=_clean(row.get("com_group_code")),
        listing_date=_clean(row.get("listing_date"))[:10],
        highlights=highlights,
        analyst=analyst,
        officers=sorted(officers, key=lambda p: p.percent or 0, reverse=True)[:12],
        shareholders=sorted(shareholders, key=lambda p: p.percent or 0, reverse=True)[:15],
        subsidiaries=sorted(subsidiaries, key=lambda c: c.percent or 0, reverse=True)[:20],
        affiliates=sorted(affiliates, key=lambda c: c.percent or 0, reverse=True)[:20],
    )


def fetch_statement(ticker: str, statement: StatementKey) -> FinancialStatement:
    """Một báo cáo tài chính, nhãn tiếng Việt, đơn vị tỷ đồng."""
    try:
        from vnstock import Finance
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    ticker = ticker.upper().strip()
    method_name, title = _STATEMENTS[statement]

    try:
        frame = getattr(Finance(symbol=ticker, source="VCI"), method_name)(
            period="year", lang="vi", dropna=False)
    except Exception as exc:
        raise ProviderError(f"Không lấy được {title.lower()} của {ticker}: {exc}") from exc

    if frame is None or len(frame) == 0:
        raise ProviderError(f"Không có {title.lower()} cho {ticker}.")

    periods = [str(c) for c in frame.columns if str(c).isdigit()]
    if not periods:
        raise ProviderError(f"Nguồn không trả kỳ báo cáo nào cho {ticker}.")

    label_col = "item" if "item" in frame.columns else "item_en"
    rows: list[StatementRow] = []
    for record in frame.to_dict("records"):
        label = _clean(record.get(label_col))
        values = [_to_float(record.get(p)) for p in periods]
        #  Bỏ dòng rỗng hoàn toàn để bảng không bị loãng.
        if label and any(v is not None for v in values):
            rows.append(StatementRow(
                label=label,
                values=[round(v / _BILLION, 2) if v is not None else None for v in values],
            ))

    return FinancialStatement(
        ticker=ticker,
        statement=statement,
        title=title,
        unit="tỷ đồng",
        periods=periods,
        rows=rows,
        note="Bản miễn phí của nguồn giới hạn tối đa 4 kỳ gần nhất.",
    )


def fetch_ratios(ticker: str) -> RatioTable:
    """Bộ chỉ số tài chính kỳ gần nhất, gom nhóm cho dễ đọc.

    CHỈ lấy kỳ gần nhất: nguồn trả nhiều cột nhưng nhãn năm bị trùng lặp nên
    không thể gán năm một cách chắc chắn — thà hiển thị một kỳ đúng còn hơn
    bốn kỳ gán sai năm.
    """
    try:
        from vnstock import Finance
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("Chưa cài thư viện vnstock") from exc

    ticker = ticker.upper().strip()
    try:
        frame = Finance(symbol=ticker, source="VCI").ratio(
            period="year", lang="vi", dropna=False)
    except Exception as exc:
        raise ProviderError(f"Không lấy được chỉ số của {ticker}: {exc}") from exc

    if frame is None or len(frame) == 0:
        raise ProviderError(f"Không có chỉ số tài chính cho {ticker}.")

    columns = list(frame.columns)
    en_index = columns.index("item_en") if "item_en" in columns else 0
    vi_index = columns.index("item") if "item" in columns else en_index

    #  Cột cuối = kỳ gần nhất (TTM) — đã đối chiếu với P/E hiển thị ở tab phân tích.
    by_key: dict[str, tuple[str, Optional[float]]] = {}
    for i in range(len(frame)):
        key = _clean(frame.iloc[i, en_index])
        if not key or key in _RATIO_SKIP:
            continue
        by_key[key] = (_clean(frame.iloc[i, vi_index], key), _to_float(frame.iloc[i, -1]))

    groups: list[RatioGroup] = []
    used: set[str] = set()
    for group_name, keys in _RATIO_GROUPS:
        items: list[RatioItem] = []
        for key in keys:
            if key not in by_key:
                continue
            used.add(key)
            label, value = by_key[key]
            is_percent = key in _PERCENT_RATIOS
            #  Nhóm ngân hàng trả 0 cho doanh nghiệp thường → bỏ cho đỡ nhiễu.
            if group_name.startswith("Riêng ngành ngân hàng") and not value:
                continue
            if value is not None and is_percent:
                shown, suffix = round(value * 100, 2), ""
            elif value is not None and key in _RATIO_SCALE:
                divisor, suffix = _RATIO_SCALE[key]
                shown = round(value / divisor, 2)
            else:
                shown, suffix = (round(value, 2) if value is not None else None), ""
            items.append(RatioItem(label=label, value=shown, percent=is_percent, unit=suffix))
        if items:
            groups.append(RatioGroup(name=group_name, items=items))

    others = [
        RatioItem(label=by_key[k][0], value=round(by_key[k][1], 2))
        for k in by_key if k not in used and by_key[k][1] is not None
    ]
    if others:
        groups.append(RatioGroup(name="Khác", items=others))

    return RatioTable(
        ticker=ticker,
        period_label="Kỳ gần nhất (TTM — bốn quý gần nhất)",
        groups=groups,
    )
