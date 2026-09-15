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
  //  Lãi/lỗ ĐÃ THỰC HIỆN (nghìn đồng) — gắn thêm từ danh mục đồng bộ TCBS.
  realized_pnl?: number | null
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

/** Danh mục đã ĐỒNG BỘ từ công ty chứng khoán (lưu server, giá theo ĐỒNG). */
export interface ImportedHolding {
  ticker: string
  quantity: number
  avg_price: number | null
  market_price: number | null
  realized_pnl?: number | null
  source: string
  account_no: string
  updated_at: string | null
}

export interface SyncedInfo {
  count: number
  source: string
  account: string
  updated_at: string | null
}

export function usePortfolio() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')
  const { listAll } = usePositionBook()
  const { isLoggedIn, ensureLoaded } = useAuth()

  const data = ref<PortfolioReview | null>(null)
  const pending = ref(false)
  const error = ref('')
  const isEmpty = ref(false)
  //  Thông tin danh mục đồng bộ từ TCBS (để trang hiện huy hiệu "đã đồng bộ").
  const synced = ref<SyncedInfo | null>(null)

  function toNumber(text: string | undefined): number | null {
    const clean = String(text ?? '').trim().replace(/\s/g, '').replace(',', '.')
    const n = Number(clean)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  /** Danh mục đồng bộ từ server (chỉ khi đã đăng nhập). Lỗi → coi như rỗng. */
  async function fetchSynced(): Promise<ImportedHolding[]> {
    await ensureLoaded()
    if (!isLoggedIn.value) return []
    try {
      return await $fetch<ImportedHolding[]>(`${apiBase}/api/portfolio/holdings`, {
        credentials: 'include'
      })
    } catch {
      return []
    }
  }

  async function load(): Promise<void> {
    const stored = listAll()
    const server = await fetchSynced()

    //  Gộp: nhập tay (localStorage) + đồng bộ (server). Cùng mã thì ưu tiên bản
    //  ĐỒNG BỘ (số thực từ công ty chứng khoán). Giá server theo ĐỒNG → ÷1000
    //  cho khớp đơn vị "nghìn đồng" mà backend/review dùng.
    const byTicker = new Map<string, { ticker: string; lots: { price: number; quantity: number }[] }>()
    for (const h of stored) {
      byTicker.set(h.ticker.toUpperCase(), {
        ticker: h.ticker,
        lots: h.lots.map((l) => ({ price: l.price, quantity: l.quantity }))
      })
    }
    for (const s of server) {
      const price = (s.avg_price || s.market_price || 0) / 1000
      if (!(price > 0) || !(s.quantity > 0)) continue // không có giá vốn → bỏ qua khi định giá
      byTicker.set(s.ticker.toUpperCase(), {
        ticker: s.ticker,
        lots: [{ price: Number(price.toFixed(2)), quantity: s.quantity }]
      })
    }

    synced.value = server.length
      ? {
          count: server.length,
          source: server[0].source || 'TCBS',
          account: server[0].account_no || '',
          updated_at: server.map((s) => s.updated_at).filter(Boolean).sort().pop() || null
        }
      : null

    const holdings = [...byTicker.values()]
    if (!holdings.length) {
      data.value = null
      isEmpty.value = true
      return
    }
    isEmpty.value = false
    //  Vốn tài khoản lưu theo từng mã — lấy giá trị lớn nhất làm tổng vốn (thường
    //  người dùng nhập cùng một con số). Không có thì bỏ qua (tỷ trọng để trống).
    const account = stored
      .map((h) => toNumber(h.account))
      .filter((v): v is number => v !== null)
      .reduce<number | null>((max, v) => (max === null || v > max ? v : max), null)

    pending.value = true
    error.value = ''
    try {
      const review = await $fetch<PortfolioReview>(`${apiBase}/api/portfolio/review`, {
        method: 'POST',
        body: { holdings, account_value: account },
        timeout: 60_000
      })
      //  Gắn lãi/lỗ ĐÃ THỰC HIỆN (từ TCBS, đơn vị đồng → ÷1000 cho khớp "nghìn đ").
      const realizedByTicker = new Map<string, number>()
      for (const s of server) {
        if (s.realized_pnl != null) realizedByTicker.set(s.ticker.toUpperCase(), s.realized_pnl / 1000)
      }
      if (realizedByTicker.size) {
        for (const row of review.rows) {
          const r = realizedByTicker.get(row.ticker.toUpperCase())
          if (r != null) row.realized_pnl = r
        }
      }
      data.value = review
    } catch (err) {
      data.value = null
      error.value = (err as { data?: { detail?: string } })?.data?.detail
        || 'Không tải được danh mục. Kiểm tra máy chủ và thử lại.'
    } finally {
      pending.value = false
    }
  }

  return { data, pending, error, isEmpty, synced, load }
}
