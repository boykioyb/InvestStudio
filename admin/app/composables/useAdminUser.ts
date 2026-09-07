/**
 * Người đang đăng nhập ở khu quản trị (dùng chung giữa middleware, layout, trang).
 *
 * Giữ trong `useState` để mỗi lần chuyển trang không phải hỏi lại `/api/auth/me` —
 * middleware chỉ gọi khi chưa biết là ai.
 */
export function useAdminUser() {
  return useState<any | null>('admin-user', () => null)
}

/** Đưa về trang đăng nhập, nhớ đường đang định vào để quay lại sau khi đăng nhập. */
export function toLogin(next?: string, loi?: string) {
  const params = new URLSearchParams()
  if (next && next !== '/dang-nhap') params.set('next', next)
  if (loi) params.set('loi', loi)
  const query = params.toString()
  return navigateTo(`/dang-nhap${query ? `?${query}` : ''}`)
}
