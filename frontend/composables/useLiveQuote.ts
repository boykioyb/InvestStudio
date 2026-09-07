import type { Quote, QuoteBatch } from '~/types/stock'

/**
 * Giá khớp GẦN REALTIME cho thẻ phân tích — poll nhẹ, lịch sự với nguồn.
 *
 * Backend đã cache chung + gộp lô, nên client chỉ việc hỏi mỗi 8s. Tự DỪNG vòng
 * lặp khi: tab bị ẩn (không ai nhìn), hoặc ngoài giờ giao dịch (giá không đổi thì
 * hỏi lại vô ích). Không tính toán nghiệp vụ ở đây — chỉ lấy số về hiển thị.
 */
const INTERVAL_MS = 8000

export function useLiveQuote(symbol: Ref<string> | string) {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')
  const sym = computed(() => String(typeof symbol === 'string' ? symbol : symbol.value || '').toUpperCase())

  const quote = ref<Quote | null>(null)
  const isOpen = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  const hidden = () => typeof document !== 'undefined' && document.hidden

  async function tick(): Promise<boolean> {
    if (!sym.value) return false
    try {
      const b = await $fetch<QuoteBatch>(`${apiBase}/api/market/quotes`, { query: { symbols: sym.value } })
      quote.value = b.quotes[0] ?? null
      isOpen.value = b.is_open
    } catch {
      // Im lặng: giữ giá cũ, lần sau thử lại.
    }
    return isOpen.value
  }

  function stop(): void {
    if (timer) { clearInterval(timer); timer = null }
  }

  function start(): void {
    stop()
    if (hidden()) return
    // Chỉ mở vòng lặp khi phiên đang chạy; ngoài phiên chỉ lấy 1 lần rồi thôi.
    void tick().then((open) => {
      if (open && !timer && !hidden()) {
        timer = setInterval(() => { if (!hidden()) void tick() }, INTERVAL_MS)
      }
    })
  }

  function onVisibility(): void {
    if (hidden()) stop()
    else start()
  }

  onMounted(() => {
    start()
    document.addEventListener('visibilitychange', onVisibility)
  })
  onBeforeUnmount(() => {
    stop()
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibility)
  })
  //  Đổi mã → reset và khởi động lại.
  watch(sym, () => { quote.value = null; start() })

  return { quote, isOpen }
}
