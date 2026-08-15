import type {
  AgentStep, AttachmentOut, AttachmentRef, ChatResponse, ConversationOut, IndexStatus
} from '~/types/account'

/** Một lượt hỏi–đáp để hiển thị lịch sử hội thoại trên trang trợ lý. */
export interface ChatTurn {
  question: string
  response: ChatResponse | null
  error: string
  /** Các bước công cụ agent đang chạy (cập nhật trực tiếp khi stream). */
  steps?: AgentStep[]
  /** Tệp đính kèm của lượt hỏi (ảnh/PDF) — để hiển thị trong bong bóng. */
  attachments?: AttachmentRef[]
}

/** Tuỳ chọn cuộc trò chuyện khi hỏi (trang Trợ lý). Widget nổi bỏ trống → phẳng. */
export interface AskOptions {
  conversationId?: number | null
  startConversation?: boolean
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
  //  Danh sách câu chuyện + cuộc đang mở (chỉ dùng ở trang Trợ lý).
  const conversations = ref<ConversationOut[]>([])
  const activeConvId = ref<number | null>(null)
  //  Tệp đã upload nhưng CHƯA gửi (chờ đính vào câu hỏi kế tiếp).
  const pendingAttachments = ref<AttachmentOut[]>([])

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

  /** Upload một tệp (ảnh/PDF); OK → thêm vào chờ-gửi. Trả chuỗi lỗi ('' nếu thành công). */
  async function uploadAttachment(file: File): Promise<string> {
    const form = new FormData()
    form.append('file', file)
    try {
      const out = await $fetch<AttachmentOut>(`${apiBase}/api/chat/upload`, {
        method: 'POST', body: form, credentials: 'include'
      })
      pendingAttachments.value = [...pendingAttachments.value, out]
      return ''
    } catch (err) {
      return messageOf(err, 'Tải tệp thất bại.')
    }
  }

  function removePendingAttachment(id: number): void {
    pendingAttachments.value = pendingAttachments.value.filter((a) => a.id !== id)
  }

  /** Chốt attachment cho lượt sắp gửi: trả refs (để hiển thị) + ids, rồi xoá chờ-gửi. */
  function takeAttachments(): { refs: AttachmentRef[]; ids: number[] } {
    const atts = pendingAttachments.value
    pendingAttachments.value = []
    return {
      refs: atts.map((a) => ({ id: a.id, filename: a.filename, mime: a.mime })),
      ids: atts.map((a) => a.id)
    }
  }

  /** Sau một lượt có gắn cuộc: bám theo id cuộc + làm mới danh sách (đổi tên/thứ tự). */
  async function afterConversationTurn(resp: ChatResponse | null): Promise<void> {
    if (resp?.conversation_id) {
      activeConvId.value = resp.conversation_id
      await loadConversations()
    }
  }

  async function ask(question: string, ticker = '', opts: AskOptions = {}): Promise<void> {
    const q = question.trim()
    if (!q) return
    const history = historyPayload()
    const { refs, ids } = takeAttachments()
    const turn: ChatTurn = { question: q, response: null, error: '', steps: [], attachments: refs }
    turns.value = [...turns.value, turn]
    pending.value = true
    try {
      turn.response = await call<ChatResponse>('', {
        method: 'POST',
        body: {
          question: q, ticker: ticker.trim().toUpperCase() || null, history,
          conversation_id: opts.conversationId ?? null,
          start_conversation: !!opts.startConversation,
          attachment_ids: ids
        },
        //  Agent có thể gọi nhiều vòng Gemini + phân tích mã nên cho chờ lâu.
        timeout: 90_000
      })
      await afterConversationTurn(turn.response)
    } catch (err) {
      turn.error = messageOf(err, 'Trợ lý chưa trả lời được. Thử lại sau.')
    } finally {
      pending.value = false
    }
  }

  /** Hỏi và nhận câu trả lời THEO LUỒNG (SSE). Không có EventSource → dùng ask thường. */
  function askStream(question: string, ticker = '', opts: AskOptions = {}): void {
    const q = question.trim()
    if (!q) return
    if (typeof EventSource === 'undefined') {
      void ask(q, ticker, opts)
      return
    }
    const history = historyPayload()
    const { refs, ids } = takeAttachments()
    const turn: ChatTurn = { question: q, response: { answer: '', citations: [], note: '' }, error: '', steps: [], attachments: refs }
    turns.value = [...turns.value, turn]
    pending.value = true

    const params = new URLSearchParams({ question: q })
    const tk = ticker.trim().toUpperCase()
    if (tk) params.set('ticker', tk)
    if (history.length) params.set('history', JSON.stringify(history))
    if (opts.conversationId != null) params.set('conversation_id', String(opts.conversationId))
    if (opts.startConversation) params.set('start_conversation', 'true')
    if (ids.length) params.set('attachment_ids', ids.join(','))

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
      void afterConversationTurn(turn.response)
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
      const rows = await call<Array<{ question: string; answer: string; citations: ChatResponse['citations']; attachments?: AttachmentRef[] }>>(`/history${qs}`)
      turns.value = rows.map((h) => ({
        question: h.question,
        response: { answer: h.answer, citations: h.citations, note: '' },
        error: '',
        attachments: h.attachments || []
      }))
    } catch {
      /* chưa đăng nhập hoặc chưa có lịch sử — bỏ qua */
    }
  }

  /** Danh sách câu chuyện của người dùng (mới → cũ). */
  async function loadConversations(): Promise<void> {
    try {
      conversations.value = await call<ConversationOut[]>('/conversations')
    } catch {
      conversations.value = []
    }
  }

  /** Mở một câu chuyện: nạp toàn bộ tin nhắn của nó vào khung chat. */
  async function openConversation(id: number): Promise<void> {
    activeConvId.value = id
    try {
      const rows = await call<Array<{ question: string; answer: string; citations: ChatResponse['citations']; attachments?: AttachmentRef[] }>>(`/conversations/${id}/messages`)
      turns.value = rows.map((h) => ({
        question: h.question,
        response: { answer: h.answer, citations: h.citations, note: '' },
        error: '',
        attachments: h.attachments || []
      }))
    } catch {
      turns.value = []
    }
  }

  /** Bắt đầu câu chuyện mới: xoá khung + bỏ cuộc đang mở (cuộc sẽ tạo ở lượt hỏi đầu). */
  function newConversation(): void {
    activeConvId.value = null
    turns.value = []
  }

  async function renameConversation(id: number, title: string): Promise<void> {
    const t = title.trim()
    if (!t) return
    try {
      await call(`/conversations/${id}`, { method: 'PATCH', body: { title: t } })
      await loadConversations()
    } catch { /* bỏ qua */ }
  }

  async function deleteConversation(id: number): Promise<void> {
    try {
      await call(`/conversations/${id}`, { method: 'DELETE' })
    } catch { /* bỏ qua */ }
    if (activeConvId.value === id) newConversation()
    await loadConversations()
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

  return {
    turns, pending, status, conversations, activeConvId, pendingAttachments,
    ask, askStream, loadHistory, fetchStatus, reindex,
    loadConversations, openConversation, newConversation, renameConversation, deleteConversation,
    uploadAttachment, removePendingAttachment
  }
}
