import type { MarketEvent, MarketHighlights, MarketLeader, MarketNewsItem } from '~/types/stock'

/**
 * Điểm nhấn thị trường cho trang chủ: lịch sự kiện sắp tới, tin công bố mới và
 * bảng điểm cao nhất trong rổ.
 *
 * Một lần gọi `/api/market/highlights` trả cả ba khối. Composable chỉ giữ dữ
 * liệu thô của máy chủ — không suy luận, không chấm điểm ở client. Ba mảng đều
 * có thể rỗng (nguồn chưa có dữ liệu) → phía trình bày tự hiện trạng thái trống.
 */
export function useMarketHighlights() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const pending = ref(false)
  /** true = gọi lỗi → khối này nên thu gọn/ẩn thay vì làm sập trang. */
  const failed = ref(false)
  const events = ref<MarketEvent[]>([])
  const news = ref<MarketNewsItem[]>([])
  const leaders = ref<MarketLeader[]>([])

  async function load(group: string, limit = 5): Promise<void> {
    pending.value = true
    failed.value = false
    try {
      const data = await $fetch<MarketHighlights>(`${apiBase}/api/market/highlights`, {
        query: { group, limit }
      })
      events.value = data.events || []
      news.value = data.news || []
      leaders.value = data.leaders || []
    } catch {
      failed.value = true
      events.value = []
      news.value = []
      leaders.value = []
    } finally {
      pending.value = false
    }
  }

  /** Không có gì để hiện (gọi xong nhưng cả ba khối đều rỗng). */
  const isEmpty = computed(() =>
    !pending.value && !events.value.length && !news.value.length && !leaders.value.length
  )

  return { pending, failed, events, news, leaders, isEmpty, load }
}
