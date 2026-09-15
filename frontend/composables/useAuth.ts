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

  //  Ở SSR, cookie httpOnly của người dùng nằm trong request đến máy chủ Nuxt —
  //  chuyển tiếp nó tới /me để backend nhận ra phiên. Nhờ vậy trang render ĐÚNG
  //  trạng thái đăng nhập ngay từ khung hình đầu (không nháy chưa-đăng-nhập/field
  //  rỗng rồi mới nhảy ra dữ liệu). Trên trình duyệt thì cookie tự đi kèm.
  const reqCookie = import.meta.server ? useRequestHeaders(['cookie']) : undefined

  /** credentials:'include' để cookie đi kèm cả khi apiBase là origin khác. */
  function call<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    return $fetch<T>(`${apiBase}${path}`, {
      credentials: 'include',
      ...(reqCookie ? { headers: reqCookie } : {}),
      ...options
    })
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

  //  ── Đăng nhập ngoài (Google) ───────────────────────────────────────────
  //  Nút chỉ hiện/hoạt động thật khi backend đã có client id + secret.
  const googleEnabled = useState<boolean>('auth-google-enabled', () => false)

  async function loadOauthConfig(): Promise<void> {
    try {
      const cfg = await call<{ google: boolean }>('/api/auth/oauth-config')
      googleEnabled.value = !!cfg.google
    } catch {
      googleEnabled.value = false
    }
  }

  /**
   * Bắt đầu đăng nhập Google. Lấy URL từ backend (kèm cookie chống giả mạo) rồi
   * ĐIỀU HƯỚNG cả trang sang Google — không dùng redirect phía backend vì proxy
   * /api tự đi theo redirect nên sẽ nuốt mất.
   */
  async function startGoogle(next = '/'): Promise<void> {
    error.value = ''
    try {
      const { url } = await call<{ url: string }>(
        `/api/auth/google/start?next=${encodeURIComponent(next)}`)
      window.location.href = url
    } catch (err) {
      error.value = messageOf(err, 'Chưa mở được đăng nhập Google. Thử lại sau.')
    }
  }

  /** Trạng thái cho giao diện biết đang phải giải câu đố chống tự động. */
  const solvingChallenge = ref(false)

  async function solveChallenge(): Promise<{ pow_nonce: string; pow_answer: string }> {
    const { nonce, difficulty } = await call<{ nonce: string; difficulty: number }>(
      '/api/auth/challenge')
    solvingChallenge.value = true
    try {
      return { pow_nonce: nonce, pow_answer: await solveProofOfWork(nonce, difficulty) }
    } finally {
      solvingChallenge.value = false
    }
  }

  async function register(email: string, password: string, displayName = ''): Promise<boolean> {
    pending.value = true
    error.value = ''
    const body: Record<string, unknown> = { email, password, display_name: displayName }
    try {
      user.value = await call<UserOut>('/api/auth/register', { method: 'POST', body })
      ready.value = true
      return true
    } catch (err) {
      //  Thiết bị đã tạo nhiều tài khoản → backend đòi câu đố. Giải rồi gửi lại
      //  MỘT lần, thay vì bắt người dùng tự hiểu và bấm lại.
      const canDo = (err as { response?: Response })?.response?.headers?.get?.('x-challenge-required')
      if (canDo === 'pow') {
        try {
          Object.assign(body, await solveChallenge())
          user.value = await call<UserOut>('/api/auth/register', { method: 'POST', body })
          ready.value = true
          return true
        } catch (err2) {
          error.value = messageOf(err2, 'Đăng ký không thành công. Thử lại sau.')
          return false
        }
      }
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

  async function setAlertEmail(bat: boolean): Promise<boolean> {
    pending.value = true
    error.value = ''
    try {
      user.value = await call<UserOut>('/api/auth/preferences',
                                       { method: 'PATCH', body: { alert_email: bat } })
      return true
    } catch (err) {
      error.value = messageOf(err, 'Chưa lưu được tùy chọn. Thử lại sau.')
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

  return { user, ready, pending, error, solvingChallenge, isLoggedIn, googleEnabled,
           fetchMe, ensureLoaded, loadOauthConfig, startGoogle, register, login,
           changePassword, logout, verifyEmail, resendVerification, forgotPassword,
           resetPassword, deleteAccount, setAlertEmail }
}
