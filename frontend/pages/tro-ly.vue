<script setup lang="ts">
/**
 * Trợ lý hỏi–đáp RAG (Agentic). Cần đăng nhập.
 * Bố cục kiểu Messenger: thanh bên trái = danh sách CÂU CHUYỆN; bên phải = khung chat.
 * Chỉ gọi composable; không chứa logic nghiệp vụ.
 */
import { MessageCircle, Paperclip, Pencil, Plus, Search, Star, Trash2, X } from 'lucide-vue-next'
import type { ConversationOut } from '~/types/account'

definePageMeta({ middleware: 'auth' })

const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

const { ensureLoaded } = useAuth()
const {
  turns, pending, status, conversations, activeConvId, pendingAttachments,
  askStream, fetchStatus, reindex,
  loadConversations, openConversation, newConversation, renameConversation, deleteConversation,
  uploadAttachment, removePendingAttachment
} = useChat()

const question = ref('')
const ticker = ref('')
const reindexMsg = ref('')
const uploadErr = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
let poll: ReturnType<typeof setInterval> | null = null

function attUrl(id: number): string {
  return `${apiBase}/api/chat/attachments/${id}`
}

function isImage(mime: string): boolean {
  return mime.startsWith('image/')
}

async function onPickFiles(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  uploadErr.value = ''
  for (const f of Array.from(input.files || [])) {
    const err = await uploadAttachment(f)
    if (err) uploadErr.value = err
  }
  input.value = ''  // cho phép chọn lại cùng tệp
}

useHead({ title: 'Trợ lý hỏi–đáp — InvestStudio' })

const examples = [
  'Mã nào trong VN30 vốn hóa lớn nhất?',
  'FPT có tin tức gì đáng chú ý gần đây?',
  'So sánh định giá P/E của VCB và CTG.'
]

onMounted(async () => {
  await ensureLoaded()  // middleware đã đảm bảo đăng nhập
  await fetchStatus()
  await loadConversations()
  //  Mở sẵn cuộc gần nhất để có gì đó để xem; chưa có thì để khung trống.
  if (conversations.value.length) await openConversation(conversations.value[0].id)
  poll = setInterval(() => {
    if (status.value?.running) void fetchStatus()
  }, 4000)
})

onBeforeUnmount(() => {
  if (poll) clearInterval(poll)
})

function submit(): void {
  const q = question.value
  question.value = ''
  //  Đang mở cuộc → nối tiếp; chưa có → tạo cuộc mới ngay ở lượt hỏi này.
  askStream(q, ticker.value,
    activeConvId.value ? { conversationId: activeConvId.value } : { startConversation: true })
}

function onRename(c: ConversationOut): void {
  const t = window.prompt('Đổi tên câu chuyện:', c.title)
  if (t && t.trim()) void renameConversation(c.id, t.trim())
}

function onDelete(c: ConversationOut): void {
  if (window.confirm(`Xoá câu chuyện "${c.title}"? Không thể hoàn tác.`)) void deleteConversation(c.id)
}

async function startReindex(): Promise<void> {
  reindexMsg.value = await reindex()
  await fetchStatus()
}
</script>

