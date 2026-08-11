<script setup lang="ts">
import { List, MessageCircle, Search, Star, Target, TrendingUp } from 'lucide-vue-next'

/** Trang danh sách mã theo dõi. Cần đăng nhập; chưa đăng nhập thì chuyển hướng. */
const { user, isLoggedIn, ensureLoaded } = useAuth()
const { items, pending, error, load, add, remove } = useWatchlist()

const newTicker = ref('')
const adding = ref(false)

useHead({ title: 'Mã theo dõi — InvestStudio' })

onMounted(async () => {
  await ensureLoaded()
  if (!isLoggedIn.value) {
    void navigateTo({ path: '/dang-nhap', query: { next: '/theo-doi' } })
    return
  }
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

    <p v-if="user" class="note">Xin chào <b>{{ user.display_name }}</b>. Ghim mã để mở lại thật nhanh.</p>

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
          <button type="button" class="btn danger" title="Bỏ theo dõi" @click="remove(item.id)">Bỏ</button>
        </div>
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
