"""Đánh giá vị thế: đã mua nhiều đợt thì nên mua thêm, giữ, hay cắt lỗ?

⚠️ Chủ ý thiết kế QUAN TRỌNG — quy tắc ở đây cố tình BẤT ĐỐI XỨNG:

"Bình quân giá xuống" là hành vi làm cháy tài khoản phổ biến nhất của nhà đầu tư
mới. Một công cụ tính giá vốn bình quân rất dễ biến thành cái nút hợp thức hóa
việc gồng lỗ: đang lỗ 20%, bấm vào, thấy chữ "mua thêm để hạ giá vốn", rồi đổ
thêm tiền vào một mã đã hỏng.

Vì vậy:
  · Thủng ngưỡng cắt lỗ  → CẮT, bất kể điểm số bao nhiêu.
  · Điểm dưới 50 (yếu)   → CẮT, vì luận điểm đầu tư đã sai.
  · Chỉ khi điểm ≥ 65 VÀ chưa thủng cắt lỗ VÀ tỷ trọng còn dưới trần thì mới
    được gợi ý mua thêm — và luôn kèm cảnh báo rằng mua thêm làm TĂNG số tiền
    đang chịu rủi ro, chứ không "giảm lỗ".

Ngưỡng cắt lỗ và trần tỷ trọng lấy từ `scoring.py` để không có hai bộ quy tắc.
"""
from __future__ import annotations

from typing import Optional

from app.schemas.stock import (
    LotResult,
    PositionAction,
    PositionRequest,
    PositionReview,
)
from app.services import analyzer, scoring
from app.services.scoring import STOP_LOSS_PCT

_ADD_MIN_SCORE = 65   # dưới mức "Tốt" thì không bao giờ gợi ý mua thêm
_CUT_MAX_SCORE = 50   # dưới mức này coi như luận điểm đã sai


def review(ticker: str, request: PositionRequest) -> PositionReview:
    """Chấm lại mã, đối chiếu với các đợt mua thật của người dùng."""
    ticker = ticker.upper().strip()

    analysis = analyzer.analyze(
        ticker, pos=request.pos, mgmt=request.mgmt, cat=request.cat,
        pe_sec=request.pe_sec, pb_fair=request.pb_fair,
    )
    price = analysis.price
    score = analysis.score

    total_quantity = sum(lot.quantity for lot in request.lots)
    total_cost = sum(lot.price * lot.quantity for lot in request.lots)
    avg_cost = total_cost / total_quantity if total_quantity else 0.0

    lots = [
        LotResult(
            price=lot.price,
            quantity=lot.quantity,
            date=lot.date,
            cost=round(lot.price * lot.quantity, 2),
            pnl=round((price - lot.price) * lot.quantity, 2) if price else 0.0,
            pnl_pct=round((price - lot.price) / lot.price * 100, 2) if price else 0.0,
        )
        for lot in request.lots
    ]

    market_value = (price or 0.0) * total_quantity
    pnl = market_value - total_cost
    pnl_pct = (pnl / total_cost * 100) if total_cost else 0.0

    #  Cắt lỗ tính từ GIÁ VỐN BÌNH QUÂN, không phải từ đợt mua gần nhất —
    #  đây mới là mức thực sự phản ánh rủi ro của cả vị thế.
    stop_price = round(avg_cost * (1 - STOP_LOSS_PCT / 100), 2) if avg_cost else None
    stop_breached = bool(price is not None and stop_price is not None and price <= stop_price)

    _, size_max_pct, _ = scoring._size_bracket(score.total)  # noqa: SLF001 - dùng chung ngưỡng
    weight_pct = (round(market_value / request.account_value * 100, 2)
                  if request.account_value else None)

    warnings: list[str] = []
    if pnl < 0:
        warnings.append(
            f"Vị thế đang lỗ {abs(pnl_pct):.2f}%. Mua thêm lúc này làm TĂNG số tiền "
            "đang chịu rủi ro — giá vốn bình quân giảm chỉ là con số kế toán, "
            "khoản lỗ thực tế không hề nhỏ đi."
        )
    if analysis.missing:
        warnings.append(
            "Một phần chỉ số cơ bản chưa lấy được nên điểm đang thấp hơn thực tế. "
            "Đừng cắt lỗ chỉ vì điểm thấp do thiếu dữ liệu."
        )
    if weight_pct is not None and size_max_pct and weight_pct > size_max_pct:
        warnings.append(
            f"Tỷ trọng hiện tại {weight_pct:.2f}% đã vượt trần {size_max_pct:g}% "
            "ứng với mức điểm này — cân nhắc giảm bớt thay vì mua thêm."
        )

    action = _decide(
        total=score.total,
        verdict_text=score.verdict.text,
        stop_breached=stop_breached,
        stop_price=stop_price,
        pnl_pct=pnl_pct,
        weight_pct=weight_pct,
        size_max_pct=size_max_pct,
        has_price=price is not None,
    )

    return PositionReview(
        ticker=ticker,
        current_price=price,
        asof=analysis.asof,
        score_total=score.total,
        verdict=score.verdict.text,
        verdict_level=score.verdict.level,
        total_quantity=total_quantity,
        total_cost=round(total_cost, 2),
        avg_cost=round(avg_cost, 2),
        market_value=round(market_value, 2),
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 2),
        stop_price=stop_price,
        stop_breached=stop_breached,
        weight_pct=weight_pct,
        max_weight_pct=size_max_pct or None,
        lots=lots,
        action=action,
        warnings=warnings,
        note=("Mọi con số tính từ các đợt mua bạn nhập và giá thị trường hiện tại. "
              "Đây là công cụ hỗ trợ tư duy, không phải khuyến nghị mua bán."),
    )