<template>
  <div class="wrap">
    <header class="head">
      <h1><MessageCircle /> Trợ lý hỏi–đáp</h1>
      <div class="row nav">
        <NuxtLink to="/" class="btn"><Search /> Phân tích</NuxtLink>
        <NuxtLink to="/theo-doi" class="btn"><Star /> Theo dõi</NuxtLink>
      </div>
    </header>

    <div class="chat-layout">
      <!-- Thanh bên: danh sách câu chuyện -->
      <aside class="sidebar">
        <button type="button" class="btn primary new" @click="newConversation">
          <Plus :size="16" /> Cuộc mới
        </button>

        <ul class="conv-list">
          <li v-for="c in conversations" :key="c.id"
              :class="['conv', { active: c.id === activeConvId }]"
              @click="openConversation(c.id)">
            <span class="conv-title">{{ c.title }}</span>
            <span class="conv-actions">
              <button type="button" title="Đổi tên" @click.stop="onRename(c)"><Pencil :size="14" /></button>
              <button type="button" title="Xoá" @click.stop="onDelete(c)"><Trash2 :size="14" /></button>
            </span>
          </li>
          <li v-if="!conversations.length" class="empty">Chưa có câu chuyện nào.</li>
        </ul>

        <!-- Kho dữ liệu + lập chỉ mục (gọn ở chân) -->
        <div class="idx">
          <p v-if="status" class="note tiny">
            <b>{{ status.documents }}</b> đoạn · <b>{{ status.tickers }}</b> mã đã lập chỉ mục
          </p>
          <button type="button" class="btn idx-btn" :disabled="status?.running" @click="startReindex">
            {{ status?.running ? 'Đang lập chỉ mục…' : 'Lập chỉ mục VN30 + tin' }}
          </button>
          <p v-if="reindexMsg" class="note tiny">{{ reindexMsg }}</p>
        </div>
      </aside>

      <!-- Khung chat -->
      <section class="main">
        <div v-if="turns.length" class="thread">
          <article v-for="(turn, i) in turns" :key="i" class="turn">
            <div class="chat-row me">
              <div class="bubble me">
                <div v-if="turn.attachments && turn.attachments.length" class="atts">
                  <a v-for="(a, ai) in turn.attachments" :key="ai" :href="attUrl(a.id)"
                     target="_blank" rel="noopener" class="att">
                    <img v-if="isImage(a.mime)" :src="attUrl(a.id)" :alt="a.filename" class="att-img" />
                    <span v-else class="att-file">📄 {{ a.filename }}</span>
                  </a>
                </div>
                {{ turn.question }}
              </div>
            </div>

            <ul v-if="turn.steps && turn.steps.length" class="steps">
              <li v-for="(s, k) in turn.steps" :key="k">🔧 {{ s.label }}</li>
            </ul>

            <div v-if="turn.error" class="chat-row bot">
              <div class="bubble bot err">{{ turn.error }}</div>
            </div>
            <div v-else-if="turn.response" class="chat-row bot">
              <div class="bubble bot">
                <MarkdownText v-if="turn.response.answer" :text="turn.response.answer" class="a-text" />
                <p v-else class="a-text typing">Đang trả lời…</p>

                <details v-if="turn.response.citations.length" class="cites">
                  <summary>{{ turn.response.citations.length }} nguồn tham chiếu</summary>
                  <ul>
                    <li v-for="(c, j) in turn.response.citations" :key="j">
                      <span class="tag lv-na">{{ c.ticker }} · {{ c.doc_type }}</span>
                      <b>{{ c.title }}</b>
                      <span class="snip">{{ c.snippet }}</span>
                    </li>
                  </ul>
                </details>
              </div>
            </div>
            <div v-else class="chat-row bot">
              <div class="bubble bot typing">Đang chờ trả lời…</div>
            </div>
          </article>
        </div>
        <p v-else class="empty-thread">
          {{ activeConvId
            ? 'Câu chuyện này chưa có tin nhắn.'
            : 'Bắt đầu một câu chuyện mới — hỏi bất cứ điều gì về cổ phiếu.' }}
        </p>

        <!-- Xem trước tệp đã đính (chưa gửi) -->
        <div v-if="pendingAttachments.length" class="preview">
          <span v-for="a in pendingAttachments" :key="a.id" class="chip">
            <img v-if="isImage(a.mime)" :src="attUrl(a.id)" :alt="a.filename" class="chip-img" />
            <span v-else class="chip-file">📄</span>
            <span class="chip-name">{{ a.filename }}</span>
            <button type="button" class="chip-x" title="Bỏ" @click="removePendingAttachment(a.id)">
              <X :size="12" />
            </button>
          </span>
        </div>
        <p v-if="uploadErr" class="upload-err">{{ uploadErr }}</p>

        <form class="askbar" @submit.prevent="submit">
          <button type="button" class="btn attach" title="Đính kèm ảnh/PDF"
                  @click="fileInput?.click()">
            <Paperclip :size="16" />
          </button>
          <input ref="fileInput" type="file" class="hidden-file" multiple
                 accept="image/png,image/jpeg,image/webp,image/gif,application/pdf"
                 @change="onPickFiles" />
          <input v-model="ticker" type="text" maxlength="12" class="tk"
                 placeholder="Mã (tùy chọn)" aria-label="Giới hạn theo mã"
                 autocapitalize="characters" spellcheck="false" />
          <input v-model="question" type="text" class="q" required
                 placeholder="Hỏi điều gì đó về cổ phiếu…" aria-label="Câu hỏi" />
          <button class="btn primary" type="submit" :disabled="pending">
            {{ pending ? 'Đang hỏi…' : 'Hỏi →' }}
          </button>
        </form>
        <div class="samples">
          <button v-for="ex in examples" :key="ex" type="button" class="sample"
                  :disabled="pending" @click="question = ex">{{ ex }}</button>
        </div>
      </section>
    </div>

    <p class="disclaimer">
      Trợ lý tổng hợp dữ liệu (có thể sai) — luôn đối chiếu nguồn.
      Đây là công cụ hỗ trợ tư duy, <b>không phải khuyến nghị đầu tư</b>.
    </p>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

