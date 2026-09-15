/**
 * Nạp phiên đăng nhập NGAY Ở SSR (và một lần ở client cho SPA).
 *
 * Chạy trước route middleware, nên tới lúc render trang thì trạng thái đăng nhập
 * đã có: header và các trang cần tài khoản hiện đúng từ KHUNG HÌNH ĐẦU, không
 * nháy "chưa đăng nhập" rồi mới lật, cũng không để field trống rồi mới nhảy ra
 * dữ liệu. Kết quả từ server được chuyển sang client nên client không gọi lại.
 */
export default defineNuxtPlugin(async () => {
  await useAuth().ensureLoaded()
})
