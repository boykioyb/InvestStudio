/**
 * Proxy /api/** sang FastAPI — giống hệt app công khai.
 *
 * Nhờ cùng origin nên cookie đăng nhập (httpOnly) đi kèm mà không phải bật CORS,
 * và cũng ghi đè x-real-ip bằng địa chỉ socket thật để backend đếm/ghi audit
 * đúng IP người vận hành (header do client gửi lên là bịa được).
 */
export default defineEventHandler(async (event) => {
  const target = useRuntimeConfig(event).apiProxyTarget?.replace(/\/+$/, '')
  if (!target) {
    throw createError({ statusCode: 500, statusMessage: 'Chưa cấu hình NUXT_API_PROXY_TARGET.' })
  }
  const clientIp = getRequestIP(event, { xForwardedFor: false }) || ''
  return proxyRequest(event, `${target}${event.path}`, {
    headers: { 'accept-encoding': 'identity', 'x-forwarded-for': clientIp, 'x-real-ip': clientIp }
  })
})
