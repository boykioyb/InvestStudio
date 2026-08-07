"""NGUỒN SỰ THẬT DUY NHẤT của mô hình chấm điểm 100 điểm.

⚠️ KHÔNG được nhân bản logic này sang frontend hay bất kỳ nơi nào khác.
Frontend chỉ render kết quả trả về từ đây. Muốn đổi tiêu chí/ngưỡng/công thức
→ sửa DUY NHẤT file này (và bảng khai báo trong `criteria.py`).

Mô hình: 14 tiêu chí / 4 nhóm — xem `criteria.py` để biết ngưỡng từng tiêu chí.
  · Nền tảng & tài chính 45đ · Định giá 20đ · Kỹ thuật 20đ · Định tính 15đ

Hai nguyên tắc:
  1. Chỉ số không lấy được (None) → 0đ và `available=False`. KHÔNG bịa số, không
     cho điểm "miễn phí". Bảo thủ có chủ đích.
  2. Mọi lời giải thích (`Explain`) được sinh TỪ CHÍNH ngưỡng dùng để chấm, nên
     thang điểm hiển thị luôn khớp với điểm thực nhận.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from app.schemas.stock import (
    BestHorizon,
    Decision,
    Explain,
    Horizon,
    Level,
    Metrics,
    Risk,
    Score,
    ScoreCategory,
    ScoreItem,
    Verdict,
    WorstCase,
)
from app.services import criteria
from app.services.criteria import CriterionSpec


def _round_half_up(value: float) -> int:
    """Làm tròn NỬA LÊN (2.5 → 3).

    Cố ý KHÔNG dùng round() của Python (banker's rounding: 2.5 → 2) vì mô hình
    gốc dùng Math.round của JS. Khác biệt này từng gây lệch 1–2 điểm ở các tiêu
    chí có điểm tối đa lẻ (P/B 5, cổ tức 5, ban lãnh đạo 5).
    """
    return math.floor(value + 0.5)


def _points(level: int, maximum: int) -> int:
    """Mức 2 → full điểm, mức 1 → nửa điểm (làm tròn lên), mức 0 → 0đ."""
    if level >= 2:
        return maximum
    if level == 1:
        return _round_half_up(maximum / 2)
    return 0


_NA_RAW = "N/A (chưa lấy được)"


def _scale_text(spec: CriterionSpec) -> list[str]:
    """Thang điểm hiển thị — sinh từ chính các band dùng để chấm."""
    return [f"{band.text} → {_points(band.level, spec.max)}/{spec.max}đ" for band in spec.bands]


def _build_item(spec: CriterionSpec, *values: Optional[object]) -> ScoreItem:
    """Chấm một tiêu chí và soạn luôn phần giải thích kèm dẫn chứng."""
    scale = _scale_text(spec)

    if any(v is None for v in values):
        reason = ("Mục này bạn tự chấm trong Tùy chọn."
                  if spec.manual else
                  "Chưa lấy được dữ liệu từ nguồn nên tạm tính 0 điểm — đây là cách tính bảo thủ, "
                  "KHÔNG có nghĩa doanh nghiệp yếu. Hãy tra báo cáo tài chính gốc để tự đối chiếu.")
        return ScoreItem(
            label=spec.label, raw=_NA_RAW, level=0, points=0, max=spec.max, available=False,
            explain=Explain(what=spec.what, why=spec.why, how=spec.how, scale=scale,
                            applied=f"{spec.label}: {reason}"),
        )

    band = spec.evaluate(*values)
    points = _points(band.level, spec.max)
    raw = spec.fmt(*values)
    return ScoreItem(
        label=spec.label, raw=raw, level=band.level, points=points, max=spec.max,
        explain=Explain(
            what=spec.what, why=spec.why, how=spec.how, scale=scale,
            applied=f"{spec.label} = {raw} → rơi vào mốc “{band.text}” → {points}/{spec.max} điểm.",
        ),
    )


# Tiêu chí nào lấy giá trị nào từ Metrics (P/E và P/B cần thêm mốc so sánh).
_VALUE_OF: dict[str, Callable[[Metrics], tuple]] = {
    "growth": lambda m: (m.growth,),
    "roe": lambda m: (m.roe,),
    "margin": lambda m: (m.margin,),
    "de": lambda m: (m.de,),
    "ocf": lambda m: (m.ocf,),
    "pe": lambda m: (m.pe, m.pe_sec),
    "pb": lambda m: (m.pb, m.pb_fair),
    "div": lambda m: (m.div,),
    "trend": lambda m: (m.trend,),
    "vol": lambda m: (m.vol,),
    "rsi": lambda m: (m.rsi,),
    "pos": lambda m: (m.pos,),
    "mgmt": lambda m: (m.mgmt,),
    "cat": lambda m: (m.cat,),
}


def _build_categories(m: Metrics) -> list[ScoreCategory]:
    categories: list[ScoreCategory] = []
    for name, maximum, specs in criteria.GROUPS:
        items = [_build_item(spec, *_VALUE_OF[spec.key](m)) for spec in specs]
        categories.append(
            ScoreCategory(name=name, max=maximum, sum=sum(i.points for i in items), items=items)
        )
    return categories


def _verdict(total: int) -> Verdict:
    if total >= 80:
        return Verdict(text="Xuất sắc — ưu tiên giải ngân", level="good")
    if total >= 65:
        return Verdict(text="Tốt — có thể đầu tư, canh điểm mua", level="good")
    if total >= 50:
        return Verdict(text="Trung bình — theo dõi / thăm dò nhỏ", level="warn")
    return Verdict(text="Yếu — nên tránh", level="bad")


def _horizon_fit(value: int) -> tuple[Level, str]:
    if value >= 70:
        return "good", "Phù hợp cao"
    if value >= 50:
        return "warn", "Cân nhắc"
    return "bad", "Chưa phù hợp"


# Mỗi khung thời gian = tổng có trọng số của 4 nhóm (chỉ số là vị trí nhóm trong GROUPS).
# Trọng số phải cộng đủ 1.0 — có test kiểm tra.
_HORIZON_SPECS: dict[str, dict] = {
    "short": {
        "label": "Ngắn hạn (ngày–tuần)",
        "what": "Mức phù hợp nếu bạn định giữ cổ phiếu vài ngày đến vài tuần rồi bán.",
        "why": "Trong vài ngày, giá chạy theo xu hướng và dòng tiền của thị trường chứ chưa kịp "
               "phản ánh kết quả kinh doanh. Vì vậy nhóm kỹ thuật được cho trọng số lớn nhất.",
        "weights": ((2, 0.60), (0, 0.20), (3, 0.20)),
    },
    "mid": {
        "label": "Trung hạn (tháng–1 năm)",
        "what": "Mức phù hợp nếu bạn định nắm giữ từ vài tháng đến khoảng một năm.",
        "why": "Trong một năm, cả kết quả kinh doanh lẫn dòng tiền thị trường đều kịp thể hiện, "
               "nên nền tảng và kỹ thuật được cân bằng, định giá đóng vai trò phụ.",
        "weights": ((0, 0.35), (2, 0.35), (1, 0.15), (3, 0.15)),
    },
    "long": {
        "label": "Dài hạn (nhiều năm)",
        "what": "Mức phù hợp nếu bạn định nắm giữ nhiều năm, xem mình như người đồng sở hữu doanh nghiệp.",
        "why": "Qua nhiều năm, biến động giá ngắn hạn bị san phẳng; thứ còn lại là doanh nghiệp làm "
               "ăn thế nào và bạn đã mua ở mức giá nào. Kỹ thuật không còn được tính.",
        "weights": ((0, 0.50), (1, 0.25), (3, 0.25)),
    },
}


def _horizons(categories: list[ScoreCategory]) -> list[Horizon]:
    """Quy mỗi nhóm về thang 100 rồi nhân trọng số theo từng khung thời gian."""
    result: list[Horizon] = []
    for key, spec in _HORIZON_SPECS.items():
        parts: list[str] = []
        raw_total = 0.0
        for group_index, weight in spec["weights"]:
            group = categories[group_index]
            ratio = group.sum / group.max if group.max else 0.0
            raw_total += ratio * weight
            parts.append(
                f"{group.name} {group.sum}/{group.max} ({ratio * 100:.0f}%) × {weight * 100:.0f}%"
            )
        value = _round_half_up(raw_total * 100)
        level, fit = _horizon_fit(value)
        formula = " + ".join(f"{g_name} {int(w * 100)}%"
                             for (g_i, w), g_name in
                             ((wp, categories[wp[0]].name) for wp in spec["weights"]))
        result.append(Horizon(
            key=key, label=spec["label"], value=value, level=level, fit=fit,
            explain=Explain(
                what=spec["what"],
                why=spec["why"],
                how=f"Công thức: {formula}. Mỗi nhóm được quy về thang 100 trước khi nhân trọng số.",
                scale=["Từ 70 trở lên → Phù hợp cao",
                       "Từ 50 đến 69 → Cân nhắc",
                       "Dưới 50 → Chưa phù hợp"],
                applied=f"{' + '.join(parts)} = {value}/100 → {fit}.",
            ),
        ))
    return result


def _timing(m: Metrics) -> str:
    if m.trend is None or m.rsi is None:
        return "Chưa đủ dữ liệu kỹ thuật để nhận định điểm mua."
    trend = criteria.TREND.evaluate(m.trend).level
    rsi = criteria.RSI.evaluate(m.rsi).level
    if trend == 2 and rsi == 2:
        return "Điểm mua thuận lợi — xu hướng tăng, động lượng khỏe mà chưa quá mua."
    if trend == 2:
        return "Đang tăng nhưng nóng (RSI cao) — chờ nhịp chỉnh, tránh mua đuổi đỉnh."
    if trend == 1:
        return "Giá đi ngang — đợi break khỏi nền tích lũy kèm khối lượng."
    return "Xu hướng giảm — chưa nên mua, tránh 'bắt dao rơi'."


STOP_LOSS_PCT = 8.0  # kỷ luật cắt lỗ mặc định của mô hình (%)

# Với mỗi tiêu chí bị 0đ, giải thích điều gì có thể xảy ra — theo số liệu thật của mã.
_RISK_TEMPLATES: dict[str, Callable[[Metrics], str]] = {
    "Tăng trưởng LN": lambda m: (
        f"Lợi nhuận đang đi lùi ({m.growth}% so cùng kỳ). Nếu quý tới vẫn giảm, "
        "mức giá hiện tại lập tức thành đắt và giá dễ bị chiết khấu mạnh."),
    "ROE": lambda m: (
        f"Đồng vốn sinh lời kém (ROE {m.roe}%). Doanh nghiệp khó tự lớn, dễ phải vay thêm "
        "hoặc phát hành cổ phiếu — pha loãng phần của bạn."),
    "Biên lợi nhuận": lambda m: (
        f"Biên lãi mỏng ({m.margin}%). Chỉ cần chi phí đầu vào nhích lên là lợi nhuận bốc hơi."),
    "Nợ vay D/E": lambda m: (
        f"Nợ vay cao (D/E {m.de}). Lãi suất tăng hoặc doanh thu hụt là chi phí tài chính "
        "ăn hết lợi nhuận; xấu nhất là mất khả năng trả nợ."),
    "Dòng tiền KD": lambda m: (
        "Dòng tiền kinh doanh không dương bền — lãi có thể nằm trên giấy (hàng tồn, "
        "phải thu) chứ tiền thật chưa về."),
    "P/E vs ngành": lambda m: (
        f"Đang đắt hơn mặt bằng ngành (P/E {m.pe} so với {m.pe_sec}). Khi thị trường chỉnh, "
        "nhóm định giá cao thường giảm sâu hơn."),
    "P/B": lambda m: (
        f"Trả giá cao hơn giá trị sổ sách (P/B {m.pb} so với mức hợp lý {m.pb_fair}). "
        "Nếu tăng trưởng hụt, phần chênh này là thứ mất trước."),
    "Cổ tức": lambda m: (
        "Không có cổ tức tiền mặt — toàn bộ kỳ vọng lời đến từ tăng giá. Giá đi ngang "
        "là bạn không nhận được gì trong lúc chờ."),
    "Xu hướng giá": lambda m: (
        "Giá đang dưới đường trung bình, xu hướng giảm. Mua lúc này dễ thành 'bắt dao rơi' "
        "và phải chịu lỗ kéo dài."),
    "Thanh khoản": lambda m: (
        f"Thanh khoản mỏng ({m.vol} triệu cp/phiên). Khi cần bán gấp có thể không có người mua, "
        "phải hạ giá sâu mới thoát được hàng."),
    "Động lượng RSI": lambda m: (
        f"RSI {m.rsi:.0f} ở vùng cực đoan — dễ đảo chiều đột ngột ngay sau khi bạn vào lệnh."),
    "Vị thế ngành": lambda m: (
        "Vị thế cạnh tranh yếu — đối thủ có thể giành thị phần, biên lợi nhuận bị bào mòn dần."),
    "Ban lãnh đạo & cổ đông TC": lambda m: (
        "Ban lãnh đạo bị đánh giá thấp — rủi ro quản trị, thông tin thiếu minh bạch, "
        "quyền lợi cổ đông nhỏ dễ bị bỏ qua."),
    "Catalyst": lambda m: (
        "Chưa có câu chuyện nào đủ rõ để kéo giá lên — tiền của bạn có thể kẹt rất lâu "
        "mà không có động lực tăng."),
}


def _size_bracket(total: int) -> tuple[str, float, str]:
    """(chuỗi hiển thị, % tối đa để tính lỗ, câu hành động)."""
    if total >= 80:
        return ("15–20%", 20.0,
                "Ứng viên mạnh — có thể giải ngân theo khung phù hợp nhất, canh nhịp chỉnh để vào giá tốt.")
    if total >= 65:
        return "8–12%", 12.0, "Đủ tốt — vào lệnh thăm dò, gia tăng khi có thêm xác nhận."
    if total >= 50:
        return ("≤ 5% (thăm dò)", 5.0,
                "Chưa đủ hấp dẫn — đưa vào watchlist, chờ nền tảng hoặc định giá cải thiện.")
    return "0% (loại)", 0.0, "Rủi ro lớn hơn cơ hội — nên tránh."


def _worst_case(
    categories: list[ScoreCategory],
    metrics: Metrics,
    price: Optional[float],
    size_max_pct: float,
    has_missing: bool,
) -> WorstCase:
    """Dựng kịch bản xấu nhất từ chính số liệu: giá cắt lỗ, thiệt hại, và các điểm dễ vỡ."""
    # Xếp các tiêu chí mất điểm nhiều nhất lên đầu (chỉ lấy tiêu chí có dữ liệu).
    losers = sorted(
        (i for c in categories for i in c.items if i.available and i.points < i.max),
        key=lambda i: (i.points / i.max if i.max else 1, -i.max),
    )
    risks = [
        Risk(label=item.label, detail=_RISK_TEMPLATES[item.label](metrics))
        for item in losers
        if item.label in _RISK_TEMPLATES and item.level == 0
    ][:3]

    if has_missing:
        risks.append(Risk(
            label="Thiếu dữ liệu",
            detail=("Một phần chỉ số cơ bản chưa lấy được nên đang bị tính 0đ. "
                    "Điểm tổng vì thế thấp hơn thực tế — hãy tra báo cáo tài chính gốc trước khi kết luận."),
        ))
    if not risks:
        risks.append(Risk(
            label="Rủi ro thị trường",
            detail=("Không tiêu chí nào bị điểm liệt, nhưng cổ phiếu vẫn giảm theo thị trường chung "
                    "hoặc vì tin xấu bất ngờ. Cắt lỗ vẫn là bắt buộc."),
        ))

    stop_price = round(price * (1 - STOP_LOSS_PCT / 100), 2) if price else None
    account_loss_pct = size_max_pct * STOP_LOSS_PCT / 100

    if size_max_pct <= 0:
        narrative = ("Mô hình khuyên KHÔNG mua mã này, nên kịch bản xấu nhất là bạn bỏ qua kỷ luật "
                     "và vẫn xuống tiền — khi đó mọi rủi ro bên dưới đều là của bạn.")
    elif stop_price is not None:
        narrative = (
            f"Bạn mua ở giá {price:g}, giá quay đầu và chạm cắt lỗ {STOP_LOSS_PCT:g}% tại "
            f"{stop_price:g} nghìn đ/cp. Nếu đã dồn mức tối đa {size_max_pct:g}% tài khoản, "
            f"bạn mất khoảng {account_loss_pct:.1f}% tổng tài khoản trong lần này. "
            "Mất mát chỉ dừng ở đó NẾU bạn thật sự cắt — giữ lệnh lỗ và bình quân giá xuống "
            "là cách phổ biến nhất biến khoản lỗ nhỏ thành lỗ lớn."
        )
    else:
        narrative = ("Chưa có giá tham chiếu nên không tính được mức thiệt hại bằng số. "
                     "Vẫn phải đặt sẵn ngưỡng cắt lỗ trước khi vào lệnh.")

    return WorstCase(
        stop_price=stop_price,
        account_loss=(f"≈ {account_loss_pct:.1f}% tài khoản" if size_max_pct > 0 else "—"),
        narrative=narrative,
        risks=risks,
    )


def _decision(
    ticker: str,
    total: int,
    best: Horizon,
    m: Metrics,
    verdict: Verdict,
    categories: list[ScoreCategory],
    price: Optional[float],
    has_missing: bool,
) -> Decision:
    size, size_max_pct, action = _size_bracket(total)
    summary = (f"{ticker} đạt {total}/100 — {verdict.text.lower()}. "
               f"Phù hợp nhất với đầu tư {best.label.split(' (')[0].lower()}. {action}")
    return Decision(
        position_size=size,
        stop_loss=f"−{STOP_LOSS_PCT:g}% từ giá mua",
        timing=_timing(m),
        summary=summary,
        note="Tạm dừng ít nhất 1 ngày trước khi bấm lệnh — cơ hội tốt không biến mất sau 24 giờ.",
        worst_case=_worst_case(categories, m, price, size_max_pct, has_missing),
    )


def compute_score(ticker: str, metrics: Metrics, price: Optional[float] = None) -> Score:
    """Điểm vào duy nhất của mô hình: 14 chỉ số → điểm, verdict, tầm nhìn, quyết định.

    `price` chỉ dùng để quy kịch bản xấu nhất ra con số cụ thể (giá cắt lỗ,
    % thiệt hại) — KHÔNG tham gia vào việc chấm điểm.
    """
    categories = _build_categories(metrics)
    total = sum(c.sum for c in categories)
    verdict = _verdict(total)
    horizons = _horizons(categories)
    best = max(horizons, key=lambda h: h.value)
    has_missing = any(not i.available for c in categories for i in c.items)
    return Score(
        total=total,
        verdict=verdict,
        categories=categories,
        horizons=horizons,
        best_horizon=BestHorizon(key=best.key, label=best.label),
        decision=_decision(ticker, total, best, metrics, verdict, categories, price, has_missing),
    )
