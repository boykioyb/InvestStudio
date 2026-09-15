import type { PositionLot, PositionReview } from '~/types/stock'

const STORAGE_KEY = 'phantichma.positions.v1'
//  Khóa cũ từ thời tên sản phẩm là InvestStudio. Người dùng đã lưu sổ mua trong
//  trình duyệt của họ — đổi tên khóa mà không đọc lại khóa cũ là XÓA SẠCH dữ
//  liệu đó một cách âm thầm. Đọc lại một lần rồi chuyển sang khóa mới.
const LEGACY_KEY = 'investstudio.positions.v1'

/**
 * Sổ mua nhiều đợt.
 *
 * Lưu trong localStorage của chính trình duyệt bạn dùng — không gửi lên máy chủ
 * để lưu trữ, không có tài khoản, không đồng bộ giữa các máy. Xóa dữ liệu duyệt
 * web là mất. Đây là lựa chọn có chủ đích: số tiền bạn đầu tư là chuyện riêng tư.
 *
 * Máy chủ chỉ nhận các đợt mua để TÍNH TOÁN rồi trả kết quả, không lưu lại.
 */
export function usePositionBook() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const lots = ref<PositionLot[]>([])
  const accountValue = ref<string>('')
  const review = ref<PositionReview | null>(null)
  const pending = ref(false)
  const error = ref<string | null>(null)

  function readAll(): Record<string, { lots: PositionLot[]; account?: string }> {
    if (!import.meta.client) return {}
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) return JSON.parse(raw)

      //  Chưa có khóa mới → thử khóa cũ và dọn nhà một lần.
      const cu = localStorage.getItem(LEGACY_KEY)
      if (!cu) return {}
      localStorage.setItem(STORAGE_KEY, cu)
      localStorage.removeItem(LEGACY_KEY)
      return JSON.parse(cu)
    } catch {
      return {}
    }
  }

  function persist(ticker: string): void {
    if (!import.meta.client) return
    const all = readAll()
    const code = ticker.toUpperCase()
    if (lots.value.length) {
      all[code] = { lots: lots.value, account: accountValue.value }
    } else {
      delete all[code]
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
    } catch {
      /* hết dung lượng hoặc bị chặn — bỏ qua, dữ liệu vẫn dùng được trong phiên */
    }
  }

  /** Toàn bộ mã đang có vị thế trong máy này — cho trang tổng quan danh mục. */
  function listAll(): { ticker: string; lots: PositionLot[]; account?: string }[] {
    const all = readAll()
    return Object.entries(all)
      .filter(([, v]) => v?.lots?.length)
      .map(([ticker, v]) => ({ ticker, lots: v.lots, account: v.account }))
  }

  function load(ticker: string): void {
    const saved = readAll()[ticker.toUpperCase()]
    lots.value = saved?.lots ? [...saved.lots] : []
    accountValue.value = saved?.account || ''
    review.value = null
    error.value = null
  }

  function addLot(ticker: string, lot: PositionLot): void {
    lots.value = [...lots.value, lot]
    persist(ticker)
  }

  function removeLot(ticker: string, index: number): void {
    lots.value = lots.value.filter((_, i) => i !== index)
    persist(ticker)
    if (!lots.value.length) review.value = null
  }

  function clear(ticker: string): void {
    lots.value = []
    review.value = null
    persist(ticker)
  }

  function saveAccount(ticker: string): void {
    persist(ticker)
  }

  function toNumber(text: string): number | null {
    const clean = text.trim().replace(/\s/g, '').replace(',', '.')
    if (!clean) return null
    const n = Number(clean)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  async function evaluate(ticker: string): Promise<void> {
    if (!lots.value.length) {
      error.value = 'Hãy thêm ít nhất một đợt mua.'
      return
    }
    pending.value = true
    error.value = null
    try {
      review.value = await $fetch<PositionReview>(
        `/api/stocks/${encodeURIComponent(ticker.toUpperCase())}/position`,
        {
          baseURL: apiBase,
          method: 'POST',
          body: { lots: lots.value, account_value: toNumber(accountValue.value) },
          timeout: 90_000
        }
      )
    } catch (err) {
      const detail = (err as { data?: { detail?: string } })?.data?.detail
      review.value = null
      //  Ghi log nguyên văn: thông điệp rút gọn bên dưới che mất nguyên nhân thật.
      console.error('[usePositionBook] đánh giá vị thế thất bại:', err)
      error.value = detail || 'Không đánh giá được vị thế. Kiểm tra máy chủ và thử lại.'
    } finally {
      pending.value = false
    }
  }

  /**
   * Nhập đợt khớp đã đồng bộ (server) vào Vị thế của tôi, TRỪ FIFO theo lệnh bán.
   *
   * Mỗi mã: xếp các đợt theo NGÀY (cùng ngày ưu tiên MUA trước BÁN vì txdate chỉ có
   * ngày, mất thứ tự trong phiên); duyệt lần lượt, đợt bán trừ dần các đợt mua cũ
   * nhất còn lại → phần còn lại = vị thế đang giữ. Giá server theo ĐỒNG → ÷1000.
   * Ghi ĐÈ các mã có trong dữ liệu đồng bộ, giữ nguyên mã khác (nhập tay).
   */
  async function importFromServer(): Promise<{ tickers: number; lots: number }> {
    interface ServerLot { ticker: string; side: string; quantity: number; price: number; txdate: string }
    const rows = await $fetch<ServerLot[]>(`${apiBase}/api/portfolio/lots`, { credentials: 'include' })

    //  Gom theo mã.
    const perTicker = new Map<string, ServerLot[]>()
    for (const r of rows) {
      if (!(r.quantity > 0)) continue
      const code = r.ticker.toUpperCase()
      const arr = perTicker.get(code) || []
      arr.push(r)
      perTicker.set(code, arr)
    }

    const byTicker = new Map<string, PositionLot[]>()
    let totalLots = 0
    for (const [code, events] of perTicker) {
      //  Ngày tăng dần; cùng ngày: mua (0) trước bán (1).
      events.sort((a, b) =>
        (a.txdate || '').localeCompare(b.txdate || '') ||
        (a.side === 'buy' ? 0 : 1) - (b.side === 'buy' ? 0 : 1))

      const queue: PositionLot[] = [] // hàng đợi đợt mua còn lại (FIFO)
      for (const e of events) {
        if (e.side === 'buy' && e.price > 0) {
          queue.push({ price: Number((e.price / 1000).toFixed(2)), quantity: e.quantity, date: e.txdate || '' })
        } else if (e.side === 'sell') {
          let remain = e.quantity
          while (remain > 0 && queue.length) {
            const lot = queue[0]
            if (lot.quantity > remain) { lot.quantity = Number((lot.quantity - remain).toFixed(4)); remain = 0 }
            else { remain -= lot.quantity; queue.shift() } // bán hết đợt mua cũ nhất
          }
          //  remain > 0 (bán nhiều hơn mua trong dữ liệu) → bỏ qua phần dôi.
        }
      }
      const kept = queue.filter((l) => l.quantity > 0)
      if (kept.length) { byTicker.set(code, kept); totalLots += kept.length }
    }

    if (import.meta.client && byTicker.size) {
      const all = readAll()
      for (const [code, ls] of byTicker) all[code] = { lots: ls, account: all[code]?.account }
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(all)) } catch { /* hết dung lượng — bỏ qua */ }
    }
    return { tickers: byTicker.size, lots: totalLots }
  }

  return { lots, accountValue, review, pending, error, listAll, load, addLot, removeLot, clear, saveAccount, evaluate, importFromServer }
}
