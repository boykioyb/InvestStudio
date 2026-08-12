<script setup lang="ts">
import { List, MessageCircle, Search, Star, Target, TrendingUp } from 'lucide-vue-next'
import type { WatchlistItem } from '~/types/account'

/** Trang danh sách mã theo dõi. Cần đăng nhập (middleware chặn nếu chưa). */
definePageMeta({ middleware: 'auth' })

const { user, ensureLoaded, changePassword } = useAuth()
const { items, pending, error, load, add, update, remove } = useWatchlist()

const newTicker = ref('')
const adding = ref(false)

//  Sửa ghi chú / ngưỡng của một mục theo dõi (mục 6).
const editingId = ref<number | null>(null)
const editForm = reactive({ note: '', target_price: '', target_score: '' })

function numOrNull(input: string): number | null {
  const text = String(input).trim()
  if (!text) return null
  const n = Number(text)
  return Number.isFinite(n) ? n : null
}

function startEdit(item: WatchlistItem): void {
  editingId.value = item.id
  editForm.note = item.note || ''
  editForm.target_price = item.target_price != null ? String(item.target_price) : ''
  editForm.target_score = item.target_score != null ? String(item.target_score) : ''
}

async function saveEdit(id: number): Promise<void> {
  const ok = await update(id, {
    note: editForm.note.trim(),
    target_price: numOrNull(editForm.target_price),
    target_score: numOrNull(editForm.target_score)
  })
  if (ok) editingId.value = null
}

//  Đổi mật khẩu (mục 3).
const showPw = ref(false)
const pwOld = ref('')
const pwNew = ref('')
const pwMsg = ref('')

async function submitPw(): Promise<void> {
  pwMsg.value = ''
  if (pwNew.value.length < 6) { pwMsg.value = '⚠️ Mật khẩu mới cần tối thiểu 6 ký tự.'; return }
  const ok = await changePassword(pwOld.value, pwNew.value)
  if (ok) { pwMsg.value = '✅ Đã đổi mật khẩu.'; pwOld.value = ''; pwNew.value = ''; showPw.value = false }
  else pwMsg.value = '⚠️ Đổi không thành công — mật khẩu hiện tại có đúng không?'
}

useHead({ title: 'Mã theo dõi — InvestStudio' })

onMounted(async () => {
  await ensureLoaded()  // middleware đã đảm bảo đăng nhập
  await load()
})

async function quickAdd(): Promise<void> {
  const code = newTicker.value.trim().toUpperCase()
  if (!code) return
  adding.value = true
  try {
    if (await add({ ticker: code })) newTicker.value = ''
  } finally {
    adding.value = false
  }
}

/** Mở màn hình phân tích của mã (giống bấm dòng ở trang Danh sách). */
function analyze(ticker: string): void {
  void navigateTo({ path: '/', query: { ma: ticker } })
}

function fmtPrice(value: number | null): string {
  return value === null ? '—' : `${value} nghìn đ`
}
</script>

