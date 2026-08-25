<script setup lang="ts">
import { Search, Sparkles, Compass, Bot } from 'lucide-vue-next'

/** Trang chủ: cửa vào tổng quan → tìm mã → đi vào phân tích từng mã. */
const { num } = useFormat()
const {
  group, pending, error, inSession, sessionLabel,
  gainers, losers, mostActive, activeLabel, breadth, load, selectGroup
} = useMarketOverview()
const { listAll } = usePositionBook()
const { isLoggedIn, ensureLoaded } = useAuth()
const { items: watchItems, load: loadWatch } = useWatchlist()

const ticker = ref('')
const positions = ref<{ ticker: string }[]>([])
const examples = ['FPT', 'VCB', 'HPG', 'MWG', 'VNM', 'MBB']
const GROUPS = [
  { key: 'VN30', label: 'VN30' },
  { key: 'VN100', label: 'VN100' },
  { key: 'HOSE', label: 'HOSE' },
  { key: 'HNX30', label: 'HNX30' }
]

function go(code: string): void {
  const c = code.trim().toUpperCase()
  if (c) void navigateTo({ path: '/phan-tich', query: { ma: c } })
}

const breadthTotal = computed(() => breadth.value.up + breadth.value.down + breadth.value.flat)
const upPct = computed(() => breadthTotal.value ? Math.round(breadth.value.up / breadthTotal.value * 100) : 0)

onMounted(async () => {
  positions.value = listAll()
  void load()
  await ensureLoaded()
  if (isLoggedIn.value) void loadWatch()
})

useHead({ title: 'InvestStudio — Đầu tư có cơ sở' })
</script>