def _decide(
    *,
    total: int,
    verdict_text: str,
    stop_breached: bool,
    stop_price: Optional[float],
    pnl_pct: float,
    weight_pct: Optional[float],
    size_max_pct: float,
    has_price: bool,
) -> PositionAction:
    """Thứ tự kiểm tra có ý nghĩa: kỷ luật đặt trước, cơ hội đặt sau."""
    if not has_price:
        return PositionAction(
            key="none", label="Chưa kết luận được", level="warn",
            reason="Không lấy được giá thị trường hiện tại nên chưa đối chiếu được với giá vốn.",
        )

    #  1. Kỷ luật cắt lỗ đứng trên mọi thứ khác — kể cả khi điểm số vẫn đẹp.
    if stop_breached:
        return PositionAction(
            key="cut", label="Cắt lỗ", level="bad",
            reason=(f"Giá đã thủng ngưỡng cắt lỗ {stop_price:g} (−{STOP_LOSS_PCT:g}% từ giá vốn "
                    f"bình quân). Vị thế đang lỗ {abs(pnl_pct):.2f}%."),
            detail=("Ngưỡng cắt lỗ được đặt ra từ lúc còn bình tĩnh, chính là để dùng cho "
                    "đúng lúc này. Bán trước, phân tích lại sau — mã tốt sẽ luôn còn cơ hội "
                    "mua lại, còn tài khoản cháy thì không."),
        )

    #  2. Luận điểm đầu tư đã sai thì thêm tiền là thêm sai.
    if total < _CUT_MAX_SCORE:
        return PositionAction(
            key="cut", label="Thoát dần", level="bad",
            reason=f"Điểm chỉ {total}/100 — {verdict_text.lower()}. Lý do nắm giữ ban đầu không còn.",
            detail=("Chưa thủng cắt lỗ nên không cần bán vội trong một lệnh, nhưng nên giảm "
                    "dần thay vì chờ đợi trong hy vọng."),
        )

    #  3. Đủ tốt và còn dư địa → mới được nhắc tới chuyện mua thêm.
    room_left = weight_pct is None or not size_max_pct or weight_pct < size_max_pct
    if total >= _ADD_MIN_SCORE and room_left:
        detail = (f"Trần tỷ trọng ứng với mức điểm này là {size_max_pct:g}% tài khoản."
                  if size_max_pct else "")
        if weight_pct is not None:
            detail += f" Hiện bạn đang nắm {weight_pct:.2f}%."
        return PositionAction(
            key="add", label="Có thể mua thêm — nhưng có điều kiện", level="good",
            reason=(f"Điểm {total}/100 — {verdict_text.lower()}, và giá chưa thủng ngưỡng "
                    f"cắt lỗ {stop_price:g}."),
            detail=(detail + " Chỉ mua thêm khi luận điểm ban đầu vẫn đúng, KHÔNG mua thêm "
                    "chỉ để kéo giá vốn xuống. Nếu đang lỗ, hãy hỏi: nếu chưa từng mua mã "
                    "này, hôm nay mình có mua ở giá này không?").strip(),
        )

    #  4. Còn lại: giữ nguyên, không thêm không bớt.
    reason = f"Điểm {total}/100 — {verdict_text.lower()}."
    if not room_left and weight_pct is not None:
        reason += f" Tỷ trọng {weight_pct:.2f}% đã chạm/vượt trần {size_max_pct:g}%."
    return PositionAction(
        key="hold", label="Giữ nguyên, không mua thêm", level="warn",
        reason=reason,
        detail=("Chưa đủ hấp dẫn để tăng tiền, cũng chưa đủ xấu để bán. Giữ nguyên ngưỡng "
                f"cắt lỗ {stop_price:g} và theo dõi thêm."),
    )
