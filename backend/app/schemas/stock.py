"""Schema (DTO) cho API phân tích cổ phiếu.

Quy ước quan trọng: mọi chỉ số trong `Metrics` đều Optional — `None` nghĩa là
KHÔNG crawl được, và bộ chấm điểm sẽ cho 0đ + đánh dấu `available=False`
thay vì bịa số. Không dùng giá trị sentinel (0, 99...) để né hiểu nhầm.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["good", "warn", "bad"]
Trend = Literal["up", "side", "down"]
OcfSign = Literal["+", "±", "-"]
SourceMode = Literal["auto", "vnstock", "cafef"]


class Metrics(BaseModel):
    """14 chỉ số đầu vào của mô hình chấm điểm."""

    # Nhóm nền tảng & tài chính
    growth: Optional[float] = Field(None, description="Tăng trưởng LN sau thuế (% YoY)")
    roe: Optional[float] = Field(None, description="ROE — tỷ suất lợi nhuận trên vốn chủ (%)")
    margin: Optional[float] = Field(None, description="Biên lợi nhuận ròng (%)")
    de: Optional[float] = Field(None, description="D/E — nợ trên vốn chủ sở hữu")
    ocf: Optional[OcfSign] = Field(None, description="Dấu dòng tiền kinh doanh")
    # Nhóm định giá
    pe: Optional[float] = Field(None, description="P/E của mã")
    pe_sec: Optional[float] = Field(None, description="P/E trung bình ngành (ước lượng)")
    pb: Optional[float] = Field(None, description="P/B của mã")
    pb_fair: Optional[float] = Field(None, description="P/B hợp lý (ước lượng)")
    div: Optional[float] = Field(None, description="Tỷ suất cổ tức (%)")
    # Nhóm kỹ thuật
    trend: Optional[Trend] = Field(None, description="Xu hướng giá so MA")
    vol: Optional[float] = Field(None, description="Thanh khoản (triệu cp/phiên)")
    rsi: Optional[float] = Field(None, description="RSI 14 phiên")
    # Nhóm định tính (người dùng tự đánh giá — không crawl được)
    pos: int = Field(1, ge=0, le=2, description="Vị thế ngành")
    mgmt: int = Field(1, ge=0, le=2, description="Ban lãnh đạo & cổ đông tổ chức")
    cat: int = Field(1, ge=0, le=2, description="Catalyst / câu chuyện")


class Explain(BaseModel):
    """Giải thích cho một tiêu chí / khung thời gian.

    Sinh TỪ CHÍNH ngưỡng dùng để chấm điểm nên không thể lệch với kết quả.
    """

    what: str = Field(..., description="Đây là gì, hiểu nôm na thế nào")
    why: str = Field("", description="Vì sao tiêu chí này đáng quan tâm")
    how: str = Field(..., description="Lấy ở đâu, tính bằng công thức nào")
    scale: list[str] = Field(default_factory=list, description="Thang điểm: mốc nào mấy điểm")
    applied: str = Field(..., description="Áp vào mã này: số thật → rơi mốc nào → mấy điểm")


class ScoreItem(BaseModel):
    label: str
    raw: str
    level: int = Field(..., ge=0, le=2)
    points: int
    max: int
    available: bool = True
    explain: Explain


class ScoreCategory(BaseModel):
    name: str
    max: int
    sum: int
    items: list[ScoreItem]


class Verdict(BaseModel):
    text: str
    level: Level


class Horizon(BaseModel):
    key: Literal["short", "mid", "long"]
    label: str
    value: int
    level: Level
    fit: str
    explain: Explain


class BestHorizon(BaseModel):
    key: str
    label: str


class Risk(BaseModel):
    """Một rủi ro CỤ THỂ suy ra từ chính số liệu của mã, không phải lời khuyên chung."""

    label: str
    detail: str


class WorstCase(BaseModel):
    """Kịch bản xấu nhất được tính sẵn — thay cho việc bảo người dùng 'hãy tự hỏi'."""

    stop_price: Optional[float] = Field(None, description="Giá chạm cắt lỗ (nghìn đ)")
    account_loss: str = Field(..., description="Thiệt hại ước tính trên tổng tài khoản")
    narrative: str = Field(..., description="Diễn giải kịch bản bằng câu chữ + con số")
    risks: list[Risk] = Field(default_factory=list, description="Điểm dễ vỡ nhất, xếp theo mức mất điểm")


class Decision(BaseModel):
    position_size: str
    stop_loss: str
    timing: str
    summary: str
    note: str
    worst_case: WorstCase


class Score(BaseModel):
    total: int
    verdict: Verdict
    categories: list[ScoreCategory]
    horizons: list[Horizon]
    best_horizon: BestHorizon
    decision: Decision


class StockAnalysis(BaseModel):
    """Payload trả về cho frontend — đã tính sẵn toàn bộ điểm."""

    ticker: str
    name: str
    sector: str
    price: Optional[float]
    asof: str
    sources: list[str] = []
    missing: list[str] = []
    hint: str = ""
    prices: list[float] = []
    metrics: Metrics
    score: Score


class HealthResponse(BaseModel):
    status: Literal["ok"]


# ── Lịch sử giá theo khung thời gian ─────────────────────────────────────────
RangeKey = Literal["1m", "3m", "1y", "3y"]


class PricePoint(BaseModel):
    """Một phiên giao dịch. Tên trường viết tắt để payload nhẹ khi có ~800 phiên."""

    d: str = Field(..., description="Ngày YYYY-MM-DD")
    o: float = Field(..., description="Giá mở cửa")
    h: float = Field(..., description="Giá cao nhất")
    l: float = Field(..., description="Giá thấp nhất")
    c: float = Field(..., description="Giá đóng cửa")
    v: float = Field(..., description="Khối lượng khớp")


class HistoryStats(BaseModel):
    sessions: int = Field(..., description="Số phiên trong khung")
    low: float = Field(..., description="Giá thấp nhất trong khung")
    high: float = Field(..., description="Giá cao nhất trong khung")
    first: float = Field(..., description="Giá đóng cửa phiên đầu khung")
    last: float = Field(..., description="Giá đóng cửa phiên gần nhất")
    change_pct: float = Field(..., description="% thay đổi từ đầu khung tới nay")
    avg_volume: float = Field(..., description="Khối lượng trung bình (triệu cp/phiên)")


class PriceHistory(BaseModel):
    ticker: str
    range: RangeKey
    label: str = Field(..., description="Nhãn tiếng Việt của khung, VD 'Một năm'")
    source: str = Field(..., description="Nguồn dữ liệu đã dùng")
    points: list[PricePoint]
    stats: HistoryStats


# ── Hồ sơ doanh nghiệp ───────────────────────────────────────────────────────
class Highlight(BaseModel):
    label: str
    value: str
    note: str = ""


class Person(BaseModel):
    name: str
    position: str = ""
    percent: Optional[float] = Field(None, description="Tỷ lệ sở hữu (%)")
    quantity: Optional[float] = Field(None, description="Số cổ phiếu nắm giữ")


class RelatedCompany(BaseModel):
    name: str
    code: str = ""
    percent: Optional[float] = None


class AnalystView(BaseModel):
    """Khuyến nghị của CÔNG TY CHỨNG KHOÁN, không phải quan điểm của công cụ này."""

    source: str
    rating: str
    target_price: Optional[float] = None
    upside_pct: Optional[float] = None
    analyst: str = ""
    as_of: str = ""


class CompanyProfile(BaseModel):
    ticker: str
    name: str
    short_name: str = ""
    sector: str = ""
    exchange: str = ""
    listing_date: str = ""
    highlights: list[Highlight] = []
    analyst: Optional[AnalystView] = None
    officers: list[Person] = []
    shareholders: list[Person] = []
    subsidiaries: list[RelatedCompany] = []
    affiliates: list[RelatedCompany] = []


# ── Báo cáo tài chính & chỉ số ───────────────────────────────────────────────
StatementKey = Literal["income", "balance", "cashflow"]


class StatementRow(BaseModel):
    label: str
    values: list[Optional[float]]


class FinancialStatement(BaseModel):
    ticker: str
    statement: StatementKey
    title: str
    unit: str = Field(..., description="Đơn vị của các con số, VD 'tỷ đồng'")
    periods: list[str]
    rows: list[StatementRow]
    note: str = ""


class RatioItem(BaseModel):
    label: str
    value: Optional[float] = None
    percent: bool = Field(False, description="True nếu giá trị nên hiển thị dạng %")
    unit: str = Field("", description="Đơn vị kèm theo, VD 'tỷ đồng' (rỗng nếu là hệ số)")


class RatioGroup(BaseModel):
    name: str
    items: list[RatioItem]


class RatioTable(BaseModel):
    ticker: str
    period_label: str = Field(..., description="Kỳ của số liệu, VD 'TTM (4 quý gần nhất)'")
    groups: list[RatioGroup]


# ── Tab Giao dịch: ảnh chụp bảng giá phiên hiện tại ──────────────────────────
class QuoteLevel(BaseModel):
    price: Optional[float] = None
    volume: Optional[float] = None


class ForeignFlow(BaseModel):
    """Khối ngoại — ảnh chụp MỘT phiên, không phải chuỗi nhiều ngày.

    Nguồn KHÔNG xóa số khối ngoại khi sang phiên mới (đã đo: 09:02 phiên mới,
    khối lượng khớp = 0 mà số khối ngoại vẫn y nguyên của phiên trước). Vì vậy
    phải nói rõ số này thuộc phiên nào thay vì mặc định coi là phiên hiện tại.
    """

    buy_volume: Optional[float] = None
    sell_volume: Optional[float] = None
    net_volume: Optional[float] = None
    buy_value: Optional[float] = Field(None, description="Tỷ đồng")
    sell_value: Optional[float] = Field(None, description="Tỷ đồng")
    net_value: Optional[float] = Field(None, description="Tỷ đồng")
    room_left: Optional[float] = Field(None, description="Triệu cp còn được mua")
    room_total: Optional[float] = Field(None, description="Triệu cp room tối đa")
    stale: bool = Field(False, description="True = số của phiên TRƯỚC, phiên này chưa khớp lệnh")
    note: str = Field("", description="Số liệu khối ngoại này thuộc phiên nào")


class TradingBoard(BaseModel):
    ticker: str
    asof: str = ""
    reference: Optional[float] = None
    ceiling: Optional[float] = None
    floor: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    match_price: Optional[float] = None
    match_volume: Optional[float] = None
    avg_price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    bids: list[QuoteLevel] = []
    asks: list[QuoteLevel] = []
    foreign: Optional[ForeignFlow] = None
    note: str = ""


# ── Tab Dòng tiền: chỉ báo theo NGÀY (không phải áp lực trong phiên) ─────────
class FlowPoint(BaseModel):
    d: str
    mfi: Optional[float] = None
    obv: Optional[float] = Field(None, description="Triệu cp, tích lũy")
    close: Optional[float] = Field(None, description="Giá đóng cửa (nghìn đ)")
    change_pct: Optional[float] = Field(None, description="% thay đổi so phiên trước")
    volume: Optional[float] = Field(None, description="Khối lượng khớp (triệu cp)")
    value: Optional[float] = Field(None, description="Giá trị khớp ước tính (tỷ đồng)")


class MoneyFlow(BaseModel):
    ticker: str
    range: RangeKey
    label: str
    points: list[FlowPoint] = []
    mfi_latest: Optional[float] = None
    mfi_state: str = Field("", description="Nhận định vùng MFI, VD 'Vùng cân bằng'")
    mfi_level: Level = "warn"
    obv_change_pct: Optional[float] = Field(None, description="% thay đổi OBV trong khung")
    up_sessions: int = 0
    down_sessions: int = 0
    up_volume: Optional[float] = Field(None, description="Triệu cp trong các phiên tăng")
    down_volume: Optional[float] = Field(None, description="Triệu cp trong các phiên giảm")
    foreign: Optional[ForeignFlow] = None
    note: str = ""


# ── Tab Tin tức & Vốn/cổ tức ────────────────────────────────────────────────
class NewsLink(BaseModel):
    """Đường dẫn kèm theo một tin.

    `kind='search'` nghĩa là link TÌM KIẾM theo tiêu đề, KHÔNG phải URL bài gốc —
    nguồn không cung cấp URL bài viết nên không thể dựng link trực tiếp.
    """

    label: str
    url: str
    kind: Literal["search", "official"] = "search"


class NewsItem(BaseModel):
    title: str
    date: str = ""
    links: list[NewsLink] = Field(default_factory=list)


class EventItem(BaseModel):
    name: str = Field(..., description="Loại sự kiện, VD 'Trả cổ tức bằng tiền mặt'")
    title: str = ""
    date: str = ""
    ratio: Optional[float] = Field(None, description="Tỷ lệ thực hiện (%)")
    value_per_share: Optional[float] = Field(None, description="Đồng/cp")
    record_date: str = ""
    exright_date: str = ""
    payout_date: str = ""
    action: str = Field("", description="Mua / Bán với giao dịch nội bộ")


class NewsFeed(BaseModel):
    ticker: str
    news: list[NewsItem] = []
    events: list[EventItem] = []
    disclosure_links: list[NewsLink] = Field(
        default_factory=list,
        description="Trang công bố thông tin chính thức của mã, để tra cứu bản gốc",
    )
    note: str = ""


class CorporateActions(BaseModel):
    ticker: str
    dividends: list[EventItem] = []
    issues: list[EventItem] = []
    insider: list[EventItem] = []
    others: list[EventItem] = []
    note: str = ""


# ── Tab Thống kê: tự tính từ lịch sử giá ────────────────────────────────────
class StatGroup(BaseModel):
    name: str
    items: list[Highlight]


class StockStats(BaseModel):
    ticker: str
    range: RangeKey
    label: str
    groups: list[StatGroup] = []
    note: str = ""


# ── Cảnh báo ────────────────────────────────────────────────────────────────
#  Ba mức độ chắc chắn, KHÔNG được trộn lẫn khi hiển thị:
#    mechanical — tác động số học chắc chắn (điều chỉnh giá ngày GDKHQ)
#    observed   — đã đo được trong dữ liệu (KL đột biến, biến động mạnh)
#    info       — chỉ là thông tin, KHÔNG suy ra hướng giá
EffectKind = Literal["mechanical", "observed", "info"]


class Alert(BaseModel):
    key: str
    level: Level
    title: str
    detail: str = Field(..., description="Diễn giải kèm con số cụ thể")
    evidence: str = Field("", description="Số liệu gốc dẫn tới cảnh báo này")
    effect_kind: EffectKind
    effect_label: str = Field(..., description="Mức độ chắc chắn, hiển thị cho người dùng")
    date: str = ""
    #  Thứ tự ưu tiên hiển thị, số nhỏ lên trước.
    rank: int = 50


class AlertFeed(BaseModel):
    ticker: str
    asof: str = ""
    alerts: list[Alert] = []
    note: str = ""


# ── Sổ mua nhiều đợt & khuyến nghị hành động ────────────────────────────────
ActionKey = Literal["cut", "hold", "add", "none"]


class PositionLot(BaseModel):
    """Một đợt mua do người dùng nhập."""

    price: float = Field(..., gt=0, description="Giá mua (nghìn đ/cp)")
    quantity: float = Field(..., gt=0, description="Số cổ phiếu")
    date: str = Field("", description="Ngày mua YYYY-MM-DD (tùy chọn)")


class PositionRequest(BaseModel):
    lots: list[PositionLot] = Field(..., min_length=1, max_length=50)
    #  Tùy chọn định tính, dùng lại cùng ngưỡng với endpoint phân tích.
    pos: int = Field(1, ge=0, le=2)
    mgmt: int = Field(1, ge=0, le=2)
    cat: int = Field(1, ge=0, le=2)
    pe_sec: Optional[float] = Field(None, gt=0)
    pb_fair: Optional[float] = Field(None, gt=0)
    #  Tổng vốn của tài khoản (nghìn đ) — có thì tính được tỷ trọng thật.
    account_value: Optional[float] = Field(None, gt=0)


class LotResult(BaseModel):
    price: float
    quantity: float
    date: str = ""
    cost: float = Field(..., description="Tiền đã bỏ ra cho đợt này (nghìn đ)")
    pnl: float = Field(..., description="Lãi/lỗ của riêng đợt này (nghìn đ)")
    pnl_pct: float


class PositionAction(BaseModel):
    key: ActionKey
    label: str = Field(..., description="Hành động ngắn gọn, VD 'Cắt lỗ'")
    level: Level
    reason: str = Field(..., description="Vì sao lại khuyên như vậy, dựa trên số liệu")
    detail: str = Field("", description="Hướng dẫn cụ thể nếu thực hiện")


class PositionReview(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    asof: str = ""
    score_total: int = 0
    verdict: str = ""
    verdict_level: Level = "warn"

    total_quantity: float = 0
    total_cost: float = Field(0, description="Tổng tiền đã bỏ ra (nghìn đ)")
    avg_cost: float = Field(0, description="Giá vốn bình quân (nghìn đ/cp)")
    market_value: float = Field(0, description="Giá trị hiện tại (nghìn đ)")
    pnl: float = 0
    pnl_pct: float = 0

    stop_price: Optional[float] = Field(None, description="Giá cắt lỗ tính từ giá vốn bình quân")
    stop_breached: bool = False
    weight_pct: Optional[float] = Field(None, description="Tỷ trọng vị thế trên tài khoản (%)")
    max_weight_pct: Optional[float] = Field(None, description="Trần tỷ trọng theo điểm số (%)")

    lots: list[LotResult] = []
    action: PositionAction
    warnings: list[str] = []
    note: str = ""


# ── Danh sách mã (screener) ──────────────────────────────────────────────────
SortOrder = Literal["asc", "desc"]
ColumnType = Literal["text", "number"]


class ScreenerGroup(BaseModel):
    """Một rổ chọn được, VD VN30."""
    key: str
    label: str
    hint: str = ""


class ScreenerColumn(BaseModel):
    """Mô tả một cột để frontend dựng bảng mà không tự đặt nhãn/đơn vị."""
    key: str
    label: str
    unit: str = ""
    type: ColumnType = "number"
    digits: int = Field(2, ge=0, le=6, description="Số chữ số thập phân khi hiển thị")
    signed: bool = Field(False, description="Cột có dấu: hiện dấu + và tô màu tăng/giảm")
    hint: str = Field("", description="Giải thích cột — dùng cho icon ⓘ")


class ScreenerRow(BaseModel):
    """Một mã trong bảng. `None` = nguồn KHÔNG có số liệu, không phải bằng 0."""
    symbol: str
    name: str
    exchange: str = ""
    price: Optional[float] = None
    ref_price: Optional[float] = Field(None, description="Giá tham chiếu (nghìn đ)")
    change_pct: Optional[float] = None
    volume: Optional[float] = Field(None, description="KL khớp lũy kế (triệu cp)")
    value: Optional[float] = Field(None, description="GT khớp lũy kế (tỷ đồng)")
    foreign_net: Optional[float] = Field(None, description="Khối ngoại mua ròng (tỷ đồng)")
    foreign_stale: bool = Field(
        False,
        description="True = con số khối ngoại KHÔNG thể thuộc phiên này (lớn hơn cả "
                    "tổng giá trị đã khớp), tức là số cũ nguồn chưa xóa",
    )
    market_cap: Optional[float] = Field(None, description="Vốn hóa (tỷ đồng)")


class SessionState(BaseModel):
    """Phiên có đang chạy không — suy ra từ dữ liệu, không so giờ đồng hồ."""
    live: bool
    label: str
    note: str = ""


class ScreenerList(BaseModel):
    group: str
    groups: list[ScreenerGroup] = []
    columns: list[ScreenerColumn] = []
    sort: str
    order: SortOrder = "desc"
    count: int = 0
    session: SessionState
    rows: list[ScreenerRow] = []
    note: str = ""
