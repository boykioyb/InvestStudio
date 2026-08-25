/**
 * Tổng quan danh mục.
 *
 * Đọc TẤT CẢ vị thế đã lưu trong máy (localStorage) rồi gửi lên backend gộp —
 * backend lấy giá cả danh mục trong một request và tính lãi/lỗ. Không có logic
 * nghiệp vụ ở đây: chỉ gom dữ liệu và gọi API.
 */
export interface PortfolioRow {
  ticker: string
  name: string
  quantity: number
  avg_cost: number
  total_cost: number
  current_price: number | null
  price_is_ref: boolean
  market_value: number | null
  pnl: number | null
  pnl_pct: number | null
  weight_pct: number | null
}

export interface PortfolioTotals {
  total_cost: number
  market_value: number
  pnl: number
  pnl_pct: number
  positions: number
  priced: number
  winners: number
  losers: number
}

export interface PortfolioReview {
  in_session: boolean
  rows: PortfolioRow[]
  totals: PortfolioTotals
  errors: { ticker: string; message: string }[]
  note: string
}

export function usePortfolio() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')
  const { listAll } = usePositionBook()

  const data = ref<PortfolioReview | null>(null)
  const pending = ref(false)
  const error = ref('')
  const isEmpty = ref(false)

  function toNumber(text: string | undefined): number | null {
    const clean = String(text ?? '').trim().replace(/\s/g, '').replace(',', '.')
    const n = Number(clean)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  async function load(): Promise<void> {
    const stored = listAll()
    if (!stored.length) {
      data.value = null
      isEmpty.value = true
      return
    }
    isEmpty.value = false

    const holdings = stored.map((h) => ({
      ticker: h.ticker,
      lots: h.lots.map((l) => ({ price: l.price, quantity: l.quantity }))
    }))
    //  Vốn tài khoản lưu theo từng mã — lấy giá trị lớn nhất làm tổng vốn (thường
    //  người dùng nhập cùng một con số). Không có thì bỏ qua (tỷ trọng để trống).
    const account = stored
      .map((h) => toNumber(h.account))
      .filter((v): v is number => v !== null)
      .reduce<number | null>((max, v) => (max === null || v > max ? v : max), null)

    pending.value = true
    error.value = ''
    try {
      data.value = await $fetch<PortfolioReview>(`${apiBase}/api/portfolio/review`, {
        method: 'POST',
        body: { holdings, account_value: account },
        timeout: 60_000
      })
    } catch (err) {
      data.value = null
      error.value = (err as { data?: { detail?: string } })?.data?.detail
        || 'Không tải được danh mục. Kiểm tra máy chủ và thử lại.'
    } finally {
      pending.value = false
    }
  }

  return { data, pending, error, isEmpty, load }
}