<template>
  <div class="home">
    <AppHeader />

    <!-- ticker tape (mã sôi động thật) -->
    <div v-if="mostActive.length" class="tape">
      <div class="tape-track">
        <span v-for="(m, i) in [...mostActive, ...mostActive]" :key="m.symbol + '-' + i">
          <b>{{ m.symbol }}</b>
          <span class="tnum">{{ num(m.price) }}</span>
          <span v-if="m.change != null" class="tnum" :class="m.change >= 0 ? 'lv-good' : 'lv-bad'">
            {{ m.change >= 0 ? '+' : '' }}{{ num(m.change) }}%
          </span>
        </span>
      </div>
    </div>

    <!-- hero -->
    <section class="hero">
      <div class="eyebrow">
        <span class="dot" :class="{ live: inSession }" />
        {{ inSession ? 'Thị trường đang mở cửa' : (sessionLabel || 'Ngoài phiên giao dịch') }}
      </div>
      <h1>Đầu tư có <span class="grad">cơ sở</span>,<br>không đầu tư theo <span class="grad">cảm tính</span>.</h1>
      <p class="lead">
        Nhập một mã cổ phiếu — nhận điểm sức khỏe 0–100 trên 14 tiêu chí, định giá, kỹ thuật
        và khung thời gian phù hợp. Tất cả trong một màn hình.
      </p>
      <form class="hero-search" @submit.prevent="go(ticker)">
        <Search />
        <input v-model="ticker" placeholder="Nhập mã cổ phiếu, VD: FPT"
               autocapitalize="characters" spellcheck="false" maxlength="12" aria-label="Mã cổ phiếu" />
        <button class="btn primary" type="submit">Phân tích →</button>
      </form>
      <div class="chips">
        <button v-for="c in examples" :key="c" type="button" @click="go(c)">{{ c }}</button>
      </div>
    </section>

    <!-- breadth + snapshot -->
    <section class="strip">
      <div class="card breadth">
        <h3 class="sec-title">Độ rộng thị trường · {{ group }}</h3>
        <template v-if="inSession && breadthTotal">
          <div class="bd-bar">
            <span class="bg-good" :style="{ width: upPct + '%' }" />
            <span class="bg-bad" :style="{ width: (100 - upPct) + '%' }" />
          </div>
          <div class="bd-nums">
            <span class="lv-good tnum">▲ {{ breadth.up }} tăng</span>
            <span class="muted tnum">■ {{ breadth.flat }}</span>
            <span class="lv-bad tnum">▼ {{ breadth.down }} giảm</span>
          </div>
        </template>
        <p v-else class="hint">Phiên chưa mở — độ rộng hiển thị khi thị trường giao dịch. Dưới đây là các mã sôi động nhất theo giá trị khớp lệnh.</p>
        <div class="baskets">
          <button v-for="g in GROUPS" :key="g.key" :class="{ on: group === g.key }"
                  :disabled="pending" @click="selectGroup(g.key)">{{ g.label }}</button>
        </div>
      </div>

      <div class="card snap">
        <h3 class="sec-title">Của bạn</h3>
        <div class="snap-grid">
          <NuxtLink to="/theo-doi" class="snap-item">
            <span class="k">Đang theo dõi</span>
            <span class="v tnum">{{ isLoggedIn ? watchItems.length : '—' }}</span>
          </NuxtLink>
          <div class="snap-item">
            <span class="k">Mã có vị thế</span>
            <span class="v tnum">{{ positions.length }}</span>
          </div>
        </div>
        <NuxtLink v-if="positions.length" :to="{ path: '/phan-tich', query: { ma: positions[0].ticker } }" class="btn snap-cta">
          Mở {{ positions[0].ticker }} →
        </NuxtLink>
        <NuxtLink v-else to="/danh-sach" class="btn snap-cta">Khám phá danh sách mã →</NuxtLink>
      </div>
    </section>

    <p v-if="error" class="msg error" role="alert">{{ error }}</p>

    <!-- movers -->
    <section class="cols">
      <template v-if="inSession">
        <div class="card"><h3 class="sec-title">🔥 Tăng mạnh nhất</h3>
          <MoverList :items="gainers" />
        </div>
        <div class="card"><h3 class="sec-title">❄️ Giảm sâu nhất</h3>
          <MoverList :items="losers" />
        </div>
      </template>
      <div class="card" :class="{ wide: !inSession }">
        <h3 class="sec-title">Sôi động nhất · {{ activeLabel }}</h3>
        <MoverList :items="mostActive" show-price />
      </div>
    </section>

    <!-- feature strip -->
    <section class="feat">
      <div class="card"><div class="ic"><Sparkles /></div><h4>Điểm 14 tiêu chí</h4>
        <p>Chấm sức khỏe tài chính, định giá và kỹ thuật trên thang 100 — minh bạch từng tiêu chí.</p></div>
      <div class="card"><div class="ic"><Compass /></div><h4>Khung thời gian</h4>
        <p>Gợi ý ngắn / trung / dài hạn phù hợp với điểm số và bối cảnh từng mã.</p></div>
      <div class="card"><div class="ic"><Bot /></div><h4>Trợ lý AI</h4>
        <p>Hỏi bất cứ điều gì về mã đang xem — trợ lý đọc đúng số liệu của bạn để trả lời.</p></div>
    </section>

    <footer class="disclaimer">
      Số liệu <b>thu thập tự động từ nguồn công khai</b> nên có thể chậm hoặc sai lệch.
      Đây là <b>công cụ hỗ trợ tư duy</b>, <b>không phải khuyến nghị đầu tư</b>.
    </footer>
  </div>
</template>

<style scoped>
.home { min-height: 100dvh; }

/* header */
.top { position: sticky; top: 0; z-index: 30; display: flex; align-items: center; gap: 16px;
  padding: 13px 26px; border-bottom: 1px solid var(--line);
  background: rgba(7, 11, 22, 0.72); backdrop-filter: blur(14px) saturate(1.4); }
.brand { display: flex; align-items: center; gap: 11px; font-weight: 800; font-size: 16px; text-decoration: none; color: var(--text); white-space: nowrap; }
.brand small { color: var(--muted); font-weight: 500; }
.logo { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
  background: conic-gradient(from 210deg, var(--accent), var(--accent2), var(--good), var(--accent));
  box-shadow: 0 0 22px -4px var(--accent); color: #04121f; font-weight: 900; }
.tabs { display: flex; gap: 4px; margin-left: 8px; }
.tabs a { padding: 8px 14px; border-radius: 10px; color: var(--muted); text-decoration: none; font-size: 13.5px; font-weight: 600; transition: 0.18s; }
.tabs a:hover { color: var(--text); background: var(--panel-hi); }
.tabs a.on { color: var(--text); background: var(--panel); border: 1px solid var(--line-hi); }
.head-right { margin-left: auto; }

/* ticker tape */
.tape { overflow: hidden; border-bottom: 1px solid var(--line); background: rgba(10, 17, 34, 0.5); }
.tape-track { display: inline-flex; gap: 30px; padding: 7px 0; white-space: nowrap; animation: tape 40s linear infinite; font-size: 13px; }
.tape-track span { display: inline-flex; gap: 7px; align-items: baseline; }
.tape:hover .tape-track { animation-play-state: paused; }
@keyframes tape { to { transform: translateX(-50%); } }

/* hero */
.hero { max-width: 1320px; margin: 0 auto; padding: 60px 26px 26px; text-align: center; }
.eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--muted);
  border: 1px solid var(--line); background: var(--panel); border-radius: 20px; padding: 6px 14px; margin-bottom: 20px; }
