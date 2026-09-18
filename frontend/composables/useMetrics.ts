/**
 * Beacon số liệu sản phẩm (North Star Metric).
 *
 * CHỈ gửi sự kiện GIAO DIỆN do người dùng tạo (mở "vì sao điểm", hành động sau khi
 * xem điểm). Fire-and-forget: không chặn UI, nuốt mọi lỗi — số liệu hỏng không được
 * làm hỏng trải nghiệm. Máy chủ tự ghi `analyze`/`assistant` nên ở đây không gửi.
 *
 * Định nghĩa NSM: docs/scrum/nsm.md.
 */
type ClientEvent = 'why_open' | 'score_action'

export function useMetrics() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  function track(event: ClientEvent, opts: { ticker?: string; ref?: string } = {}): void {
    //  Chỉ chạy phía trình duyệt: sự kiện luôn bắt nguồn từ thao tác người dùng.
    if (!import.meta.client) return
    try {
      void $fetch('/api/metrics/event', {
        baseURL: apiBase,
        method: 'POST',
        body: { event, ticker: opts.ticker || '', ref: opts.ref || '' },
        // Gửi kịp cả khi người dùng rời trang ngay sau đó.
        keepalive: true
      }).catch(() => {})
    } catch {
      /* beacon số liệu không bao giờ được ném lỗi ra UI */
    }
  }

  return { track }
}
