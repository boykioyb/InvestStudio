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
    "income": ("INCOME_STATEMENT", "Kết quả kinh doanh"),
    "balance": ("BALANCE_SHEET", "Cân đối kế toán"),
    "cashflow": ("CASH_FLOW", "Lưu chuyển tiền tệ"),
}

#  Field camelCase của VCI → (nhãn tiếng Anh để gom nhóm, nhãn tiếng Việt để hiện).
_RATIO_FIELD_MAP: dict[str, tuple[str, str]] = {
    "pe": ("P/E", "P/E"), "pb": ("P/B", "P/B"), "ps": ("P/S", "P/S"),
    "priceToCashFlow": ("Price/Cash Flow", "Giá/Dòng tiền"),
    "evToEbitda": ("EV/EBITDA", "EV/EBITDA"),
    "marketCap": ("Market Cap", "Vốn hóa"),
    "numberOfSharesMktCap": ("Outstanding Shares (mil)", "Số CP lưu hành"),
    "dividendYield": ("Dividend Yield (%)", "Tỷ suất cổ tức"),
    "roe": ("ROE (%)", "ROE"), "roa": ("ROA (%)", "ROA"), "roic": ("ROIC", "ROIC"),
    "grossMargin": ("Gross Margin (%)", "Biên LN gộp"),
    "ebitMargin": ("EBIT Margin (%)", "Biên EBIT"),
    "preTaxProfitMargin": ("Pre-tax Profit Margin (%)", "Biên LN trước thuế"),
    "afterTaxProfitMargin": ("After-tax Profit Margin (%)", "Biên LN sau thuế"),
    "ebit": ("EBIT", "EBIT"), "ebitda": ("EBITDA", "EBITDA"),
    "cashRatio": ("Cash Ratio", "Thanh toán tiền mặt"),
    "quickRatio": ("Quick Ratio", "Thanh toán nhanh"),
    "currentRatio": ("Current Ratio", "Thanh toán hiện hành"),
    "debtPerEquity": ("Debt/Equity", "Nợ/Vốn chủ"),
    "debtToEquity": ("Debt to Equity", "Nợ trên vốn chủ"),
    "financialLeverage": ("Financial Leverage", "Đòn bẩy tài chính"),
    "ownersEquity": ("Owners Equity", "Vốn chủ sở hữu"),
    "assetTurnover": ("Asset Turnover", "Vòng quay tài sản"),
    "fixedAssetTurnover": ("Fixed Asset Turnover", "Vòng quay TSCĐ"),
    "cashCycle": ("Cash Cycle", "Chu kỳ tiền"),
    "daySaleOutstanding": ("Days Sales Outstanding", "Số ngày phải thu"),
    "daysInventoryOutstanding": ("Days Inventory Outstanding", "Số ngày tồn kho"),
    "daysPayableOutstanding": ("Days Payable Outstanding", "Số ngày phải trả"),
    "netInterestMargin": ("Net Interest Margin", "Biên lãi thuần (NIM)"),
    "ldrLoanDepositRatio": ("LDR (%)", "LDR"), "npl": ("NPL (%)", "Nợ xấu"),
    "cir": ("CIR", "CIR"), "car": ("CAR", "CAR"),
    "loansGrowth": ("Loans Growth (%)", "Tăng trưởng cho vay"),
    "depositGrowth": ("Deposit Growth (%)", "Tăng trưởng tiền gửi"),
    "casaRatio": ("CASA Ratio", "Tỷ lệ CASA"),
    "loansLossReservesToNPLs": ("Loan Loss Reserves/NPLs", "DP rủi ro/Nợ xấu"),
    "loansLossReserveToLoans": ("Loan Loss Reserve/Loans", "DP rủi ro/Cho vay"),
    "provisionToOutstandingLoans": ("Provision/Outstanding Loans", "Trích lập DP/Cho vay"),
    "equityToLiabilities": ("Equity/Total Liabilities", "Vốn chủ/Tổng nợ"),
    "equityToLoans": ("Equity/Loans", "Vốn chủ/Cho vay"),
    "totalEquityTotalAsset": ("Equity/Total Assets", "Vốn chủ/Tổng tài sản"),
    "averageYieldOnEarningAssets": ("Avg Yield on Earning Assets", "LS bình quân TS sinh lãi"),
    "averageCostOfFinancing": ("Avg Cost of Financing", "Chi phí vốn bình quân"),
    "nonAndInterestIncome": ("Non-interest Income", "Thu nhập ngoài lãi"),
    "costToIncome": ("Cost/Income Ratio", "Chi phí/Thu nhập"),
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
    """Hồ sơ doanh nghiệp (thẳng VCI): tổng quan, lãnh đạo, cổ đông, công ty con/liên kết."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()
    try:
        p = vci_direct.company_profile(ticker)
        holders = vci_direct.shareholders(ticker)
        rel = vci_direct.relationships(ticker)
    except VciError as exc:
        raise ProviderError(f"Không lấy được hồ sơ của {ticker}: {exc}") from exc

    if not p:
        raise ProviderError(f"Không có hồ sơ doanh nghiệp cho {ticker}.")

    highlights: list[Highlight] = []

    def add(label: str, value: Optional[str], note: str = "") -> None:
        if value:
            highlights.append(Highlight(label=label, value=value, note=note))

    high_1y, low_1y = _to_float(p.get("highestPrice1Year")), _to_float(p.get("lowestPrice1Year"))
    if high_1y and low_1y:
        add("Đỉnh / đáy 1 năm", f"{high_1y / 1000:,.2f} / {low_1y / 1000:,.2f}", "nghìn đ/cp")

    avg_vol = _to_float(p.get("averageMatchVolume1Month"))
    if avg_vol:
        add("KL khớp TB 1 tháng", f"{avg_vol / 1_000_000:,.2f} triệu cp/phiên")

    avg_val = _to_float(p.get("averageMatchValue1Month"))
    if avg_val:
        add("GT khớp TB 1 tháng", f"{avg_val / _BILLION:,.0f} tỷ đồng/phiên")

    foreign = _percent(p.get("foreignerPercentage"))
    room = _percent(p.get("maximumForeignPercentage"))
    if foreign is not None:
        add("Sở hữu nước ngoài", f"{foreign}%",
            f"trần cho phép {room}%" if room is not None else "")

    state = _percent(p.get("statePercentage"))
    if state is not None:
        add("Sở hữu nhà nước", f"{state}%")

    analyst: Optional[AnalystView] = None
    rating = _clean(p.get("rating"))
    if rating:
        target = _to_float(p.get("targetPrice"))
        analyst = AnalystView(
            source="Vietcap (VCI) — khuyến nghị của công ty chứng khoán, không phải của công cụ này",
            rating=rating,
            target_price=round(target / 1000, 2) if target else None,
            upside_pct=_percent(p.get("upsideToTargetPercent"), 1),
            analyst=_clean(p.get("analyst")),
            as_of=_clean(p.get("ratingAsOf"))[:10],
        )

    def person(h: dict) -> Person:
        return Person(name=_clean(h.get("name")), position=_clean(h.get("position")),
                      percent=_percent(h.get("percent")), quantity=_to_float(h.get("quantity")))

    officers = [person(h) for h in holders if _clean(h.get("position"))]
    shareholders = [person(h) for h in holders if _clean(h.get("name"))]
    subsidiaries = [RelatedCompany(name=_clean(s["name"]), code=_clean(s["code"]),
                                   percent=_percent(s["percent"])) for s in rel["subsidiaries"]]
    affiliates = [RelatedCompany(name=_clean(a["name"]), code=_clean(a["code"]),
                                 percent=_percent(a["percent"])) for a in rel["affiliates"]]

    return CompanyProfile(
        ticker=ticker,
        name=_clean(p.get("name"), ticker),
        short_name=_clean(p.get("viOrganShortName")),
        sector=_clean(p.get("sector_vn") or p.get("sector")),
        exchange=_clean(p.get("comGroupCode")),
        listing_date="",
        highlights=highlights,
        analyst=analyst,
        officers=sorted(officers, key=lambda p: p.percent or 0, reverse=True)[:12],
        shareholders=sorted(shareholders, key=lambda p: p.percent or 0, reverse=True)[:15],
        subsidiaries=sorted(subsidiaries, key=lambda c: c.percent or 0, reverse=True)[:20],
        affiliates=sorted(affiliates, key=lambda c: c.percent or 0, reverse=True)[:20],
    )


def fetch_statement(ticker: str, statement: StatementKey) -> FinancialStatement:
    """Một báo cáo tài chính (thẳng VCI), nhãn tiếng Việt, đơn vị tỷ đồng."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()
    section, title = _STATEMENTS[statement]

    try:
        data = vci_direct.financial_statement(ticker, section)
    except VciError as exc:
        raise ProviderError(f"Không lấy được {title.lower()} của {ticker}: {exc}") from exc

    periods = data["periods"]
    if not periods:
        raise ProviderError(f"Không có {title.lower()} cho {ticker}.")

    rows = [
        StatementRow(
            label=row["label"],
            values=[round(v / _BILLION, 2) if v is not None else None for v in row["values"]],
        )
        for row in data["rows"] if row["label"]
    ]

    return FinancialStatement(
        ticker=ticker, statement=statement, title=title, unit="tỷ đồng",
        periods=periods, rows=rows,
        note="Báo cáo năm từ VCI (tối đa 4 kỳ gần nhất).",
    )


def fetch_ratios(ticker: str) -> RatioTable:
    """Bộ chỉ số tài chính kỳ gần nhất, gom nhóm cho dễ đọc.

    CHỈ lấy kỳ gần nhất: nguồn trả nhiều cột nhưng nhãn năm bị trùng lặp nên
    không thể gán năm một cách chắc chắn — thà hiển thị một kỳ đúng còn hơn
    bốn kỳ gán sai năm.
    """
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    ticker = ticker.upper().strip()
    try:
        raw = vci_direct.ratios_latest(ticker)
    except VciError as exc:
        raise ProviderError(f"Không lấy được chỉ số của {ticker}: {exc}") from exc

    if not raw:
        raise ProviderError(f"Không có chỉ số tài chính cho {ticker}.")

    #  Field camelCase của VCI → (nhãn Anh để gom nhóm, nhãn Việt để hiện).
    by_key: dict[str, tuple[str, Optional[float]]] = {}
    for field, value in raw.items():
        mapping = _RATIO_FIELD_MAP.get(field)
        if not mapping or value is None:
            continue
        en_label, vi_label = mapping
        by_key[en_label] = (vi_label, _to_float(value))

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
        period_label="Chỉ số năm gần nhất (P/E, P/B theo TTM hiện tại)",
        groups=groups,
    )
