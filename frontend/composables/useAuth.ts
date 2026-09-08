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

  async function changePassword(oldPassword: string, newPassword: string): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      await call('/api/auth/change-password', {
        method: 'POST',
        body: { old_password: oldPassword, new_password: newPassword }
      })
      return true
    } catch (err) {
      error.value = messageOf(err, 'Đổi mật khẩu không thành công.')
      return false
    } finally {
      pending.value = false
    }
  }

  /** Xác minh email bằng token trong thư. Thành công thì có phiên mới luôn. */
  async function verifyEmail(token: string): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      user.value = await call<UserOut>(`/api/auth/verify?token=${encodeURIComponent(token)}`,
                                       { method: 'POST' })
      ready.value = true
      return true
    } catch (err) {
      error.value = messageOf(err, 'Liên kết xác minh không hợp lệ hoặc đã hết hạn.')
      return false
    } finally {
      pending.value = false
    }
  }

  async function resendVerification(): Promise<string> {
    pending.value = true
    error.value = ''
    try {
      const res = await call<{ detail: string }>('/api/auth/resend-verification',
                                                 { method: 'POST' })
      return res.detail
    } catch (err) {
      error.value = messageOf(err, 'Chưa gửi lại được thư. Thử lại sau ít phút.')
      return ''
    } finally {
      pending.value = false
    }
  }

  /** Quên mật khẩu. Backend cố tình trả lời GIỐNG NHAU dù email có tồn tại hay không. */
  async function forgotPassword(email: string): Promise<string> {
    pending.value = true
    error.value = ''
    try {
      const res = await call<{ detail: string }>('/api/auth/forgot-password',
                                                 { method: 'POST', body: { email } })
      return res.detail
    } catch (err) {
      error.value = messageOf(err, 'Chưa gửi được liên kết. Thử lại sau ít phút.')
      return ''
    } finally {
      pending.value = false
    }
  }

  async function resetPassword(token: string, newPassword: string): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      await call('/api/auth/reset-password',
                 { method: 'POST', body: { token, new_password: newPassword } })
      //  Đặt lại mật khẩu thu hồi mọi phiên cũ → xóa trạng thái phía trình duyệt.
      user.value = null
      return true
    } catch (err) {
      error.value = messageOf(err, 'Liên kết không hợp lệ hoặc đã dùng rồi.')
      return false
    } finally {
      pending.value = false
    }
  }

  /** Xóa tài khoản — KHÔNG hoàn tác được, backend xóa cả dữ liệu con. */
  async function deleteAccount(password: string): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      await call('/api/auth/me', { method: 'DELETE', body: { password } })
      user.value = null
      return true
    } catch (err) {
      error.value = messageOf(err, 'Xóa tài khoản không thành công.')
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

  return { user, ready, pending, error, isLoggedIn, fetchMe, ensureLoaded, register, login,
           changePassword, logout, verifyEmail, resendVerification, forgotPassword,
           resetPassword, deleteAccount }
}
