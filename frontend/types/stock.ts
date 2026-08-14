/**
 * Kiểu dữ liệu phản chiếu đúng hợp đồng API của backend (FastAPI).
 * Frontend KHÔNG tự tính điểm — mọi con số/nhãn đều do API trả về.
 */

/** Mức đánh giá dạng chuỗi mà API trả về (dùng để tô màu). */
export type Level = 'good' | 'warn' | 'bad'

/** Mức đánh giá dạng số của từng tiêu chí: 0 = kém, 1 = trung bình, 2 = tốt. */
export type ItemLevel = 0 | 1 | 2

/** Lựa chọn định tính do người dùng tự chấm: 0 | 1 | 2. */
export type QualitativeOption = 0 | 1 | 2

/** Nguồn dữ liệu muốn dùng. */
export type SourceOption = 'auto' | 'vci' | 'cafef'

/**
 * Lời giải thích do MÁY CHỦ soạn sẵn cho một tiêu chí / tầm nhìn.
 * Frontend chỉ hiển thị nguyên văn — không tự viết thêm ngưỡng, công thức hay nhận định.
 */
export interface Explain {
  /** Khái niệm là gì. */
  what: string
  /** Vì sao chỉ số này đáng quan tâm (có thể rỗng). */
  why: string
  /** Cách máy chủ tính ra con số. */
  how: string
  /** Thang quy đổi điểm, mỗi phần tử một bậc (có thể rỗng). */
  scale: string[]
  /** Áp vào đúng mã đang xem — bằng chứng cho điểm số. */
  applied: string
}

/** Khung thời gian của biểu đồ giá. */
export type RangeKey = '1m' | '3m' | '1y' | '3y'

/** Một phiên giao dịch (tên trường viết tắt cho payload nhẹ). */
export interface PricePoint {
  /** Ngày YYYY-MM-DD */
  d: string
  /** Mở cửa */
  o: number
  /** Cao nhất */
  h: number
  /** Thấp nhất */
  l: number
  /** Đóng cửa */
  c: number
  /** Khối lượng khớp */
  v: number
}

/** Thống kê nhanh của khung — do máy chủ tính, frontend chỉ hiển thị. */
export interface HistoryStats {
  sessions: number
  low: number
  high: number
  first: number
  last: number
  change_pct: number
  avg_volume: number
}

export interface PriceHistory {
  ticker: string
  range: RangeKey
  label: string
  source: string
  points: PricePoint[]
  stats: HistoryStats
}

/** Tiến độ một bước phân tích do máy chủ phát qua SSE. */
export interface AnalyzeProgress {
  /** Mã bước: technical | company | fundamentals | scoring | done | cache | start */
  step: string
  /** Mô tả tiếng Việt của bước đang chạy. */
  label: string
  /** Phần trăm hoàn thành (0–100). */
  percent: number
}

/** Một tiêu chí chấm điểm trong một nhóm. */
export interface ScoreItem {
  /** Tên tiêu chí, ví dụ "Tăng trưởng LN". */
  label: string
  /** Giá trị thô đã được backend định dạng sẵn, ví dụ "19.1% YoY". */
  raw: string
  /** 0 = kém, 1 = trung bình, 2 = tốt. */
  level: ItemLevel
  /** Điểm đạt được. */
  points: number
  /** Điểm tối đa của tiêu chí. */
  max: number
  /** false = không lấy được dữ liệu (N/A). */
  available: boolean
  /**
   * Giải thích do máy chủ soạn.
   * Khai báo tùy chọn vì phản hồi cũ (đã cache) có thể chưa có trường này —
   * khi thiếu thì KHÔNG hiển thị nút ⓘ, tuyệt đối không bịa chữ thay thế.
   */
  explain?: Explain
}

/** Một nhóm tiêu chí, ví dụ "Nền tảng & tài chính". */
export interface ScoreCategory {
  name: string
  max: number
  sum: number
  items: ScoreItem[]
}

/** Kết luận tổng thể do API sinh ra. */
export interface Verdict {
  text: string
  level: Level
}

/** Điểm theo từng tầm nhìn đầu tư. */
export interface Horizon {
  key: string
  label: string
  value: number
  level: Level
  /** Nhãn mức độ phù hợp, ví dụ "Phù hợp cao". */
  fit: string
  /** Giải thích do máy chủ soạn (tùy chọn — xem ghi chú ở ScoreItem.explain). */
  explain?: Explain
}

export interface BestHorizon {
  key: string
  label: string
}

/** Gợi ý hành động, toàn bộ chữ do API sinh. */
/** Một rủi ro cụ thể do máy chủ suy ra từ số liệu của mã. */
export interface Risk {
  label: string
  detail: string
}

/** Kịch bản xấu nhất — máy chủ tính sẵn, frontend chỉ hiển thị. */
export interface WorstCase {
  stop_price: number | null
  account_loss: string
  narrative: string
  risks: Risk[]
}

export interface Decision {
  position_size: string
  stop_loss: string
  timing: string
  summary: string
  note: string
  worst_case: WorstCase
}

