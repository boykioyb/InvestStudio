import type { WatchlistItem, WatchlistItemInput } from '~/types/account'

/**
 * Danh sách mã theo dõi của người dùng đang đăng nhập.
 *
 * Chỉ gọi API và dịch lỗi. Danh sách dùng chung qua useState để nút ⭐ ở mọi
 * nơi và trang /theo-doi luôn thấy cùng một trạng thái.
 */
export function useWatchlist() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const items = useState<WatchlistItem[]>('watchlist-items', () => [])
  const loaded = useState<boolean>('watchlist-loaded', () => false)
  const pending = ref(false)
  const error = ref('')

  function messageOf(err: unknown, fallback: string): string {
    const detail = (err as { data?: { detail?: unknown } })?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return fallback
  }

  function call<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    return $fetch<T>(`${apiBase}/api/watchlist${path}`, { credentials: 'include', ...options })
  }

  /** Đã theo dõi mã này chưa (so khớp không phân biệt hoa/thường). */
  function has(ticker: string): boolean {
    const code = ticker.toUpperCase().trim()
    return items.value.some((item) => item.ticker === code)
  }

  async function load(): Promise<void> {
    pending.value = true
    error.value = ''
    try {
      items.value = await call<WatchlistItem[]>('')
      loaded.value = true
    } catch (err) {
      error.value = messageOf(err, 'Không tải được danh sách theo dõi.')
    } finally {
      pending.value = false
    }
  }

  async function add(payload: WatchlistItemInput): Promise<boolean> {
    error.value = ''
    try {
      const created = await call<WatchlistItem>('', { method: 'POST', body: payload })
      items.value = [created, ...items.value]
      return true
    } catch (err) {
      error.value = messageOf(err, 'Không thêm được mã vào danh sách.')
      return false
    }
  }

  async function update(id: number, payload: Partial<WatchlistItemInput>): Promise<boolean> {
    error.value = ''
    try {
      const updated = await call<WatchlistItem>(`/${id}`, { method: 'PATCH', body: payload })
      items.value = items.value.map((item) => (item.id === id ? updated : item))
      return true
    } catch (err) {
      error.value = messageOf(err, 'Không cập nhật được mục theo dõi.')
      return false
    }
  }

  async function remove(id: number): Promise<void> {
    error.value = ''
    try {
      await call(`/${id}`, { method: 'DELETE' })
      items.value = items.value.filter((item) => item.id !== id)
    } catch (err) {
      error.value = messageOf(err, 'Không bỏ được mã khỏi danh sách.')
    }
  }

  /** Bỏ theo dõi theo mã (tiện cho nút ⭐ chỉ biết ticker, không biết id). */
  async function removeByTicker(ticker: string): Promise<void> {
    const code = ticker.toUpperCase().trim()
    const found = items.value.find((item) => item.ticker === code)
    if (found) await remove(found.id)
  }

  return { items, loaded, pending, error, has, load, add, update, remove, removeByTicker }
}