<template>
  <div class="wrap">
    <header class="head">
      <h1><Star /> Mã đang theo dõi</h1>
      <div class="row nav">
        <NuxtLink to="/" class="btn"><Search /> Phân tích</NuxtLink>
        <NuxtLink to="/danh-sach" class="btn"><List /> Danh sách</NuxtLink>
        <NuxtLink to="/tro-ly" class="btn"><MessageCircle /> Trợ lý</NuxtLink>
      </div>
    </header>

    <div class="acctline">
      <p v-if="user" class="note">Xin chào <b>{{ user.display_name }}</b>. Ghim mã để mở lại thật nhanh.</p>
      <button type="button" class="btn small" @click="showPw = !showPw">Đổi mật khẩu</button>
    </div>
    <form v-if="showPw" class="pwform card" @submit.prevent="submitPw">
      <input v-model="pwOld" type="password" placeholder="Mật khẩu hiện tại"
             autocomplete="current-password" required />
      <input v-model="pwNew" type="password" placeholder="Mật khẩu mới (≥ 6 ký tự)"
             autocomplete="new-password" required minlength="6" />
      <button class="btn primary" type="submit">Lưu</button>
    </form>
    <p v-if="pwMsg" class="note pwmsg">{{ pwMsg }}</p>

    <div class="card">
      <p class="sec-title">Thêm nhanh một mã</p>
      <form class="searchbar" @submit.prevent="quickAdd">
        <input v-model="newTicker" type="text" maxlength="12" placeholder="Nhập mã (VD: FPT)"
               aria-label="Mã cần theo dõi" autocapitalize="characters" spellcheck="false" />
        <button class="btn primary" type="submit" :disabled="adding">
          {{ adding ? 'Đang thêm…' : 'Thêm' }}
        </button>
      </form>
      <p v-if="error" class="msg error" role="alert">{{ error }}</p>
    </div>

    <p v-if="pending" class="note">Đang tải danh sách…</p>

    <p v-else-if="!items.length" class="msg">
      Chưa có mã nào. Thêm ở trên, hoặc bấm <Star /> ngay trong màn hình phân tích của một mã.
    </p>

    <div v-else class="list">
      <article v-for="item in items" :key="item.id" class="card item">
        <div class="left">
          <button type="button" class="ticker" @click="analyze(item.ticker)">{{ item.ticker }}</button>
          <p v-if="item.note" class="note">{{ item.note }}</p>
          <p class="targets">
            <span v-if="item.target_price !== null"><Target /> Giá mục tiêu: <b>{{ fmtPrice(item.target_price) }}</b></span>
            <span v-if="item.target_score !== null"><TrendingUp /> Điểm mục tiêu: <b>{{ item.target_score }}/100</b></span>
          </p>
        </div>
        <div class="right row">
          <button type="button" class="btn" @click="analyze(item.ticker)">Phân tích →</button>
          <button type="button" class="btn" @click="startEdit(item)">Sửa</button>
          <button type="button" class="btn danger" title="Bỏ theo dõi" @click="remove(item.id)">Bỏ</button>
        </div>

        <form v-if="editingId === item.id" class="edit" @submit.prevent="saveEdit(item.id)">
          <input v-model="editForm.note" type="text" maxlength="500" placeholder="Ghi chú" />
          <input v-model="editForm.target_price" type="number" step="0.01" min="0"
                 placeholder="Giá mục tiêu (nghìn đ)" />
          <input v-model="editForm.target_score" type="number" min="0" max="100"
                 placeholder="Điểm mục tiêu (/100)" />
          <button class="btn primary" type="submit">Lưu</button>
          <button class="btn" type="button" @click="editingId = null">Hủy</button>
        </form>
      </article>
    </div>

    <p class="disclaimer">
      Danh sách theo dõi chỉ để mở nhanh. Đây là công cụ hỗ trợ tư duy,
      <b>không phải khuyến nghị đầu tư</b>.
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

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 0;
  flex-wrap: wrap;
}

.acctline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.btn.small {
  padding: 6px 12px;
  font-size: 12px;
}

.pwform,
.edit {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.edit {
  flex-basis: 100%;
  margin-top: 10px;
  border-top: 1px dashed var(--line);
  padding-top: 10px;
}

.pwform input,
.edit input {
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  flex: 1;
  min-width: 140px;
}

.pwmsg {
  margin: 2px 0 0;
}

.left {
  min-width: 0;
}

.ticker {
  background: none;
  border: 0;
  padding: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--accent);
  cursor: pointer;
}

.targets {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 12.5px;
  color: var(--muted);
  margin: 4px 0 0;
}

.right {
  flex: none;
}

.btn.danger:hover:not(:disabled) {
  border-color: var(--bad);
  color: var(--bad);
}

@media (max-width: 560px) {
  .item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
