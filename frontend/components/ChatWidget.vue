<script setup lang="ts">
/**
 * Trợ lý RAG dạng POPUP nổi ở góc phải dưới, dùng được ở mọi trang.
 *
 * Khi đang mở một mã (trang phân tích), tự lấy mã đó làm ngữ cảnh — hỏi là hỏi
 * ngay trên mã đang xem. Chỉ hiển thị và gọi composable; không chứa logic.
 */
import { LogIn, MessageCircle, Send, X } from 'lucide-vue-next'

const route = useRoute()
const { turns, pending, askStream } = useChat()
const { isLoggedIn, ensureLoaded } = useAuth()
const activeTicker = useActiveTicker()

const open = ref(false)
const question = ref('')
const scoped = ref(true) // mặc định: giới hạn trong mã đang xem

onMounted(ensureLoaded)

//  Ẩn widget ở những nơi thừa: trang trợ lý toàn màn hình và trang đăng nhập/ký.
const hidden = computed(() => ['/tro-ly', '/dang-nhap', '/dang-ky'].includes(route.path))

//  Chỉ coi là "đang xem mã" khi ở trang phân tích và đã có mã.
const ticker = computed(() => (route.path === '/' ? activeTicker.value : ''))

//  Đổi mã đang xem → bắt đầu hội thoại MỚI (không lẫn tin nhắn của mã cũ).
watch(ticker, () => { turns.value = [] })

const examples = computed(() =>
  ticker.value
    ? [`Điểm mạnh yếu của ${ticker.value}?`, `${ticker.value} có tin gì mới?`]
    : ['Mã nào vốn hóa lớn nhất VN30?', 'So sánh P/E của VCB và CTG']
)

function submit(): void {
  const q = question.value
  question.value = ''
  //  Có mã đang xem + đang bật giới hạn → hỏi trong đúng mã đó. Trả lời theo luồng.
  askStream(q, ticker.value && scoped.value ? ticker.value : '')
}
</script>

<template>
  <div v-if="!hidden" class="widget">
    <!-- Nút nổi -->
    <button
      v-if="!open"
      type="button"
      class="fab"
      aria-label="Mở trợ lý hỏi đáp"
      @click="open = true"
    >
      <MessageCircle />
      <span v-if="ticker" class="fab-tag">{{ ticker }}</span>
    </button>

    <!-- Bảng chat -->
    <section v-else class="panel" role="dialog" aria-label="Trợ lý hỏi đáp">
      <header class="head">
        <div class="title">
          <MessageCircle /> Trợ lý
          <span v-if="ticker" class="ctx">· {{ ticker }}</span>
        </div>
        <button type="button" class="x" aria-label="Đóng" @click="open = false"><X /></button>
      </header>

      <!-- Chưa đăng nhập -->
      <div v-if="!isLoggedIn" class="body center">
        <p class="note">Đăng nhập để dùng trợ lý hỏi đáp.</p>
        <NuxtLink class="btn primary" :to="{ path: '/dang-nhap', query: { next: route.fullPath } }">
          <LogIn /> Đăng nhập
        </NuxtLink>
      </div>

      <template v-else>
        <div class="body">
          <p v-if="!turns.length" class="note">
            Hỏi bất cứ điều gì về cổ phiếu.<span v-if="ticker"> Đang trong ngữ cảnh <b>{{ ticker }}</b>.</span>
          </p>

          <article v-for="(turn, i) in turns" :key="i" class="turn">
            <p class="q"><b>Bạn:</b> {{ turn.question }}</p>
            <div v-if="turn.error" class="a err">{{ turn.error }}</div>
            <div v-else-if="turn.response" class="a">
              <MarkdownText v-if="turn.response.answer" :text="turn.response.answer" class="txt" />
              <p v-else class="txt typing">Đang trả lời…</p>
              <details v-if="turn.response.citations.length" class="cites">
                <summary>{{ turn.response.citations.length }} nguồn</summary>
                <ul>
                  <li v-for="(c, j) in turn.response.citations" :key="j">
                    <b>{{ c.ticker }}</b> · {{ c.title }}
                  </li>
                </ul>
              </details>
            </div>
            <p v-else class="a note">Đang trả lời…</p>
          </article>
        </div>

        <div class="samples">
          <button v-for="ex in examples" :key="ex" type="button" class="sample"
                  :disabled="pending" @click="question = ex">{{ ex }}</button>
        </div>

        <form class="ask" @submit.prevent="submit">
          <label v-if="ticker" class="scope" :title="`Chỉ tìm trong dữ liệu của ${ticker}`">
            <input v-model="scoped" type="checkbox" /> chỉ {{ ticker }}
          </label>
          <div class="ask-row">
            <input v-model="question" type="text" required
                   placeholder="Nhập câu hỏi…" aria-label="Câu hỏi" />
            <button class="btn primary" type="submit" :disabled="pending" aria-label="Gửi">
              <span v-if="pending">…</span><Send v-else />
            </button>
          </div>
        </form>
      </template>
    </section>
  </div>
</template>

<style scoped>
.widget {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 60;
}

.fab {
  position: relative;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: var(--accent);
  color: #04121f;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

.fab-tag {
  position: absolute;
  top: -6px;
  right: -6px;
  background: var(--panel);
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 10px;
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
}

.panel {
  width: min(380px, calc(100vw - 36px));
  height: min(560px, calc(100dvh - 100px));
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  flex: none;
}

.title {
  font-weight: 800;
  font-size: 14px;
}

.ctx {
  color: var(--accent);
}

.x {
  background: none;
  border: 0;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.body.center {
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.turn {
  border-bottom: 1px solid var(--line);
  padding-bottom: 8px;
}

.q {
  margin: 0 0 6px;
  font-size: 13px;
}

.a {
  font-size: 13px;
}

.a .txt {
  margin: 0;
  line-height: 1.55;
}

.typing {
  color: var(--muted);
  font-style: italic;
}

.a.err {
  color: var(--bad);
}

.cites {
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--muted);
}

.cites ul {
  margin: 4px 0 0;
  padding-left: 16px;
}

.samples {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 0 14px 8px;
  flex: none;
}

.sample {
  border: 1px dashed var(--line);
  background: transparent;
  color: var(--muted);
  border-radius: 14px;
  padding: 3px 8px;
  font-size: 11px;
  cursor: pointer;
}

.sample:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.ask {
  border-top: 1px solid var(--line);
  padding: 10px 14px;
  flex: none;
}

.scope {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--muted);
  margin-bottom: 6px;
}

.ask-row {
  display: flex;
  gap: 8px;
}

.ask-row input {
  flex: 1;
  min-width: 0;
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 9px;
  padding: 9px 11px;
  font-size: 14px;
}

.ask-row input:focus {
  outline: none;
  border-color: var(--accent);
}

.btn.primary {
  border-radius: 9px;
  padding: 9px 14px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #04121f;
  font-weight: 700;
  cursor: pointer;
}

.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
