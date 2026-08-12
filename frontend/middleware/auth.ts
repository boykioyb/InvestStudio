/**
 * Chặn trang cần đăng nhập — chuyển sang /dang-nhap kèm ?next để quay lại.
 *
 * Chạy PHÍA TRÌNH DUYỆT thôi: trạng thái đăng nhập là cookie httpOnly + gọi
 * /me ở client, server không có nên bỏ qua SSR để tránh redirect nhầm.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return
  const { isLoggedIn, ensureLoaded } = useAuth()
  await ensureLoaded()
  if (!isLoggedIn.value) {
    return navigateTo({ path: '/dang-nhap', query: { next: to.fullPath } })
  }
})
