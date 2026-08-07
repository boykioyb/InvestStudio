import type { PositionLot, PositionReview } from '~/types/stock'

const STORAGE_KEY = 'investstudio.positions.v1'

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
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
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

  return { lots, accountValue, review, pending, error, load, addLot, removeLot, clear, saveAccount, evaluate }
}