export interface Score {
  total: number
  verdict: Verdict
  categories: ScoreCategory[]
  horizons: Horizon[]
  best_horizon: BestHorizon
  decision: Decision
}

/** Các chỉ số thô (dùng để hiển thị thêm, không dùng để tính toán). */
export interface Metrics {
  growth?: number | null
  roe?: number | null
  margin?: number | null
  de?: number | null
  ocf?: string | null
  pe?: number | null
  pe_sec?: number | null
  pb?: number | null
  pb_fair?: number | null
  div?: number | null
  trend?: string | null
  vol?: number | null
  rsi?: number | null
  pos?: number | null
  mgmt?: number | null
  cat?: number | null
  [key: string]: number | string | null | undefined
}

/** Toàn bộ phản hồi của GET /api/stocks/{ticker}. */
export interface StockAnalysis {
  ticker: string
  name: string
  sector: string
  price: number
  asof: string
  sources: string[]
  /** Danh sách chỉ số không lấy được. */
  missing: string[]
  /** Ghi chú thêm từ backend (có thể rỗng). */
  hint: string
  /** Chuỗi giá đóng cửa gần nhất (có thể rỗng). */
  prices: number[]
  metrics: Metrics
  score: Score
}

/** Tham số truy vấn tùy chọn gửi kèm khi phân tích. */
export interface AnalyzeOptions {
  pos?: QualitativeOption
  mgmt?: QualitativeOption
  cat?: QualitativeOption
  pe_sec?: number | null
  pb_fair?: number | null
  source?: SourceOption
}

/** Lỗi API: FastAPI trả {"detail": "..."} */
export interface ApiErrorBody {
  detail?: string
}

// ── Hồ sơ doanh nghiệp ───────────────────────────────────────────────────────
export interface Highlight {
  label: string
  value: string
  note: string
}

export interface Person {
  name: string
  position: string
  percent: number | null
  quantity: number | null
}

export interface RelatedCompany {
  name: string
  code: string
  percent: number | null
}

/**
 * Khuyến nghị của CÔNG TY CHỨNG KHOÁN (bên thứ ba).
 * Bắt buộc hiển thị kèm `source` — không được trình bày như quan điểm của công cụ.
 */
export interface AnalystView {
  source: string
  rating: string
  target_price: number | null
  upside_pct: number | null
  analyst: string
  as_of: string
}

export interface CompanyProfile {
  ticker: string
  name: string
  short_name: string
  sector: string
  exchange: string
  listing_date: string
  highlights: Highlight[]
  analyst: AnalystView | null
  officers: Person[]
  shareholders: Person[]
  subsidiaries: RelatedCompany[]
  affiliates: RelatedCompany[]
}

// ── Báo cáo tài chính & chỉ số ───────────────────────────────────────────────
export type StatementKey = 'income' | 'balance' | 'cashflow'

export interface StatementRow {
  label: string
  values: (number | null)[]
}

export interface FinancialStatement {
  ticker: string
  statement: StatementKey
  title: string
  /** Đơn vị của mọi con số trong bảng, VD "tỷ đồng". Backend đã quy đổi sẵn. */
  unit: string
  periods: string[]
  rows: StatementRow[]
  note: string
}

export interface RatioItem {
  label: string
  value: number | null
  /** true → hiển thị kèm dấu %. */
  percent: boolean
  /** Đơn vị kèm theo nếu có, VD "tỷ đồng". Rỗng nghĩa là hệ số thuần. */
  unit: string
}

export interface RatioGroup {
  name: string
  items: RatioItem[]
}

export interface RatioTable {
  ticker: string
  period_label: string
  groups: RatioGroup[]
}

// ── Tab Giao dịch ────────────────────────────────────────────────────────────
export interface QuoteLevel {
  price: number | null
  volume: number | null
}

/** Khối ngoại của PHIÊN HIỆN TẠI (ảnh chụp, không phải chuỗi nhiều ngày). */
export interface ForeignFlow {
  buy_volume: number | null
  sell_volume: number | null
  net_volume: number | null
  buy_value: number | null
  sell_value: number | null
  net_value: number | null
  room_left: number | null
  room_total: number | null
  /** true = số của phiên TRƯỚC (phiên này chưa khớp lệnh). */
  stale: boolean
  /** Máy chủ nói rõ số liệu này thuộc phiên nào. */
  note: string
}

export interface TradingBoard {
  ticker: string
  asof: string
  reference: number | null
  ceiling: number | null
  floor: number | null
  open: number | null
  high: number | null
  low: number | null
  match_price: number | null
  match_volume: number | null
  avg_price: number | null
  change: number | null
  change_pct: number | null
  bids: QuoteLevel[]
  asks: QuoteLevel[]
  foreign: ForeignFlow | null
  note: string
}

// ── Tab Dòng tiền ────────────────────────────────────────────────────────────
export interface FlowPoint {
  d: string
  mfi: number | null
  obv: number | null
  close: number | null
  change_pct: number | null
  volume: number | null
  /** Giá trị khớp ƯỚC TÍNH (tỷ đồng) = giá đóng cửa × khối lượng. */
  value: number | null
}

