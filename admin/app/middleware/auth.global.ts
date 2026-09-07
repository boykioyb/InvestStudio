/**
 * Chưa đăng nhập (hoặc không phải quản trị) → đẩy thẳng ra trang đăng nhập.
 *
 * Trước đây mỗi trang tự bắt lỗi 401 rồi hiện một dòng chữ đỏ "phiên hết hạn" —
 * đúng nhưng cụt: người dùng đọc xong không biết bấm vào đâu. Chặn ngay ở
 * middleware thì không trang nào phải tự lo việc này nữa.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/dang-nhap') return

  const me = useAdminUser()
  if (me.value) return

  try {
    const user = await $fetch<any>('/api/auth/me', { credentials: 'include' })
    if (user?.role !== 'admin') return toLogin(to.fullPath, 'quyen')
    me.value = user
  } catch {
    return toLogin(to.fullPath)
  }
})
