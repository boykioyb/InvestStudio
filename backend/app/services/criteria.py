"""Bảng khai báo 14 tiêu chí: ngưỡng chấm điểm + lời giải thích, ở CÙNG một chỗ.

Vì sao gộp chung: điểm số và câu giải thích được sinh từ CÙNG một danh sách
`bands`, nên không thể xảy ra chuyện thang điểm hiển thị một đằng còn máy chấm
một nẻo. Muốn đổi ngưỡng → sửa `bands`, phần giải thích tự đúng theo.

Thứ tự band có ý nghĩa: band đầu tiên khớp sẽ được chọn.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True, slots=True)
class Band:
    """Một mốc của thang điểm: mô tả + mức đạt (0/1/2) + điều kiện khớp."""

    text: str
    level: int
    match: Callable[..., bool]


@dataclass(frozen=True, slots=True)
class CriterionSpec:
    key: str
    label: str
    max: int
    what: str
    why: str
    how: str
    bands: tuple[Band, ...]
    fmt: Callable[..., str]
    #  Tiêu chí định tính do người dùng tự chấm — không có gì để crawl.
    manual: bool = False

    def evaluate(self, *values) -> Band:
        for band in self.bands:
            if band.match(*values):
                return band
        return self.bands[-1]


_ALWAYS = lambda *_: True  # noqa: E731 — band cuối luôn khớp (mặc định)

# ── Nhóm 1: Nền tảng & tài chính (45đ) ───────────────────────────────────────
GROWTH = CriterionSpec(
    key="growth", label="Tăng trưởng LN", max=12,
    what="Lợi nhuận sau thuế năm gần nhất so với năm liền trước, tính bằng phần trăm.",
    why="Về dài hạn giá cổ phiếu đi theo lợi nhuận. Lợi nhuận tăng đều thì giá có nền để lên; "
        "lợi nhuận đi lùi thì mọi mức định giá 'rẻ' đều có thể là bẫy.",
    how="(LNST năm nay − LNST năm trước) ÷ |LNST năm trước| × 100. "
        "Số lấy từ Báo cáo kết quả kinh doanh (nguồn vnstock/VCI).",
    bands=(
        Band("Từ 0% trở xuống — lợi nhuận đi lùi", 0, lambda v: v <= 0),
        Band("Trên 0% đến dưới 20% — có tăng nhưng chậm", 1, lambda v: v < 20),
        Band("Từ 20% trở lên — tăng mạnh", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v}% YoY",
)

ROE = CriterionSpec(
    key="roe", label="ROE", max=10,
    what="ROE (Return on Equity — tỷ suất lợi nhuận trên vốn chủ sở hữu): 100 đồng vốn của "
         "cổ đông tạo ra bao nhiêu đồng lãi mỗi năm.",
    why="ROE cao và bền cho thấy doanh nghiệp dùng tiền hiệu quả, tự nuôi được tăng trưởng mà "
        "không phải liên tục vay thêm hay phát hành cổ phiếu làm loãng phần của bạn.",
    how="Lợi nhuận sau thuế ÷ vốn chủ sở hữu, lấy chỉ số TTM (bốn quý gần nhất) từ vnstock/VCI.",
    bands=(
        Band("Dưới 10% — thấp, kém hấp dẫn so với kênh an toàn", 0, lambda v: v < 10),
        Band("Từ 10% đến 15% — chấp nhận được", 1, lambda v: v <= 15),
        Band("Trên 15% — hiệu quả cao", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v}%",
)

MARGIN = CriterionSpec(
    key="margin", label="Biên lợi nhuận", max=8,
    what="Biên lợi nhuận ròng: trong 100 đồng doanh thu, doanh nghiệp giữ lại được bao nhiêu đồng lãi.",
    why="Biên dày là tấm đệm chịu sốc: giá nguyên liệu tăng hay phải giảm giá bán thì vẫn còn lãi. "
        "Biên mỏng thì chỉ một biến động nhỏ cũng đủ đẩy doanh nghiệp vào lỗ.",
    how="Lợi nhuận sau thuế ÷ doanh thu thuần (TTM), nguồn vnstock/VCI.",
    bands=(
        Band("Dưới 8% — mỏng, dễ tổn thương", 0, lambda v: v < 8),
        Band("Từ 8% đến 15% — trung bình", 1, lambda v: v <= 15),
        Band("Trên 15% — dày, có đệm an toàn", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v}%",
)

DEBT = CriterionSpec(
    key="de", label="Nợ vay D/E", max=8,
    what="D/E (Debt to Equity — nợ trên vốn chủ sở hữu): doanh nghiệp vay bao nhiêu đồng trên "
         "mỗi đồng vốn tự có.",
    why="Nợ khuếch đại cả lãi lẫn lỗ. Khi lãi suất tăng hoặc doanh thu hụt, nhóm vay nhiều là "
        "nhóm gãy trước — đây là rủi ro làm mất vốn vĩnh viễn chứ không chỉ là giá giảm tạm thời.",
    how="Tổng nợ vay ÷ vốn chủ sở hữu (TTM), nguồn vnstock/VCI. Lưu ý: ngân hàng có cấu trúc vốn "
        "đặc thù nên chỉ số này ít ý nghĩa với nhóm ngân hàng.",
    bands=(
        Band("Trên 1.5 — vay quá nhiều so với vốn tự có", 0, lambda v: v > 1.5),
        Band("Từ 0.5 đến 1.5 — vay ở mức vừa phải", 1, lambda v: v >= 0.5),
        Band("Dưới 0.5 — ít phụ thuộc nợ vay", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v:.2f}",
)

CASHFLOW = CriterionSpec(
    key="ocf", label="Dòng tiền KD", max=7,
    what="Dấu của dòng tiền từ hoạt động kinh doanh — tiền mặt thực sự thu về từ việc bán hàng "
         "sau khi trừ tiền chi ra.",
    why="Lợi nhuận trên sổ sách có thể đẹp nhờ ghi nhận doanh thu chưa thu được tiền. Dòng tiền "
        "khó 'làm đẹp' hơn nhiều, nên 'lãi mà không có tiền về' là dấu hiệu cảnh báo kinh điển.",
    how="Đọc dòng 'Lưu chuyển tiền thuần từ hoạt động kinh doanh' các năm gần nhất (vnstock/VCI): "
        "dương ở mọi năm → bền; năm gần nhất dương nhưng có năm âm → thất thường; "
        "năm gần nhất âm → âm.",
    bands=(
        Band("Dương ở tất cả các năm gần đây", 2, lambda v: v == "+"),
        Band("Có năm âm — thất thường", 1, lambda v: v == "±"),
        Band("Năm gần nhất âm — tiền không về", 0, _ALWAYS),
    ),
    fmt=lambda v: {"+": "Dương bền", "±": "Thất thường"}.get(v, "Âm"),
)

# ── Nhóm 2: Định giá (20đ) ───────────────────────────────────────────────────
PE = CriterionSpec(
    key="pe", label="P/E vs ngành", max=10,
    what="P/E (Price to Earnings — giá trên lợi nhuận mỗi cổ phiếu): bạn bỏ ra bao nhiêu đồng để "
         "mua 1 đồng lợi nhuận mỗi năm. P/E 12 nghĩa là cần khoảng 12 năm lợi nhuận để hoàn vốn "
         "nếu lợi nhuận đứng yên.",
    why="Doanh nghiệp tốt nhưng mua quá đắt vẫn là khoản đầu tư tệ. So với mặt bằng ngành để biết "
        "bạn đang trả cao hay thấp hơn những công ty cùng loại.",
    how="P/E của mã (TTM, vnstock/VCI) chia cho P/E trung bình ngành. "
        "P/E ngành là số ƯỚC LƯỢNG theo bảng benchmark — bạn có thể tự nhập lại ở mục Tùy chọn.",
    bands=(
        Band("Đắt hơn ngành trên 10%", 0, lambda v, b: bool(b) and v / b > 1.1),
        Band("Rẻ hơn ngành trên 10%", 2, lambda v, b: bool(b) and v / b < 0.9),
        Band("Chênh dưới 10% — ngang mặt bằng ngành", 1, _ALWAYS),
    ),
    fmt=lambda v, b: f"{v} / ngành {b}",
)

PB = CriterionSpec(
    key="pb", label="P/B", max=5,
    what="P/B (Price to Book — giá trên giá trị sổ sách): bạn trả bao nhiêu đồng cho 1 đồng tài "
         "sản ròng ghi trên sổ sách.",
    why="P/B cho thấy phần 'trả thêm' ngoài tài sản hữu hình. Trả thêm càng nhiều thì kỳ vọng "
        "tăng trưởng càng phải thành hiện thực; nếu hụt, phần chênh này là thứ mất giá trước tiên.",
    how="P/B của mã (TTM, vnstock/VCI) chia cho mức P/B được coi là hợp lý với ngành. "
        "Mức hợp lý là ƯỚC LƯỢNG — có thể tự nhập lại ở mục Tùy chọn.",
    bands=(
        Band("Cao hơn mức hợp lý trên 10%", 0, lambda v, b: bool(b) and v / b > 1.1),
        Band("Thấp hơn mức hợp lý trên 10%", 2, lambda v, b: bool(b) and v / b < 0.9),
        Band("Chênh dưới 10% — quanh mức hợp lý", 1, _ALWAYS),
    ),
    fmt=lambda v, b: f"{v} / hợp lý {b}",
)

DIVIDEND = CriterionSpec(
    key="div", label="Cổ tức", max=5,
    what="Tỷ suất cổ tức: số tiền mặt doanh nghiệp trả cho cổ đông mỗi năm, tính theo phần trăm thị giá.",
    why="Cổ tức là khoản lời có thật, không phụ thuộc giá lên hay xuống. Với người mới, đây là "
        "phần thưởng nhận được trong lúc chờ giá phản ánh giá trị.",
    how="Cổ tức tiền mặt 12 tháng ÷ thị giá hiện tại (TTM, vnstock/VCI).",
    bands=(
        Band("Không trả cổ tức tiền mặt", 0, lambda v: v <= 0),
        Band("Dưới 3% — thấp hơn lãi gửi tiết kiệm", 1, lambda v: v < 3),
        Band("Từ 3% trở lên — đáng kể", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v}%",
)

# ── Nhóm 3: Kỹ thuật & xu hướng (20đ) ────────────────────────────────────────
TREND = CriterionSpec(
    key="trend", label="Xu hướng giá", max=8,
    what="Vị trí giá hiện tại so với đường trung bình động MA20 và MA50 — giá trung bình của 20 "
         "và 50 phiên gần nhất.",
    why="Mua ngược xu hướng giảm là cách thua lỗ phổ biến nhất của người mới. Xu hướng không nói "
        "doanh nghiệp tốt hay xấu, nó nói dòng tiền đang chảy vào hay rút ra khỏi cổ phiếu.",
    how="Tính MA20 và MA50 từ giá đóng cửa ĐÃ ĐIỀU CHỈNH (nguồn CafeF). "
        "Giá > MA50 và MA20 ≥ MA50 → tăng; giá < MA50 và MA20 ≤ MA50 → giảm; còn lại → đi ngang.",
    bands=(
        Band("Trên MA50, MA20 hướng lên — xu hướng tăng", 2, lambda v: v == "up"),
        Band("Đi ngang — chưa rõ hướng", 1, lambda v: v == "side"),
        Band("Dưới MA50 — xu hướng giảm", 0, _ALWAYS),
    ),
    fmt=lambda v: {"up": "Trên MA, tăng", "side": "Đi ngang"}.get(v, "Dưới MA, giảm"),
)

LIQUIDITY = CriterionSpec(
    key="vol", label="Thanh khoản", max=6,
    what="Khối lượng khớp lệnh trung bình 20 phiên gần nhất, tính bằng triệu cổ phiếu mỗi phiên.",
    why="Thanh khoản là khả năng bán được khi bạn cần. Mã ít giao dịch có thể phải hạ giá rất sâu "
        "mới có người mua — rủi ro này không hiện ra trong bất kỳ chỉ số tài chính nào.",
    how="Trung bình khối lượng khớp lệnh 20 phiên gần nhất (nguồn CafeF) chia cho 1.000.000.",
    bands=(
        Band("Dưới 0.5 triệu cp/phiên — rất mỏng, khó thoát hàng", 0, lambda v: v < 0.5),
        Band("Từ 0.5 đến dưới 2 triệu — trung bình", 1, lambda v: v < 2),
        Band("Từ 2 triệu trở lên — dồi dào", 2, _ALWAYS),
    ),
    fmt=lambda v: f"{v} tr cp/phiên",
)

RSI = CriterionSpec(
    key="rsi", label="Động lượng RSI", max=6,
    what="RSI 14 (Relative Strength Index — chỉ báo sức mạnh tương đối): đo độ 'nóng' của giá "
         "trong 14 phiên gần nhất, thang 0–100.",
    why="RSI quá cao thường rơi đúng lúc đám đông hưng phấn nhất — mua vào dễ đu đỉnh. Quá thấp là "
        "lúc bán tháo, bắt đáy sớm có thể còn lỗ tiếp. Vùng giữa là trạng thái cân bằng.",
    how="Công thức Wilder trên giá đóng cửa điều chỉnh 14 phiên (nguồn CafeF): so trung bình các "
        "phiên tăng với trung bình các phiên giảm.",
    bands=(
        Band("Trên 80 (quá mua) hoặc dưới 30 (quá bán) — vùng cực đoan", 0,
             lambda v: v > 80 or v < 30),
        Band("Từ trên 70 đến 80 — bắt đầu nóng", 1, lambda v: v > 70),
        Band("Từ 30 đến 70 — vùng cân bằng", 2, _ALWAYS),
    ),
    fmt=lambda v: f"RSI {v:.0f}" + (" (quá mua)" if v > 80 else " (quá bán)" if v < 30 else ""),
)

# ── Nhóm 4: Định tính & vĩ mô (15đ) — người dùng tự chấm ─────────────────────
_MANUAL_HOW = ("Máy KHÔNG tự đánh giá được mục này — bạn tự chấm ở phần Tùy chọn, "
               "mặc định là mức trung bình.")

POSITION = CriterionSpec(
    key="pos", label="Vị thế ngành", max=6, manual=True,
    what="Doanh nghiệp có lợi thế nào khiến đối thủ khó giành chỗ: thương hiệu, quy mô, chi phí "
         "thấp, mạng lưới phân phối, giấy phép…",
    why="Lợi thế bền vững là thứ giữ cho biên lợi nhuận không bị bào mòn khi đối thủ nhảy vào. "
        "Không có nó, lợi nhuận cao hôm nay sẽ bị cạnh tranh kéo xuống.",
    how=_MANUAL_HOW,
    bands=(
        Band("Yếu — dễ bị đối thủ thay thế", 0, lambda v: v == 0),
        Band("Trung bình — không có gì đặc biệt", 1, lambda v: v == 1),
        Band("Mạnh — có lợi thế bền vững", 2, _ALWAYS),
    ),
    fmt=lambda v: ["Yếu", "Trung bình", "Dẫn đầu"][v],
)

MANAGEMENT = CriterionSpec(
    key="mgmt", label="Ban lãnh đạo & cổ đông TC", max=5, manual=True,
    what="Đội ngũ điều hành có minh bạch, giữ lời hứa với cổ đông không; có quỹ/tổ chức lớn nắm giữ không.",
    why="Cổ đông nhỏ không kiểm soát được dòng tiền doanh nghiệp. Ban lãnh đạo thiếu minh bạch có "
        "thể pha loãng, chuyển giá hoặc dùng tiền sai mục đích — số liệu tài chính đẹp cũng vô nghĩa.",
    how=_MANUAL_HOW,
    bands=(
        Band("Có nhiều điều đáng nghi ngại", 0, lambda v: v == 0),
        Band("Bình thường — chưa thấy vấn đề", 1, lambda v: v == 1),
        Band("Minh bạch, giữ lời hứa với cổ đông", 2, _ALWAYS),
    ),
    fmt=lambda v: ["Kém", "Ổn", "Uy tín"][v],
)

CATALYST = CriterionSpec(
    key="cat", label="Catalyst", max=4, manual=True,
    what="Catalyst (chất xúc tác): sự kiện sắp diễn ra có thể kéo giá lên — nhà máy mới chạy, "
         "hợp đồng lớn, thoái vốn, niêm yết công ty con, chính sách thuận lợi…",
    why="Cổ phiếu tốt nhưng không có chất xúc tác có thể đi ngang rất lâu. Tiền của bạn bị kẹt "
        "trong khi chi phí cơ hội vẫn chạy.",
    how=_MANUAL_HOW,
    bands=(
        Band("Chưa thấy câu chuyện gì mới", 0, lambda v: v == 0),
        Band("Có nhưng còn mơ hồ", 1, lambda v: v == 1),
        Band("Rõ ràng và sắp diễn ra", 2, _ALWAYS),
    ),
    fmt=lambda v: ["Không rõ", "Tiềm năng", "Rõ ràng"][v],
)

# Nhóm → (tên, điểm tối đa, các tiêu chí). Tổng đúng 100đ.
GROUPS: tuple[tuple[str, int, tuple[CriterionSpec, ...]], ...] = (
    ("Nền tảng & tài chính", 45, (GROWTH, ROE, MARGIN, DEBT, CASHFLOW)),
    ("Định giá", 20, (PE, PB, DIVIDEND)),
    ("Kỹ thuật & xu hướng", 20, (TREND, LIQUIDITY, RSI)),
    ("Định tính & vĩ mô", 15, (POSITION, MANAGEMENT, CATALYST)),
)
