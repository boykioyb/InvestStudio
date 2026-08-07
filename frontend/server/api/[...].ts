/**
 * Proxy mọi request /api/** sang backend FastAPI.
 *
 * Vì sao cần: trình duyệt gọi API bằng CHÍNH origin đang mở trang, nên mở từ
 * điện thoại hay máy khác trong mạng LAN đều chạy — không còn phụ thuộc vào
 * "localhost" (trên máy khác, localhost là chính máy đó). Đồng thời cùng origin
 * nên không phát sinh CORS.
 *
 * Đích đến đặt bằng biến môi trường NUXT_API_PROXY_TARGET:
 *   · trong Docker  → http://backend:8000 (tên service, mạng nội bộ)
 *   · chạy máy local → http://localhost:8010
 */
export default defineEventHandler(async (event) => {
  const target = useRuntimeConfig(event).apiProxyTarget?.replace(/\/+$/, '')

  if (!target) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Chưa cấu hình NUXT_API_PROXY_TARGET cho proxy API.'
    })
  }

  // event.path giữ nguyên cả query string, ví dụ "/api/stocks/FPT?pos=1"
  return proxyRequest(event, `${target}${event.path}`, {
    // SSE cần đẩy từng khối ngay, không gom buffer
    headers: { 'accept-encoding': 'identity' }
  })
})
