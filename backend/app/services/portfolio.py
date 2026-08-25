"""Tổng quan danh mục (B‑lite): gộp nhiều mã, chỉ lấy GIÁ HIỆN TẠI để tính lãi/lỗ.

Chủ ý: KHÔNG chạy `analyzer.analyze` nặng cho từng mã (điểm số/khuyến nghị vẫn
xem ở tab từng mã). Ở đây chỉ cần giá → giá trị thị trường → lãi/lỗ, nên dùng
`vci_direct.price_board` lấy giá **cả danh mục trong MỘT request** (tôn trọng hạn
mức ~20 req/phút của nguồn). Toàn bộ số học nằm ở tầng service này, không có logic
chấm điểm.
"""
from __future__ import annotations

from app.schemas.stock import (
    PortfolioError,
    PortfolioRequest,
    PortfolioReview,
    PortfolioRow,
    PortfolioTotals,
)


def review(request: PortfolioRequest) -> PortfolioReview:
    """Đối chiếu các đợt mua của người dùng với giá hiện tại của cả danh mục."""
    from app.services.providers import vci_direct
    from app.services.providers.vci_direct import VciError

    tickers = [h.ticker.upper().strip() for h in request.holdings]

    #  MỘT request cho cả danh mục: {mã: (giá nghìn đ, có phải giá tham chiếu)}.
    prices: dict[str, tuple[float | None, bool]] = {}
    errors: list[PortfolioError] = []
    try:
        for rec in vci_direct.price_board(tickers):
            sym = rec.get("symbol")
            if not sym:
                continue
            match, ref = rec.get("match_price"), rec.get("ref_price")
            raw = match if match else ref
            price = round(float(raw) / 1000, 2) if raw else None
            prices[sym] = (price, match is None or match == 0)
    except VciError as exc:
        #  Không lấy được giá cho cả danh mục → vẫn trả về vốn/SL, lãi/lỗ để trống.
        errors.append(PortfolioError(ticker="*", message=f"Không lấy được bảng giá: {exc}"))

    #  Tên + sàn (1 request nữa, không bắt buộc — thiếu vẫn hiển thị theo mã).
    directory: dict = {}
    try:
        directory = vci_direct.symbol_directory()
    except VciError:
        directory = {}

    account = request.account_value
    rows: list[PortfolioRow] = []
    sum_cost = 0.0
    sum_mv = 0.0
    priced = winners = losers = 0
    in_session = False

    for holding in request.holdings:
        code = holding.ticker.upper().strip()
        quantity = sum(lot.quantity for lot in holding.lots)
        total_cost = sum(lot.price * lot.quantity for lot in holding.lots)
        avg_cost = total_cost / quantity if quantity else 0.0
        sum_cost += total_cost

        current, is_ref = prices.get(code, (None, False))
        info = directory.get(code) or {}

        row = PortfolioRow(
            ticker=code,
            name=info.get("name") or "",
            quantity=quantity,
            avg_cost=round(avg_cost, 2),
            total_cost=round(total_cost, 2),
            current_price=current,
            price_is_ref=is_ref,
        )

        if current is not None:
            priced += 1
            if not is_ref:
                in_session = True
            market_value = current * quantity
            pnl = market_value - total_cost
            sum_mv += market_value
            row.market_value = round(market_value, 2)
            row.pnl = round(pnl, 2)
            row.pnl_pct = round(pnl / total_cost * 100, 2) if total_cost else 0.0
            if account:
                row.weight_pct = round(market_value / account * 100, 2)
            if pnl > 0:
                winners += 1
            elif pnl < 0:
                losers += 1

        rows.append(row)

    total_pnl = sum_mv - sum(r.total_cost for r in rows if r.current_price is not None)
    priced_cost = sum(r.total_cost for r in rows if r.current_price is not None)
    totals = PortfolioTotals(
        total_cost=round(sum_cost, 2),
        market_value=round(sum_mv, 2),
        pnl=round(total_pnl, 2),
        pnl_pct=round(total_pnl / priced_cost * 100, 2) if priced_cost else 0.0,
        positions=len(rows),
        priced=priced,
        winners=winners,
        losers=losers,
    )

    if not priced:
        note = ("Chưa lấy được giá cho mã nào — chỉ hiển thị vốn đã bỏ ra. "
                "Thử lại sau hoặc kiểm tra kết nối nguồn.")
    elif not in_session:
        note = ("Ngoài phiên: lãi/lỗ tính theo GIÁ THAM CHIẾU (đóng cửa phiên gần nhất). "
                "Điểm số & khuyến nghị từng mã xem trong tab của mã đó.")
    else:
        note = ("Lãi/lỗ theo giá khớp hiện tại. Đây là công cụ hỗ trợ tư duy, "
                "không phải khuyến nghị mua bán.")

    return PortfolioReview(
        in_session=in_session,
        rows=rows,
        totals=totals,
        errors=errors,
        note=note,
    )
