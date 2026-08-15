import type { AgentStep, ChatResponse, IndexStatus } from '~/types/account'

/** Một lượt hỏi–đáp để hiển thị lịch sử hội thoại trên trang trợ lý. */
export interface ChatTurn {
  question: string
  response: ChatResponse | null
  error: string
  /** Các bước công cụ agent đang chạy (cập nhật trực tiếp khi stream). */
  steps?: AgentStep[]
}

//  Số lượt gần nhất gửi kèm để agent giữ ngữ cảnh nối tiếp ("ROE của nó?").
const HISTORY_TURNS = 6

/**
 * Trợ lý RAG: gửi câu hỏi, xem trạng thái kho dữ liệu, kích hoạt lập chỉ mục.
 * Chỉ gọi API và dịch lỗi — mọi truy xuất/sinh câu trả lời đều ở backend.
 */
export function useChat() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

  const turns = ref<ChatTurn[]>([])
  const pending = ref(false)
  const status = ref<IndexStatus | null>(null)

  function messageOf(err: unknown, fallback: string): string {
    const detail = (err as { data?: { detail?: unknown } })?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return fallback
  }

  function call<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    return $fetch<T>(`${apiBase}/api/chat${path}`, { credentials: 'include', ...options })
  }

  /** Các lượt đã hoàn tất gần nhất, dạng {question, answer} để gửi kèm câu hỏi mới. */
  function historyPayload(): Array<{ question: string; answer: string }> {
    return turns.value
      .filter((t) => t.response && !t.error)
      .slice(-HISTORY_TURNS)
      .map((t) => ({ question: t.question, answer: (t.response?.answer || '').slice(0, 1200) }))
  }

  async function ask(question: string, ticker = ''): Promise<void> {
    const q = question.trim()
    if (!q) return
    const history = historyPayload()
    const turn: ChatTurn = { question: q, response: null, error: '', steps: [] }
    turns.value = [...turns.value, turn]
    pending.value = true
    try {
      turn.response = await call<ChatResponse>('', {
        method: 'POST',
        body: { question: q, ticker: ticker.trim().toUpperCase() || null, history },
        //  Agent có thể gọi nhiều vòng Gemini + phân tích mã nên cho chờ lâu.
        timeout: 90_000
      })
    } catch (err) {
      turn.error = messageOf(err, 'Trợ lý chưa trả lời được. Thử lại sau.')
    } finally {
      pending.value = false
    }
  }

  /** Hỏi và nhận câu trả lời THEO LUỒNG (SSE). Không có EventSource → dùng ask thường. */
  function askStream(question: string, ticker = ''): void {
    const q = question.trim()
    if (!q) return
    if (typeof EventSource === 'undefined') {
      void ask(q, ticker)
      return
    }
    const history = historyPayload()
    const turn: ChatTurn = { question: q, response: { answer: '', citations: [], note: '' }, error: '', steps: [] }
    turns.value = [...turns.value, turn]
    pending.value = true

    const params = new URLSearchParams({ question: q })
    const tk = ticker.trim().toUpperCase()
    if (tk) params.set('ticker', tk)
    if (history.length) params.set('history', JSON.stringify(history))

    const source = new EventSource(`${apiBase}/api/chat/stream?${params.toString()}`, {
      withCredentials: true
    })
    let done = false
    const finish = () => {
      source.close()
      pending.value = false
    }
    //  Mỗi bước công cụ agent chạy → hiện ngay ("🔧 Phân tích mã FPT…").
    source.addEventListener('step', (ev) => {
      try {
        const s = JSON.parse((ev as MessageEvent).data) as AgentStep
        if (turn.steps) turn.steps = [...turn.steps, s]
      } catch { /* bỏ gói hỏng */ }
    })
    source.addEventListener('delta', (ev) => {
      try {
        if (turn.response) turn.response.answer += JSON.parse((ev as MessageEvent).data).text
      } catch { /* bỏ gói hỏng */ }
    })
    source.addEventListener('final', (ev) => {
      done = true
      try { turn.response = JSON.parse((ev as MessageEvent).data) } catch { /* giữ phần đã nhận */ }
      finish()
    })
    source.addEventListener('error', (ev) => {
      const raw = (ev as MessageEvent).data
      if (typeof raw === 'string' && raw) {
        try { turn.error = JSON.parse(raw).detail } catch { /* bỏ qua */ }
      }
      if (!done && !turn.error) turn.error = 'Trợ lý chưa trả lời được. Thử lại sau.'
      finish()
    })
  }

  /** Tải lịch sử đã lưu. Có `ticker` → chỉ lấy hội thoại của mã đó (widget nổi). */
  async function loadHistory(ticker = ''): Promise<void> {
    const tk = ticker.trim().toUpperCase()
    const qs = tk ? `?ticker=${encodeURIComponent(tk)}` : ''
    try {
      const rows = await call<Array<{ question: string; answer: string; citations: ChatResponse['citations'] }>>(`/history${qs}`)
      turns.value = rows.map((h) => ({
        question: h.question,
        response: { answer: h.answer, citations: h.citations, note: '' },
        error: ''
      }))
    } catch {
      /* chưa đăng nhập hoặc chưa có lịch sử — bỏ qua */
    }
  }

  async function fetchStatus(): Promise<void> {
    try {
      status.value = await call<IndexStatus>('/status')
    } catch {
      status.value = null
    }
  }

  async function reindex(): Promise<string> {
    try {
      status.value = await call<IndexStatus>('/reindex', { method: 'POST' })
      return status.value.last_message
    } catch (err) {
      return messageOf(err, 'Không khởi động được việc lập chỉ mục.')
    }
  }

  return { turns, pending, status, ask, askStream, loadHistory, fetchStatus, reindex }
}
