import type { Notification } from '~/types/account'

/**
 * Thông báo trong app (cảnh báo ngưỡng theo dõi). Chỉ gọi API + giữ trạng thái
 * chung; job nền ở backend mới là nơi tạo thông báo.
 */
export function useNotifications() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const items = useState<Notification[]>('notif-items', () => [])
  const unread = useState<number>('notif-unread', () => 0)

  function call<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    return $fetch<T>(`${apiBase}/api/notifications${path}`, { credentials: 'include', ...options })
  }

  async function fetchUnread(): Promise<void> {
    try {
      unread.value = (await call<{ count: number }>('/unread-count')).count
    } catch {
      unread.value = 0
    }
  }

  async function load(): Promise<void> {
    try {
      items.value = await call<Notification[]>('')
    } catch {
      items.value = []
    }
  }

  async function markRead(id: number): Promise<void> {
    await call(`/${id}/read`, { method: 'POST' })
    const found = items.value.find((n) => n.id === id)
    if (found && !found.is_read) {
      found.is_read = true
      unread.value = Math.max(0, unread.value - 1)
    }
  }

  async function markAllRead(): Promise<void> {
    await call('/read-all', { method: 'POST' })
    items.value = items.value.map((n) => ({ ...n, is_read: true }))
    unread.value = 0
  }

  return { items, unread, fetchUnread, load, markRead, markAllRead }
}
