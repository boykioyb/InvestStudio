import type { UserOut } from '~/types/account'

/**
 * Trạng thái đăng nhập dùng chung toàn app.
 *
 * Composable này CHỈ gọi API và chuyển lỗi sang tiếng Việt — không chứa logic
 * nghiệp vụ. Token là cookie httpOnly do backend đặt, JavaScript không đọc được;
 * trình duyệt tự gửi kèm mỗi request cùng origin nên ở đây không cần giữ token.
 */
export function useAuth() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  //  useState → chia sẻ giữa mọi trang/thành phần trong cùng một lần tải.
  const user = useState<UserOut | null>('auth-user', () => null)
  const ready = useState<boolean>('auth-ready', () => false)
  const pending = ref(false)
  const error = ref('')

  const isLoggedIn = computed(() => user.value !== null)

  function messageOf(err: unknown, fallback: string): string {
    const detail = (err as { data?: { detail?: unknown } })?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return fallback
  }

  /** credentials:'include' để cookie đi kèm cả khi apiBase là origin khác. */
  function call<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    return $fetch<T>(`${apiBase}${path}`, { credentials: 'include', ...options })
  }

  /** Nạp thông tin tài khoản từ cookie hiện có. Không có phiên thì user = null. */
  async function fetchMe(): Promise<void> {
    try {
      user.value = await call<UserOut>('/api/auth/me')
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  /** Gọi fetchMe đúng một lần cho mỗi lần tải trang (dùng ở onMounted). */
  async function ensureLoaded(): Promise<void> {
    if (!ready.value) await fetchMe()
  }

  async function register(email: string, password: string, displayName = ''): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      user.value = await call<UserOut>('/api/auth/register', {
        method: 'POST',
        body: { email, password, display_name: displayName }
      })
      ready.value = true
      return true
    } catch (err) {
      error.value = messageOf(err, 'Đăng ký không thành công. Thử lại sau.')
      return false
    } finally {
      pending.value = false
    }
  }

  async function login(email: string, password: string): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      user.value = await call<UserOut>('/api/auth/login', {
        method: 'POST',
        body: { email, password }
      })
      ready.value = true
      return true
    } catch (err) {
      error.value = messageOf(err, 'Đăng nhập không thành công.')
      return false
    } finally {
      pending.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await call('/api/auth/logout', { method: 'POST' })
    } catch {
      /* dù lỗi mạng vẫn xóa trạng thái phía trình duyệt */
    }
    user.value = null
  }

  return { user, ready, pending, error, isLoggedIn, fetchMe, ensureLoaded, register, login, logout }
}
