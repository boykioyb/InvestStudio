/**
 * Gọi API quản trị. Cùng origin (qua proxy Nuxt) nên cookie đăng nhập tự đi kèm.
 *
 * Bóc lỗi về một chỗ: backend luôn trả `{detail}`, và ba mã trạng thái dưới đây
 * có ý nghĩa RẤT khác nhau với người vận hành nên phải nói rõ, đừng gộp thành
 * "có lỗi xảy ra".
 */
export function useAdminApi() {
  async function request<T>(path: string, options: any = {}): Promise<T> {
    try {
      return await $fetch<T>(`/api${path}`, { credentials: 'include', ...options })
    } catch (error: any) {
      const status = error?.response?.status
      const detail = error?.data?.detail
      if (status === 401) {
        //  Phiên chết GIỮA CHỪNG (token bị thu hồi, hết hạn) → đưa thẳng ra
        //  trang đăng nhập kèm đường quay lại, đừng để người dùng nhìn dòng chữ
        //  đỏ rồi không biết bấm vào đâu.
        useAdminUser().value = null
        await toLogin(useRoute().fullPath)
        throw new Error('Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.')
      }
      if (status === 403) {
        //  "Chưa bật 2 lớp" khác hẳn "không có quyền": cái đầu tự sửa được, nên
        //  đưa thẳng người dùng tới nơi bật thay vì để họ đọc lỗi rồi tự mò.
        //  Backend đánh dấu bằng header X-Admin-Setup (app/api/deps.py).
        if (error?.response?.headers?.get('x-admin-setup') === 'totp') {
          const route = useRoute()
          if (route.path !== '/settings') await navigateTo('/settings?warn=2fa')
        }
        throw new Error(detail || 'Tài khoản này không có quyền quản trị.')
      }
      if (status === 404 && path.startsWith('/admin')) {
        throw new Error('Không truy cập được khu quản trị từ địa chỉ IP hiện tại.')
      }
      throw new Error(detail || 'Không gọi được API quản trị.')
    }
  }

  return {
    request,
    get: <T>(path: string) => request<T>(path),
    put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body }),
    patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body }),
    post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
    del: <T>(path: string) => request<T>(path, { method: 'DELETE' })
  }
}

export function useAdminFormat() {
  const number = (value: number | null | undefined) =>
    value === null || value === undefined ? '—' : new Intl.NumberFormat('vi-VN').format(value)
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`
  const dateTime = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '—'
  return { number, percent, dateTime }
}
