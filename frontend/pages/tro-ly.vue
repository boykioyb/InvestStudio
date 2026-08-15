<script setup lang="ts">
/**
 * Trợ lý hỏi–đáp RAG. Cần đăng nhập.
 * Hỏi bằng ngôn ngữ tự nhiên; câu trả lời do backend tổng hợp từ dữ liệu VN30 +
 * tin tức đã lập chỉ mục, kèm nguồn để người dùng tự kiểm chứng.
 */
import { MessageCircle, Search, Star } from 'lucide-vue-next'

definePageMeta({ middleware: 'auth' })

const { ensureLoaded } = useAuth()
const { turns, pending, status, askStream, loadHistory, fetchStatus, reindex } = useChat()

const question = ref('')
const ticker = ref('')
const reindexMsg = ref('')
let poll: ReturnType<typeof setInterval> | null = null

useHead({ title: 'Trợ lý hỏi–đáp — InvestStudio' })

const examples = [
  'Mã nào trong VN30 có ROE cao nhất?',
  'FPT có tin tức gì đáng chú ý gần đây?',
  'So sánh định giá P/E của VCB và CTG.'
]

onMounted(async () => {
  await ensureLoaded()  // middleware đã đảm bảo đăng nhập
  await fetchStatus()
  if (!turns.value.length) await loadHistory()  // tải lại hội thoại đã lưu
  //  Khi đang lập chỉ mục thì tự làm mới trạng thái cho người dùng thấy tiến độ.
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
  askStream(q, ticker.value)
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

    <!-- Trạng thái kho dữ liệu -->
    <div class="card status">
      <div>
        <p class="sec-title">Kho dữ liệu RAG</p>
        <p v-if="status" class="note">
          <b>{{ status.documents }}</b> đoạn văn bản · <b>{{ status.tickers }}</b> mã đã lập chỉ mục.
          <span v-if="status.last_message"> — {{ status.last_message }}</span>
        </p>
        <p v-else class="note">Chưa lấy được trạng thái.</p>
      </div>
      <button type="button" class="btn" :disabled="status?.running" @click="startReindex">
        {{ status?.running ? 'Đang lập chỉ mục…' : 'Lập chỉ mục VN30 + tin' }}
      </button>
    </div>
    <p v-if="reindexMsg" class="msg ok">{{ reindexMsg }}</p>

    <!-- Ô hỏi -->
    <div class="card">
      <form class="askbar" @submit.prevent="submit">
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
    </div>

    <!-- Hội thoại -->
    <div v-if="turns.length" class="thread">
      <article v-for="(turn, i) in turns" :key="i" class="turn">
        <div class="chat-row me">
          <div class="bubble me">{{ turn.question }}</div>
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

    <p class="disclaimer">
      Trợ lý chỉ tổng hợp dữ liệu đã lập chỉ mục và có thể sai — luôn đối chiếu nguồn gốc.
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

.status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.askbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.askbar .tk {
  width: 130px;
  flex: none;
  text-transform: uppercase;
}

.askbar .q {
  flex: 1;
  min-width: 200px;
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

.samples {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
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

.thread {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

/*  Mỗi lượt = hàng câu hỏi (phải) + steps + hàng trả lời (trái), kiểu Messenger. */
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
  max-width: 74%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  border-radius: 18px;
  overflow-wrap: anywhere;
}

/*  Câu hỏi: bong bóng xanh đặc, chữ trắng (kiểu Messenger). */
.bubble.me {
  background: color-mix(in srgb, var(--accent) 88%, black);
  color: #fff;
  border-bottom-right-radius: 5px;
}

/*  Câu trả lời: bong bóng xám trung tính, góc dưới-trái vát. */
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

/*  Bước công cụ agent — nhỏ, mờ, canh trái dưới câu hỏi. */
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
</style>
