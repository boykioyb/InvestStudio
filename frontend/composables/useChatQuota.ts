/**
 * Hạn mức trợ lý còn lại trong ngày — GET /api/chat/quota.
 *
 * Hiện số này TRƯỚC khi người dùng đâm vào 429 là khác biệt giữa "công cụ có
 * giới hạn rõ ràng" và "công cụ thỉnh thoảng từ chối không rõ lý do". Backend
 * đã trả về số NHỎ NHẤT giữa rổ tài khoản và rổ thiết bị nên ở đây chỉ hiển thị.
 */
import type { ChatQuota } from '~/types/account'

export function useChatQuota() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const quota = useState<ChatQuota | null>('chat-quota', () => null)

  async function load(): Promise<void> {
    try {
      quota.value = await $fetch<ChatQuota>(`${apiBase}/api/chat/quota`,
                                            { credentials: 'include' })
    } catch {
      //  Chưa đăng nhập / mạng lỗi → không hiện gì, đừng làm hỏng trang.
      quota.value = null
    }
  }

  /** Gọi sau mỗi lượt hỏi để con số giảm ngay, không phải tải lại trang. */
  function dungMotLuot(): void {
    if (quota.value) {
      quota.value = { ...quota.value, used: quota.value.used + 1,
                      remaining: Math.max(0, quota.value.remaining - 1) }
    }
  }

  return { quota, load, dungMotLuot }
}