.eyebrow .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted-2); }
.eyebrow .dot.live { background: var(--good); box-shadow: 0 0 10px var(--good); animation: pulse 2s infinite; }
@keyframes pulse { 50% { opacity: 0.4; } }
.hero h1 { font-size: clamp(32px, 5vw, 60px); line-height: 1.05; margin: 0 0 16px; font-weight: 800; letter-spacing: -1.2px; }
.grad { background: linear-gradient(100deg, var(--accent), var(--accent2) 45%, var(--good));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.lead { max-width: 600px; margin: 0 auto 28px; color: var(--muted); font-size: 16.5px; line-height: 1.6; }
.hero-search { max-width: 560px; margin: 0 auto; display: flex; align-items: center; gap: 10px;
  background: var(--panel); border: 1px solid var(--line-hi); border-radius: 16px; padding: 8px 8px 8px 16px;
  box-shadow: var(--shadow); color: var(--muted); }
.hero-search input { flex: 1; background: none; border: none; outline: none; color: var(--text);
  font-size: 17px; font-weight: 600; letter-spacing: 0.6px; text-transform: uppercase; font-family: var(--mono); min-width: 0; }
.hero-search input::placeholder { color: var(--muted-2); text-transform: none; font-family: var(--sans); font-weight: 400; }
.chips { display: flex; gap: 8px; justify-content: center; margin-top: 16px; flex-wrap: wrap; }
.chips button { font-size: 12.5px; color: var(--muted); border: 1px solid var(--line); background: var(--panel-hi);
  border-radius: 20px; padding: 5px 13px; cursor: pointer; font-family: var(--mono); transition: 0.15s; }
.chips button:hover { color: var(--text); border-color: var(--accent); }

/* strip: breadth + snapshot */
.strip, .cols, .feat { max-width: 1320px; margin: 18px auto 0; padding: 0 26px; display: grid; gap: 16px; }
.strip { grid-template-columns: 2fr 1fr; }
.cols { grid-template-columns: 1fr 1fr 1fr; }
.feat { grid-template-columns: repeat(3, 1fr); margin-top: 22px; }
.card { margin: 0; }
.bd-bar { display: flex; height: 10px; border-radius: 6px; overflow: hidden; gap: 2px; margin-bottom: 8px; }
.bd-bar span { display: block; }
.bd-nums { display: flex; gap: 16px; font-size: 13px; }
.baskets { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 12px; }
.baskets button { border: 1px solid var(--line); background: var(--panel-hi); color: var(--muted);
  border-radius: 20px; padding: 6px 13px; font-size: 12.5px; font-weight: 600; cursor: pointer; transition: 0.15s; }
.baskets button:hover:not(:disabled) { color: var(--text); border-color: var(--line-hi); }
.baskets button.on { color: #04121f; background: linear-gradient(135deg, var(--accent), var(--accent2)); border: none; }
.snap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.snap-item { background: var(--panel-hi); border: 1px solid var(--line); border-radius: 12px; padding: 11px; text-decoration: none; color: var(--text); display: block; }
.snap-item .k { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); display: block; }
.snap-item .v { font-size: 22px; font-weight: 700; margin-top: 2px; display: block; }
.snap-cta { display: block; text-align: center; margin-top: 12px; text-decoration: none; }
.cols .wide { grid-column: 1 / -1; }

/* feature */
.feat .ic { width: 40px; height: 40px; border-radius: 11px; display: grid; place-items: center;
  background: var(--panel-hi); border: 1px solid var(--line); margin-bottom: 12px; color: var(--accent); }
.feat h4 { margin: 0 0 6px; font-size: 16px; }
.feat p { margin: 0; color: var(--muted); font-size: 13.5px; line-height: 1.55; }

.disclaimer { max-width: 1320px; margin: 30px auto 0; padding: 16px 26px 40px; }

@media (max-width: 1000px) {
  .strip, .cols, .feat { grid-template-columns: 1fr; }
  .tabs { display: none; }
}
</style>
