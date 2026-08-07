import type { PriceHistory, RangeKey } from '~/types/stock'

/** Các khung thời gian cho biểu đồ giá. Nhãn ngắn để vừa cột hẹp. */
export const PRICE_RANGES: { key: RangeKey; short: string; title: string }[] = [
  { key: '1m', short: '1T', title: 'Một tháng' },
  { key: '3m', short: '1Q', title: 'Một quý (3 tháng)' },
  { key: '1y', short: '1N', title: 'Một năm' },
  { key: '3y', short: '3N', title: 'Ba năm' }
]

/**
 * Tải lịch sử giá theo khung thời gian.
 * Chỉ lấy dữ liệu — mọi con số thống kê đều do máy chủ tính sẵn.
 */
export function usePriceHistory() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const history = ref<PriceHistory | null>(null)
  const range = ref<RangeKey>('3m')
  const pending = ref(false)
  const error = ref<string | null>(null)

  async function load(ticker: string, next: RangeKey = range.value): Promise<void> {
    const code = (ticker || '').trim().toUpperCase()
    if (!code) return

    range.value = next
    pending.value = true
    error.value = null

    try {
      history.value = await $fetch<PriceHistory>(
        `/api/stocks/${encodeURIComponent(code)}/history`,
        { baseURL: apiBase, query: { range: next }, timeout: 45_000 }
      )
    } catch (err) {
      const detail = (err as { data?: { detail?: string } })?.data?.detail
      history.value = null
      error.value = detail || 'Không tải được lịch sử giá cho khung này.'
    } finally {
      pending.value = false
    }
  }

  return { history, range, pending, error, load }
}
