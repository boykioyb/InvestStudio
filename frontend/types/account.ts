/**
 * Kiểu dữ liệu cho tài khoản người dùng, danh sách theo dõi và trợ lý RAG.
 * Khớp 1–1 với schema Pydantic ở backend (app/schemas/auth|watchlist|chat.py).
 */

export interface UserOut {
  id: number
  email: string
  display_name: string
  role: string
  /** Chưa xác minh email thì chưa dùng được trợ lý (backend chặn ở require_verified). */
  email_verified: boolean
  totp_enabled?: boolean
  created_at: string
}

/** Hạn mức trợ lý còn lại — GET /api/chat/quota. */
export interface ChatQuota {
  limit: number
  used: number
  /** Số NHỎ NHẤT giữa rổ tài khoản và rổ thiết bị: đúng cái thực sự còn dùng được. */
  remaining: number
  /** ok = bình thường · saving = quota chung đang cạn · exhausted = chỉ phục vụ người đã hỏi. */
  level: 'ok' | 'saving' | 'exhausted'
  email_verified: boolean
}

export interface WatchlistItem {
  id: number
  ticker: string
  note: string
  target_price: number | null
  target_score: number | null
  created_at: string
}

export interface WatchlistItemInput {
  ticker: string
  note?: string
  target_price?: number | null
  target_score?: number | null
}

export interface Citation {
  ticker: string
  doc_type: string
  title: string
  snippet: string
}

/** Một bước công cụ agent đã chạy (để UI hiện 'đang làm gì'). */
export interface AgentStep {
  tool: string
  label: string
}

export interface ChatResponse {
  answer: string
  conversation_id?: number | null
  citations: Citation[]
  steps?: AgentStep[]
  note: string
}

/** Một câu chuyện (thread) trong danh sách bên trái trang Trợ lý. */
export interface ConversationOut {
  id: number
  title: string
  ticker?: string | null
  updated_at: string
}

/** Tệp đã upload (trả từ /chat/upload) — có url để xem trước. */
export interface AttachmentOut {
  id: number
  filename: string
  mime: string
  size: number
  url: string
}

/** Tệp đính kèm gắn với một lượt hỏi (để hiển thị lại). */
export interface AttachmentRef {
  id: number
  filename: string
  mime: string
}

export interface IndexStatus {
  documents: number
  tickers: number
  running: boolean
  last_message: string
}

export interface Notification {
  id: number
  ticker: string
  kind: string
  message: string
  is_read: boolean
  created_at: string
}
