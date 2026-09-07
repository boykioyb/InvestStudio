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

  /*
   * IP THẬT của người gọi, lấy từ socket — KHÔNG lấy từ header.
   *
   * Backend đếm hạn mức theo IP, mà qua proxy này nó chỉ nhìn thấy IP của
   * container frontend: nếu không đính kèm IP thật thì mọi người dùng chung một
   * "rổ" hạn mức. Ngược lại, nếu tin header `x-forwarded-for` do trình duyệt gửi
   * lên thì ai cũng tự khai một IP mới cho mỗi request và vượt mọi rào đếm.
   *
   * Vì vậy: GHI ĐÈ (không nối thêm) hai header dưới bằng địa chỉ socket thật.
   * `xForwardedFor: false` là cố ý — khi nào có reverse proxy thật (Caddy/Nginx)
   * đứng trước Nuxt thì mới bật lên, vì lúc đó header do proxy đó ghi mới đáng tin.
   */
  const clientIp = getRequestIP(event, { xForwardedFor: false }) || ''

  // event.path giữ nguyên cả query string, ví dụ "/api/stocks/FPT?pos=1"
  return proxyRequest(event, `${target}${event.path}`, {
    headers: {
      // SSE cần đẩy từng khối ngay, không gom buffer
      'accept-encoding': 'identity',
      'x-forwarded-for': clientIp,
      'x-real-ip': clientIp
    }
  })
})
