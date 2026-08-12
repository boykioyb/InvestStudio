import type { ChatResponse, IndexStatus } from '~/types/account'

/** Một lượt hỏi–đáp để hiển thị lịch sử hội thoại trên trang trợ lý. */
export interface ChatTurn {
  question: string
  response: ChatResponse | null
  error: string
}

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

  async function ask(question: string, ticker = ''): Promise<void> {
    const q = question.trim()
    if (!q) return
    const turn: ChatTurn = { question: q, response: null, error: '' }
    turns.value = [...turns.value, turn]
    pending.value = true
    try {
      turn.response = await call<ChatResponse>('', {
        method: 'POST',
        body: { question: q, ticker: ticker.trim().toUpperCase() || null },
        //  Backend phải nhúng câu hỏi + gọi Gemini nên cho phép chờ lâu.
        timeout: 60_000
      })
    } catch (err) {
      turn.error = messageOf(err, 'Trợ lý chưa trả lời được. Thử lại sau.')
    } finally {
      pending.value = false
    }
  }

  async function loadHistory(): Promise<void> {
    try {
      const rows = await call<Array<{ question: string; answer: string; citations: ChatResponse['citations'] }>>('/history')
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

  return { turns, pending, status, ask, loadHistory, fetchStatus, reindex }
}