export interface MoneyFlow {
  ticker: string
  range: RangeKey
  label: string
  points: FlowPoint[]
  mfi_latest: number | null
  mfi_state: string
  mfi_level: Level
  obv_change_pct: number | null
  up_sessions: number
  down_sessions: number
  up_volume: number | null
  down_volume: number | null
  foreign: ForeignFlow | null
  note: string
}

// ── Tab Tin tức & Vốn/cổ tức ─────────────────────────────────────────────────
/**
 * Link kèm tin. `kind='search'` = link TÌM KIẾM theo tiêu đề, KHÔNG phải bài gốc —
 * nguồn dữ liệu không có URL bài viết (đã kiểm chứng tận API gốc của Vietcap).
 */
export interface NewsLink {
  label: string
  url: string
  kind: 'search' | 'official'
}

export interface NewsItem {
  title: string
  date: string
  links: NewsLink[]
}

export interface EventItem {
  name: string
  title: string
  date: string
  ratio: number | null
  value_per_share: number | null
  record_date: string
  exright_date: string
  payout_date: string
  action: string
}

export interface NewsFeed {
  ticker: string
  news: NewsItem[]
  events: EventItem[]
  /** Trang công bố thông tin chính thức của mã. */
  disclosure_links: NewsLink[]
  note: string
}

export interface CorporateActions {
  ticker: string
  dividends: EventItem[]
  issues: EventItem[]
  insider: EventItem[]
  others: EventItem[]
  note: string
}

// ── Tab Thống kê ─────────────────────────────────────────────────────────────
export interface StatGroup {
  name: string
  items: Highlight[]
}

export interface StockStats {
  ticker: string
  range: RangeKey
  label: string
  groups: StatGroup[]
  note: string
}

// ── Cảnh báo ─────────────────────────────────────────────────────────────────
/**
 * Mức chắc chắn của một cảnh báo. KHÔNG được trộn lẫn khi hiển thị:
 * mechanical = số học chắc chắn · observed = đã đo được · info = chỉ là thông tin.
 */
export type EffectKind = 'mechanical' | 'observed' | 'info'

export interface Alert {
  key: string
  level: Level
  title: string
  detail: string
  evidence: string
  effect_kind: EffectKind
  effect_label: string
  date: string
  rank: number
}

export interface AlertFeed {
  ticker: string
  asof: string
  alerts: Alert[]
  note: string
}

// ── Sổ mua nhiều đợt ─────────────────────────────────────────────────────────
export type ActionKey = 'cut' | 'hold' | 'add' | 'none'

/** Một đợt mua do người dùng nhập (lưu trong trình duyệt). */
export interface PositionLot {
  price: number
  quantity: number
  date: string
}

export interface LotResult extends PositionLot {
  cost: number
  pnl: number
  pnl_pct: number
}

export interface PositionAction {
  key: ActionKey
  label: string
  level: Level
  reason: string
  detail: string
}

export interface PositionReview {
  ticker: string
  current_price: number | null
  asof: string
  score_total: number
  verdict: string
  verdict_level: Level
  total_quantity: number
  total_cost: number
  avg_cost: number
  market_value: number
  pnl: number
  pnl_pct: number
  stop_price: number | null
  stop_breached: boolean
  weight_pct: number | null
  max_weight_pct: number | null
  lots: LotResult[]
  action: PositionAction
  warnings: string[]
  note: string
}

// ── Danh sách mã (screener) ──────────────────────────────────────────────────
export type SortOrder = 'asc' | 'desc'
export type ColumnType = 'text' | 'number'

/** Một rổ cổ phiếu chọn được. */
export interface ScreenerGroup {
  key: string
  label: string
  hint: string
}

/**
 * Mô tả một cột của bảng. Nhãn, đơn vị, số chữ số thập phân và lời giải thích
 * đều do MÁY CHỦ khai báo — frontend chỉ dựng bảng theo mô tả, không tự đặt chữ.
 */
export interface ScreenerColumn {
  key: string
  label: string
  unit: string
  type: ColumnType
  digits: number
  /** Cột có dấu: hiện dấu + khi dương và tô màu tăng/giảm. */
  signed: boolean
  hint: string
}

/** Một dòng. `null` nghĩa là nguồn KHÔNG có số liệu — không phải bằng 0. */
export interface ScreenerRow {
  symbol: string
  name: string
  exchange: string
  price: number | null
  ref_price: number | null
  change_pct: number | null
  volume: number | null
  value: number | null
  foreign_net: number | null
  /** true = số khối ngoại KHÔNG thuộc phiên này (nguồn chưa xóa số cũ). */
  foreign_stale: boolean
  market_cap: number | null
  [key: string]: string | number | boolean | null
}

/** Phiên có đang chạy không — máy chủ suy ra từ dữ liệu, không so giờ đồng hồ. */
export interface SessionState {
  live: boolean
  label: string
  note: string
}

export interface ScreenerList {
  group: string
  groups: ScreenerGroup[]
  columns: ScreenerColumn[]
  sort: string
  order: SortOrder
  count: number
  session: SessionState
  rows: ScreenerRow[]
  note: string
}
