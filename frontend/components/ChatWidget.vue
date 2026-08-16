<script setup lang="ts">
/**
 * Trợ lý RAG dạng POPUP nổi ở góc phải dưới, dùng được ở mọi trang.
 *
 * Khi đang mở một mã (trang phân tích), tự lấy mã đó làm ngữ cảnh — hỏi là hỏi
 * ngay trên mã đang xem. Chỉ hiển thị và gọi composable; không chứa logic.
 */
import { List, LogIn, MessageCircle, Plus, Send, Trash2, X } from 'lucide-vue-next'
import type { ConversationOut } from '~/types/account'

const route = useRoute()
const {
  turns, pending, askStream,
  conversations, activeConvId, loadConversations, openConversation, newConversation, deleteConversation
} = useChat()
const { isLoggedIn, ensureLoaded } = useAuth()
const activeTicker = useActiveTicker()

const open = ref(false)
const question = ref('')
const scoped = ref(true)      // mặc định: giới hạn trong mã đang xem
const showList = ref(false)   // bật panel danh sách câu chuyện

//  Chỉ coi là "đang xem mã" khi ở trang phân tích và đã có mã.
const ticker = computed(() => (route.path === '/' ? activeTicker.value : ''))

//  Nạp danh sách câu chuyện; có thì mở cuộc gần nhất, chưa có thì để cuộc mới trống.
async function syncConversations(): Promise<void> {
  if (!isLoggedIn.value) {
    conversations.value = []
    newConversation()
    return
  }
  await loadConversations()
  if (conversations.value.length) await openConversation(conversations.value[0].id)
  else newConversation()
}

onMounted(async () => {
  await ensureLoaded()
  await syncConversations()
})

//  Ẩn widget ở những nơi thừa: trang trợ lý toàn màn hình và trang đăng nhập/ký.
const hidden = computed(() => ['/tro-ly', '/dang-nhap', '/dang-ky'].includes(route.path))

watch(isLoggedIn, syncConversations)
//  Mở widget → làm mới danh sách (không đụng cuộc đang xem).
watch(open, (v) => { if (v && isLoggedIn.value) void loadConversations() })

const examples = computed(() =>
  ticker.value
    ? [`Điểm mạnh yếu của ${ticker.value}?`, `${ticker.value} có tin gì mới?`]
    : ['Mã nào vốn hóa lớn nhất VN30?', 'So sánh P/E của VCB và CTG']
)

function submit(): void {
  const q = question.value
  question.value = ''
  //  Đang mở cuộc → nối tiếp; chưa có → tạo cuộc mới. Có mã + giới hạn → hỏi trong mã đó.
  askStream(q, ticker.value && scoped.value ? ticker.value : '',
    activeConvId.value ? { conversationId: activeConvId.value } : { startConversation: true })
}

async function openFromList(id: number): Promise<void> {
  await openConversation(id)
  showList.value = false
}

function newChat(): void {
  newConversation()
  showList.value = false
}

function onDelete(c: ConversationOut): void {
  if (window.confirm(`Xoá câu chuyện "${c.title}"?`)) void deleteConversation(c.id)
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
          <button v-if="isLoggedIn" type="button" class="hbtn" title="Câu chuyện"
                  @click="showList = !showList"><List :size="18" /></button>
          <MessageCircle /> Trợ lý
          <span v-if="ticker" class="ctx">· {{ ticker }}</span>
        </div>
        <div class="head-actions">
          <button v-if="isLoggedIn" type="button" class="hbtn" title="Cuộc mới"
                  @click="newChat"><Plus :size="18" /></button>
          <button type="button" class="x" aria-label="Đóng" @click="open = false"><X /></button>
        </div>
      </header>

      <!-- Panel danh sách câu chuyện (trượt đè lên khung chat) -->
      <div v-if="isLoggedIn && showList" class="conv-panel">
        <button type="button" class="btn primary conv-new" @click="newChat">
          <Plus :size="16" /> Cuộc mới
        </button>
        <ul class="conv-list">
          <li v-for="c in conversations" :key="c.id"
              :class="['conv', { active: c.id === activeConvId }]" @click="openFromList(c.id)">
            <span class="conv-title">{{ c.title }}</span>
            <button type="button" class="conv-del" title="Xoá" @click.stop="onDelete(c)">
              <Trash2 :size="14" />
            </button>
          </li>
          <li v-if="!conversations.length" class="empty">Chưa có câu chuyện nào.</li>
        </ul>
      </div>

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
            <div class="msg user">
              <div class="bubble">{{ turn.question }}</div>
            </div>

            <ul v-if="turn.steps && turn.steps.length" class="steps">
              <li v-for="(s, k) in turn.steps" :key="k">🔧 {{ s.label }}</li>
            </ul>

            <div class="msg bot">
              <div v-if="turn.error" class="bubble err">{{ turn.error }}</div>
              <div v-else-if="turn.response" class="bubble">
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
              <div v-else class="bubble typing">Đang trả lời…</div>
            </div>
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
  position: relative;
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
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 800;
  font-size: 14px;
}

.ctx {
  color: var(--accent);
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hbtn {
  background: none;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  display: inline-flex;
  padding: 3px;
  border-radius: 6px;
}

.hbtn:hover {
  color: var(--text);
  background: var(--panel2);
}

.x {
  background: none;
  border: 0;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}

/*  Panel danh sách câu chuyện — đè lên khung chat, ngay dưới header. */
.conv-panel {
  position: absolute;
  top: 46px;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  background: var(--panel);
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
}

.conv-new {
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
  border-radius: 8px;
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

.conv-del {
  background: none;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  padding: 2px;
  display: inline-flex;
  opacity: 0;
}

.conv:hover .conv-del,
.conv.active .conv-del {
  opacity: 1;
}

.conv-del:hover {
  color: var(--bad);
}

.empty {
  color: var(--muted);
  font-size: 12.5px;
  padding: 8px 10px;
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
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/*  Hàng tin nhắn: câu hỏi dồn phải, câu trả lời dồn trái. */
.msg {
  display: flex;
}

.msg.user {
  justify-content: flex-end;
}

.msg.bot {
  justify-content: flex-start;
}

/*  Bong bóng chung. */
.bubble {
  max-width: 85%;
  padding: 8px 11px;
  font-size: 13px;
  line-height: 1.55;
  border-radius: 14px;
  overflow-wrap: anywhere;
}

/*  Câu hỏi: nền xanh nhạt (accent), góc dưới-phải vát. */
.msg.user .bubble {
  background: color-mix(in srgb, var(--accent) 26%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
  color: var(--text);
  border-bottom-right-radius: 4px;
}

/*  Câu trả lời: nền panel trung tính, góc dưới-trái vát. */
.msg.bot .bubble {
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-bottom-left-radius: 4px;
}

/*  Gọn lề đoạn đầu/cuối của markdown trong bong bóng. */
.msg.bot .bubble :deep(p:first-child) {
  margin-top: 0;
}

.msg.bot .bubble :deep(p:last-child) {
  margin-bottom: 0;
}

/*  Các bước công cụ agent đã/đang chạy — nhỏ, mờ, không lấn câu trả lời. */
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

.txt {
  margin: 0;
}

.typing {
  color: var(--muted);
  font-style: italic;
}

.bubble.err {
  color: var(--bad);
  border-color: color-mix(in srgb, var(--bad) 45%, transparent);
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
