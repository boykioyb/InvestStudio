import type { ScreenerList, ScreenerRow } from '~/types/stock'

/**
 * Tổng quan thị trường cho trang Home.
 *
 * CHỈ MỘT lần gọi `/api/screener` (tôn trọng hạn mức ~20 req/phút của nguồn):
 * máy chủ trả cả rổ đã sắp theo `change_pct`, từ đó suy ra top tăng/giảm và độ
 * rộng thị trường ngay tại client (chỉ là đếm/lấy đầu-cuối, không có logic
 * nghiệp vụ). Ngoài phiên `change_pct` = null → tự chuyển sang xếp theo giá trị
 * khớp lệnh và ẩn phần độ rộng.
 */
export interface Mover { symbol: string; name: string; price: number | null; change: number | null }

export function useMarketOverview() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const group = ref('VN30')
  const pending = ref(false)
  const error = ref('')
  const inSession = ref(false)
  const sessionLabel = ref('')
  const gainers = ref<Mover[]>([])
  const losers = ref<Mover[]>([])
  const mostActive = ref<Mover[]>([])
  const activeLabel = ref('giá trị khớp lệnh')
  const breadth = ref({ up: 0, down: 0, flat: 0 })

  const toMover = (r: ScreenerRow): Mover => ({
    symbol: String(r.symbol),
    name: String(r.name ?? ''),
    price: (r.price as number) ?? null,
    change: (r.change_pct as number) ?? null
  })

  async function load(): Promise<void> {
    pending.value = true
    error.value = ''
    try {
      const data = await $fetch<ScreenerList>(`${apiBase}/api/screener`, {
        query: { group: group.value, sort: 'change_pct', order: 'desc' }
      })
      const rows = data.rows || []
      sessionLabel.value = data.session?.label || ''
      inSession.value = rows.some((r) => typeof r.change_pct === 'number')

      if (inSession.value) {
        const withChg = rows.filter((r) => typeof r.change_pct === 'number')
        gainers.value = withChg.filter((r) => (r.change_pct as number) > 0).slice(0, 5).map(toMover)
        losers.value = withChg.filter((r) => (r.change_pct as number) < 0).slice(-5).reverse().map(toMover)
        breadth.value = {
          up: withChg.filter((r) => (r.change_pct as number) > 0).length,
          down: withChg.filter((r) => (r.change_pct as number) < 0).length,
          flat: withChg.filter((r) => (r.change_pct as number) === 0).length
        }
      } else {
        gainers.value = []
        losers.value = []
        breadth.value = { up: 0, down: 0, flat: 0 }
      }

      // Sôi động nhất theo giá trị khớp lệnh; ngoài phiên value = null → xếp
      // theo vốn hóa (luôn có) để trang không trống.
      const hasValue = rows.some((r) => typeof r.value === 'number')
      const field = hasValue ? 'value' : 'market_cap'
      activeLabel.value = hasValue ? 'giá trị khớp lệnh' : 'vốn hóa lớn nhất'
      mostActive.value = [...rows]
        .filter((r) => typeof r[field] === 'number')
        .sort((a, b) => (b[field] as number) - (a[field] as number))
        .slice(0, 6)
        .map(toMover)
    } catch (err) {
      error.value = (err as { data?: { detail?: string } })?.data?.detail
        || 'Không tải được dữ liệu thị trường.'
    } finally {
      pending.value = false
    }
  }

  function selectGroup(key: string): void {
    if (group.value === key) return
    group.value = key
    void load()
  }

  return { group, pending, error, inSession, sessionLabel, gainers, losers, mostActive, activeLabel, breadth, load, selectGroup }
}
