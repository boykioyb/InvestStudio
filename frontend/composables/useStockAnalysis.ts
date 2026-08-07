import type { AnalyzeOptions, ApiErrorBody, AnalyzeProgress, StockAnalysis } from '~/types/stock'

/**
 * Gọi API phân tích cổ phiếu.
 * Composable này CHỈ lấy dữ liệu và chuyển lỗi thành thông báo tiếng Việt.
 * Toàn bộ điểm số / kết luận đều do backend tính sẵn.
 */
export function useStockAnalysis() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const data = ref<StockAnalysis | null>(null)
  const pending = ref(false)
  const error = ref<string | null>(null)
  /** Bước máy chủ đang chạy (null khi rảnh). */
  const progress = ref<AnalyzeProgress | null>(null)
  /** Mã đang được hiển thị (để giữ tiêu đề khi tải lại). */
  const lastTicker = ref<string>('')

  function reset() {
    data.value = null
    error.value = null
    progress.value = null
    lastTicker.value = ''
  }

  /** Rút thông điệp lỗi: ưu tiên `detail` mà FastAPI trả về. */
  function toMessage(err: unknown): string {
    const e = err as {
      data?: ApiErrorBody
      statusCode?: number
      status?: number
      message?: string
      name?: string
    }
    const status = e?.statusCode ?? e?.status
    const detail = e?.data?.detail

    if (typeof detail === 'string' && detail.trim()) return detail
    if (status === 404) return 'Không tìm thấy mã này hoặc chưa có dữ liệu.'
    if (status === 502) return 'Tất cả nguồn dữ liệu đều lỗi. Thử lại sau ít phút.'
    if (status) return `Máy chủ trả lỗi ${status}.`

    return 'Không kết nối được tới máy chủ. Kiểm tra backend đã chạy chưa (docker compose ps).'
  }

  /** Chỉ gửi tham số có giá trị thật, tránh làm bẩn URL. */
  function buildQuery(opts: AnalyzeOptions = {}): Record<string, string | number> {
    const q: Record<string, string | number> = {}

    if (opts.pos !== undefined && opts.pos !== null) q.pos = opts.pos
    if (opts.mgmt !== undefined && opts.mgmt !== null) q.mgmt = opts.mgmt
    if (opts.cat !== undefined && opts.cat !== null) q.cat = opts.cat
    if (typeof opts.pe_sec === 'number' && Number.isFinite(opts.pe_sec)) q.pe_sec = opts.pe_sec
    if (typeof opts.pb_fair === 'number' && Number.isFinite(opts.pb_fair)) q.pb_fair = opts.pb_fair
    if (opts.source) q.source = opts.source

    return q
  }

  /**
   * Nghe tiến độ THẬT qua SSE. Mỗi sự kiện `progress` là một bước máy chủ vừa
   * bắt đầu chạy — không phải đồng hồ đếm giả ở phía trình duyệt.
   * Trả về false nếu không dùng được SSE để gọi lại bằng cách thường.
   */
  function streamAnalyze(code: string, opts: AnalyzeOptions): Promise<boolean> {
    return new Promise((resolve) => {
      if (typeof EventSource === 'undefined') return resolve(false)

      const query = new URLSearchParams(
        Object.entries(buildQuery(opts)).map(([k, v]) => [k, String(v)])
      )
      const url = `${apiBase}/api/stocks/${encodeURIComponent(code)}/stream?${query}`

      let source: EventSource
      try {
        source = new EventSource(url)
      } catch {
        return resolve(false)
      }

      let gotAnything = false
      const finish = (ok: boolean) => {
        source.close()
        resolve(ok)
      }

      source.addEventListener('progress', (ev) => {
        gotAnything = true
        try {
          progress.value = JSON.parse((ev as MessageEvent).data)
        } catch {
          /* bỏ qua gói hỏng, tiến độ chỉ để hiển thị */
        }
      })

      source.addEventListener('result', (ev) => {
        gotAnything = true
        try {
          data.value = JSON.parse((ev as MessageEvent).data) as StockAnalysis
          lastTicker.value = code
          finish(true)
        } catch {
          finish(false)
        }
      })

      source.addEventListener('error', (ev) => {
        const raw = (ev as MessageEvent).data
        if (typeof raw === 'string' && raw) {
          // Lỗi nghiệp vụ do máy chủ gửi kèm thông điệp
          try {
            const body = JSON.parse(raw) as ApiErrorBody
            data.value = null
            error.value = body.detail || 'Máy chủ báo lỗi khi phân tích.'
            gotAnything = true
            return finish(true)
          } catch {
            /* rơi xuống nhánh mất kết nối */
          }
        }
        // Mất kết nối: nếu chưa nhận được gì thì để bên gọi thử cách thường
        finish(gotAnything ? true : false)
      })
    })
  }

  async function analyze(ticker: string, opts: AnalyzeOptions = {}): Promise<void> {
    const code = (ticker || '').trim().toUpperCase()

    if (!code) {
      error.value = 'Hãy nhập mã cổ phiếu (ví dụ: FPT, VCB, HPG).'
      return
    }

    pending.value = true
    error.value = null
    progress.value = { step: 'start', label: 'Kết nối tới máy chủ', percent: 3 }

    try {
      // Ưu tiên luồng SSE để có tiến độ thật; hỏng thì quay về gọi một phát.
      if (await streamAnalyze(code, opts)) return

      const res = await $fetch<StockAnalysis>(`/api/stocks/${encodeURIComponent(code)}`, {
        baseURL: apiBase,
        query: buildQuery(opts),
        // Backend phải đi crawl nhiều nguồn nên cho phép chờ lâu.
        timeout: 60_000,
        retry: 1,
        retryDelay: 800
      })
      data.value = res
      lastTicker.value = code
    } catch (err) {
      data.value = null
      error.value = toMessage(err)
    } finally {
      pending.value = false
      progress.value = null
    }
  }

  return { data, pending, error, progress, lastTicker, apiBase, analyze, reset }
}