h1 {
  margin: 0;
  font-size: 22px;
}

.nav .btn {
  text-decoration: none;
  padding: 8px 12px;
  font-size: 12.5px;
}

/*  Bố cục 2 cột: danh sách câu chuyện | khung chat. */
.chat-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 14px;
  height: calc(100dvh - 150px);
  min-height: 440px;
  margin-top: 12px;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 10px;
  overflow: hidden;
}

.new {
  justify-content: center;
  gap: 6px;
}

.conv-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 13px;
}

.conv:hover {
  background: var(--panel2);
}

.conv.active {
  background: color-mix(in srgb, var(--accent) 20%, transparent);
}

.conv-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
}

.conv:hover .conv-actions,
.conv.active .conv-actions {
  opacity: 1;
}

.conv-actions button {
  background: none;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  padding: 2px;
  display: inline-flex;
}

.conv-actions button:hover {
  color: var(--text);
}

.empty {
  color: var(--muted);
  font-size: 12.5px;
  padding: 8px 10px;
}

.idx {
  border-top: 1px solid var(--line);
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.idx-btn {
  font-size: 12px;
  padding: 7px 10px;
}

.tiny {
  font-size: 11px;
  margin: 0;
}

/* ── Khung chat ───────────────────────────────────────────────────────────── */
.main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}

.thread {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-thread {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--muted);
  padding: 24px;
}

/*  Mỗi lượt = câu hỏi (phải) + steps + trả lời (trái), kiểu Messenger. */
.turn {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-row {
  display: flex;
}

.chat-row.me {
  justify-content: flex-end;
}

.chat-row.bot {
  justify-content: flex-start;
}

.bubble {
  max-width: 78%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  border-radius: 18px;
  overflow-wrap: anywhere;
}

.bubble.me {
  background: color-mix(in srgb, var(--accent) 88%, black);
  color: #fff;
  border-bottom-right-radius: 5px;
}

.bubble.bot {
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-bottom-left-radius: 5px;
}

.bubble.bot :deep(p:first-child) {
  margin-top: 0;
}

.bubble.bot :deep(p:last-child) {
  margin-bottom: 0;
}

.bubble.err {
  color: var(--bad);
  border-color: color-mix(in srgb, var(--bad) 45%, transparent);
}

.a-text {
  margin: 0;
}

.typing {
  color: var(--muted);
  font-style: italic;
}

.steps {
  list-style: none;
  margin: 0;
  padding: 0 2px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.steps li {
  font-size: 12px;
  color: var(--muted);
}

.cites {
  margin-top: 10px;
  font-size: 12.5px;
}

.cites summary {
  cursor: pointer;
  color: var(--muted);
}

.cites ul {
  margin: 8px 0 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cites li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-left: 3px solid var(--line);
  padding-left: 10px;
}

.snip {
  color: var(--muted);
}

/* ── Ô hỏi ───────────────────────────────────────────────────────────────── */
.askbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  border-top: 1px solid var(--line);
  padding: 10px;
}

.askbar .tk {
  width: 120px;
  flex: none;
  text-transform: uppercase;
}

.askbar .q {
  flex: 1;
  min-width: 160px;
}

.askbar input {
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 9px;
  padding: 10px 12px;
  font-size: 14px;
}

.askbar input:focus {
  outline: none;
  border-color: var(--accent);
}

.attach {
  flex: none;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
}

.hidden-file {
  display: none;
}

/*  Tệp đính trong bong bóng hỏi. */
.atts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.att {
  display: inline-flex;
}

.att-img {
  max-width: 180px;
  max-height: 180px;
  border-radius: 10px;
  display: block;
}

.att-file {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12.5px;
}

/*  Xem trước tệp chờ gửi. */
.preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px 0;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 4px 6px 4px 4px;
  font-size: 12px;
  max-width: 190px;
}

.chip-img {
  width: 26px;
  height: 26px;
  object-fit: cover;
  border-radius: 5px;
}

.chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-x {
  background: none;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  display: inline-flex;
  padding: 0;
}

.chip-x:hover {
  color: var(--bad);
}

.upload-err {
  color: var(--bad);
  font-size: 12px;
  margin: 6px 10px 0;
}

.samples {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 0 10px 10px;
}

.sample {
  border: 1px dashed var(--line);
  background: transparent;
  color: var(--muted);
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 11.5px;
  cursor: pointer;
}

.sample:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.disclaimer {
  margin-top: 12px;
  font-size: 11.5px;
  color: var(--muted);
}

@media (max-width: 760px) {
  .chat-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .sidebar {
    max-height: 240px;
  }

  .thread {
    min-height: 340px;
  }
}
</style>
