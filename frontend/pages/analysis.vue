<script setup lang="ts">
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import type { AnalyzeOptions, QualitativeOption, SourceOption } from '~/types/stock'

const { data, pending, error, progress, analyze } = useStockAnalysis()

//  Chia sẻ mã đang xem cho trợ lý nổi (ChatWidget) để hỏi đúng ngữ cảnh mã đó.
const activeTicker = useActiveTicker()
watch(() => data.value?.ticker, (code) => { activeTicker.value = code || '' })

const ticker = ref('')
const showAdvanced = ref(false)

// Ba mục định tính do BẠN tự đánh giá (máy không crawl được).
const pos = ref<QualitativeOption>(1)
const mgmt = ref<QualitativeOption>(1)
const cat = ref<QualitativeOption>(1)

// Để trống = dùng giá trị mặc định của máy chủ.
const peSec = ref('')
const pbFair = ref('')
const source = ref<SourceOption>('auto')

const examples = ['FPT', 'VCB', 'HPG', 'MWG', 'VNM']

// Bước hiển thị; `at` chỉ để tô mờ bước đã qua, tiến độ thật lấy từ máy chủ.
const STEPS = [
  { key: 'technical', at: 10, text: 'Lấy giá và chỉ báo kỹ thuật' },
  { key: 'company', at: 45, text: 'Đọc hồ sơ doanh nghiệp' },
  { key: 'fundamentals', at: 55, text: 'Lấy báo cáo tài chính' },
  { key: 'scoring', at: 90, text: 'Chấm điểm 14 tiêu chí' }
] as const

const QUALITATIVE_OPTIONS: Record<'pos' | 'mgmt' | 'cat', { value: QualitativeOption; label: string }[]> = {
  pos: [
    { value: 0, label: '0 — Yếu, dễ bị đối thủ thay thế' },
    { value: 1, label: '1 — Trung bình, không có gì đặc biệt' },
    { value: 2, label: '2 — Mạnh, có lợi thế bền vững' }
  ],
  mgmt: [
    { value: 0, label: '0 — Có nhiều điều đáng nghi ngại' },
    { value: 1, label: '1 — Bình thường, chưa thấy vấn đề' },
    { value: 2, label: '2 — Minh bạch, giữ lời hứa với cổ đông' }
  ],
  cat: [
    { value: 0, label: '0 — Chưa thấy câu chuyện gì mới' },
    { value: 1, label: '1 — Có nhưng còn mơ hồ' },
    { value: 2, label: '2 — Rõ ràng và sắp diễn ra' }
  ]
}

/** Chuỗi rỗng -> null (không gửi tham số). */
function toNumberOrNull(input: string): number | null {
  const s = input.trim().replace(',', '.')
  if (!s) return null
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}

const options = computed<AnalyzeOptions>(() => ({
  pos: pos.value,
  mgmt: mgmt.value,
  cat: cat.value,
  pe_sec: toNumberOrNull(peSec.value),
  pb_fair: toNumberOrNull(pbFair.value),
  source: source.value
}))

const route = useRoute()
const { isLoggedIn, ensureLoaded } = useAuth()
const { items: watchItems, loaded: watchLoaded, load: loadWatchlist } = useWatchlist()

/** Chạy phân tích thật cho một mã (đồng bộ ô nhập để màn loading hiện đúng mã). */
async function runAnalysis(code: string) {
  showAdvanced.value = false
  ticker.value = code
  await analyze(code, options.value)
}

//  Đổi URL cho khớp mã (watcher bên dưới chạy phân tích); cùng mã thì chạy lại thẳng.
function submit() {
  const code = ticker.value.trim().toUpperCase()
  if (!code) return
  if (String(route.query.symbol || '').toUpperCase() === code) {
    void runAnalysis(code)
  } else {
    void navigateTo({ path: '/analysis', query: { symbol: code } })
  }
}

function pick(code: string) {
  ticker.value = code
  submit()
}

//  ?symbol trên URL là nguồn sự thật → mọi cách đổi mã đều phân tích đúng một lần.
watch(() => route.query.symbol, (value) => {
  const code = String(value || '').trim().toUpperCase()
  if (code) void runAnalysis(code)
})

//  Khởi tạo: có ?symbol → phân tích ngay; nếu không, đã đăng nhập thì mở mã theo dõi gần nhất.
onMounted(async () => {
  const code = String(route.query.symbol || '').trim().toUpperCase()
  if (code) {
    void runAnalysis(code)
    return
  }
  await ensureLoaded()
  if (!isLoggedIn.value) return
  if (!watchLoaded.value) await loadWatchlist()
  const recent = watchItems.value[0]
  if (recent) void navigateTo({ path: '/analysis', query: { symbol: recent.ticker } })
})

useHead({
  title: computed(() =>
    data.value?.ticker
      ? `${data.value.ticker} — Phân tích mã cổ phiếu`
      : 'Phân Tích Mã — công cụ phân tích cổ phiếu'
  )
})
</script>

<template>
  <div class="page">
    <AppHeader />
    <div class="app">
    <!-- ---------- Thanh công cụ: tìm kiếm + gợi ý + tùy chọn ---------- -->
    <header class="bar">
      <form class="search" @submit.prevent="submit">
        <input
          v-model="ticker"
          type="text"
          name="ticker"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
          maxlength="12"
          placeholder="Nhập mã (VD: FPT)"
          aria-label="Mã cổ phiếu"
        />
        <button class="btn primary" type="submit" :disabled="pending">
          {{ pending ? 'Đang chạy…' : 'Phân tích →' }}
        </button>
      </form>

      <div class="quick">
        <button
          v-for="code in examples"
          :key="code"
          type="button"
          class="chip"
          :disabled="pending"
          @click="pick(code)"
        >
          {{ code }}
        </button>
      </div>

      <button
        type="button"
        class="chip toggle"
        :aria-expanded="showAdvanced"
        @click="showAdvanced = !showAdvanced"
      >
        <ChevronUp v-if="showAdvanced" /><ChevronDown v-else /> Tùy chọn
      </button>
    </header>

    <!-- ---------- Tùy chọn nâng cao: thả xuống, không đẩy bố cục ---------- -->
    <div v-show="showAdvanced" class="adv card">
      <p class="hint">
        Ba mục đầu là phần <b>bạn tự chấm</b> (máy không đọc được), mặc định mức trung bình.
        Hai ô số để trống nếu chưa rành.
      </p>
      <div class="adv-grid">
        <div class="fg">
          <label for="pos">Vị thế cạnh tranh</label>
          <select id="pos" v-model.number="pos">
            <option v-for="o in QUALITATIVE_OPTIONS.pos" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="fg">
          <label for="mgmt">Ban lãnh đạo</label>
          <select id="mgmt" v-model.number="mgmt">
            <option v-for="o in QUALITATIVE_OPTIONS.mgmt" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="fg">
          <label for="cat">Chất xúc tác</label>
          <select id="cat" v-model.number="cat">
            <option v-for="o in QUALITATIVE_OPTIONS.cat" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="fg">
          <label for="pe_sec">
            P/E ngành
            <span class="gloss" title="P/E (giá trên lợi nhuận mỗi cổ phiếu): trả bao nhiêu đồng cho 1 đồng lợi nhuận/năm.">(?)</span>
          </label>
          <input id="pe_sec" v-model="peSec" type="number" step="0.1" min="0" inputmode="decimal" placeholder="tự động" />
        </div>
        <div class="fg">
          <label for="pb_fair">
            P/B hợp lý
            <span class="gloss" title="P/B (giá trên giá trị sổ sách): trả bao nhiêu đồng cho 1 đồng tài sản ròng.">(?)</span>
          </label>
          <input id="pb_fair" v-model="pbFair" type="number" step="0.1" min="0" inputmode="decimal" placeholder="tự động" />
        </div>
        <div class="fg">
          <label for="source">Nguồn dữ liệu</label>
          <select id="source" v-model="source">
            <option value="auto">Tự động</option>
            <option value="cafef">CafeF (chỉ kỹ thuật)</option>
          </select>
        </div>
      </div>
      <p class="hint">Đổi xong hãy bấm <b>Phân tích</b> để chấm lại.</p>
    </div>

    <!-- ---------- Sân khấu chính ---------- -->
    <main class="stage">
      <p v-if="error" class="msg error" role="alert"><b>Không phân tích được.</b> {{ error }}</p>

      <div v-else-if="pending" class="center loading">
        <p class="loading-head">
          Đang phân tích <b>{{ ticker.toUpperCase() }}</b>
        </p>

        <!-- Tiến độ THẬT: mỗi mốc do máy chủ báo khi bước đó bắt đầu chạy -->
        <div
          class="pbar"
          role="progressbar"
          aria-label="Tiến độ phân tích"
          :aria-valuenow="progress?.percent ?? 0"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <span class="pbar-fill" :style="{ width: `${progress?.percent ?? 0}%` }" />
        </div>

        <p class="loading-step">
          <span class="pct tnum">{{ progress?.percent ?? 0 }}%</span>
          <span>{{ progress?.label ?? 'Kết nối tới máy chủ' }}</span>
        </p>

        <ol class="steps">
          <li
            v-for="s in STEPS"
            :key="s.key"
            :class="{
              done: (progress?.percent ?? 0) > s.at,
              now: progress?.step === s.key
            }"
          >
            {{ s.text }}
          </li>
        </ol>
      </div>

      <div v-else-if="!data" class="center empty">
        <p class="empty-title">Nhập một mã cổ phiếu để bắt đầu</p>
        <p class="hint">
          Máy sẽ tự lấy số liệu công khai, chấm 14 tiêu chí trên thang 100 điểm và gợi ý khung
          thời gian phù hợp — tất cả hiển thị gọn trong một màn hình.
        </p>
      </div>

      <!--
        Thứ tự trong DOM giữ nguyên (tóm tắt → tiêu chí → tầm nhìn) cho desktop;
        màn hẹp sắp xếp lại bằng grid-template-areas để phần hành động lên trước.
      -->
      <!-- Dashboard hiện tại trở thành nội dung tab "Phân tích AI" (tab mặc định);
           truyền qua slot nên markup và CSS của nó giữ nguyên. -->
      <StockTabs v-else :ticker="data.ticker">
        <div class="dash" :class="{ stale: pending }">
          <SummaryPanel :data="data" class="col-a" />
          <CriteriaPanel :categories="data.score.categories" class="col-b" />
          <OutlookPanel
            :horizons="data.score.horizons"
            :best-horizon="data.score.best_horizon"
            :decision="data.score.decision"
            class="col-c"
          />
        </div>
      </StockTabs>
    </main>

    <!-- ---------- Cảnh báo trung thực ---------- -->
    <footer class="foot">
      Số liệu <b>thu thập tự động từ nguồn công khai</b> (CafeF, vnstock…) nên có thể chậm hoặc
      sai lệch — hãy đối chiếu báo cáo tài chính gốc. Đây là <b>công cụ hỗ trợ tư duy</b>,
      <b>không phải khuyến nghị đầu tư</b>.
    </footer>
    </div>
  </div>
</template>

<style scoped>
/* Khung 1 màn hình: AppHeader (global) ở trên, phần phân tích lấp phần còn lại.
   Dùng dvh để thanh công cụ của trình duyệt di động không cắt mất nội dung. */
.page {
  height: 100dvh;
  display: flex;
  flex-direction: column;
}

.app {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px 6px;
  overflow: hidden;
  position: relative;
}

.bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.search {
  display: flex;
  gap: 8px;
  flex: 1;
  max-width: 460px;
}

.search input {
  flex: 1;
  min-width: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 9px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

.search input::placeholder {
  font-weight: 400;
  letter-spacing: 0.2px;
  text-transform: none;
  color: var(--muted);
}

.search .btn {
  padding: 8px 14px;
  font-size: 13px;
  white-space: nowrap;
}

.quick {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.chip {
  font-size: 11.5px;
  font-weight: 700;
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--text);
  border-radius: 20px;
  padding: 4px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.chip:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chip.toggle {
  margin-left: auto;
  font-weight: 600;
  color: var(--muted);
}

/* Thả xuống — nằm đè lên, không làm co dashboard */
.adv {
  position: absolute;
  z-index: 20;
  top: 52px;
  right: 12px;
  left: 12px;
  max-width: 900px;
  margin-left: auto;
  padding: 12px 14px;
  /* Đè lên dashboard → nền đặc thay cho .card (kính) để không xuyên chữ. */
  background: var(--panel-solid);
  border-color: var(--line-hi);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
}

.adv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px 14px;
  margin: 10px 0;
}

/* ----- Sân khấu ----- */
.stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Desktop: 3 cột cạnh nhau, vừa trọn một màn hình.
   Dùng grid-areas để các breakpoint dưới sắp xếp lại thứ tự mà không đụng DOM. */
.dash {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr) minmax(280px, 340px);
  grid-template-areas: 'summary criteria outlook';
  gap: 10px;
  transition: opacity 0.2s ease;
}

.dash > * {
  min-height: 0;
}

.col-a {
  grid-area: summary;
}

.col-b {
  grid-area: criteria;
}

.col-c {
  grid-area: outlook;
}

.stale {
  opacity: 0.5;
}

.center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--muted);
  font-size: 14px;
  text-align: center;
}

.center.empty .hint {
  max-width: 460px;
}

.empty-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}

.loading {
  gap: 14px;
  width: min(420px, 100%);
  margin: 0 auto;
}

.loading-head {
  margin: 0;
  font-size: 15px;
  color: var(--text);
}

.pbar {
  width: 100%;
  height: 8px;
  border-radius: 5px;
  background: var(--line);
  overflow: hidden;
}

.pbar-fill {
  display: block;
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--accent), var(--good));
  transition: width 0.35s ease;
}

.loading-step {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  font-size: 13px;
}

.pct {
  font-size: 17px;
  font-weight: 800;
  color: var(--accent);
  min-width: 46px;
  text-align: right;
}

/* Các bước: mờ khi chưa tới, sáng khi đang chạy, tích khi xong */
.steps {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 100%;
  font-size: 12.5px;
  text-align: left;
}

.steps li {
  padding-left: 22px;
  position: relative;
  opacity: 0.4;
  transition: opacity 0.2s ease;
}

.steps li::before {
  content: '○';
  position: absolute;
  left: 4px;
}

.steps li.done {
  opacity: 0.75;
}

.steps li.done::before {
  content: '✓';
  color: var(--good);
}

.steps li.now {
  opacity: 1;
  color: var(--text);
  font-weight: 600;
}

.steps li.now::before {
  content: '▸';
  color: var(--accent);
}

.foot {
  flex: none;
  font-size: 10.5px;
  line-height: 1.4;
  color: var(--muted);
  text-align: center;
  padding-top: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .pbar-fill {
    transition: none;
  }
}

/* ══════════════ TABLET (768–1179px) ══════════════
   Bỏ ràng buộc một màn hình, cho cuộn dọc bình thường.
   Bố cục 2 cột: tóm tắt + quyết định ở trên (phần cần xem trước),
   bảng 14 tiêu chí trải hết bề ngang bên dưới cho dễ đọc. */
@media (max-width: 1179px) {
  .page {
    height: auto;
    min-height: 100dvh;
  }

  .app {
    flex: none;
    overflow: visible;
    gap: 10px;
  }

  .stage {
    flex: none;
  }

  .dash {
    flex: none;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
      'summary outlook'
      'criteria criteria';
  }

  /* Panel cao tự nhiên theo nội dung, không cuộn riêng bên trong nữa */
  .dash :deep(.panel) {
    overflow: visible;
    min-height: 0;
  }

  .dash :deep(.groups) {
    overflow: visible;
  }

  .bar {
    flex-wrap: wrap;
  }

  /* Tùy chọn nâng cao: thành khối trong luồng, không còn đè lên nội dung */
  .adv {
    position: static;
    max-width: none;
    box-shadow: none;
  }
}

/* Tablet dọc (768–1023px): bảng tiêu chí 1 cột, rộng rãi → nới cột nhãn
   để những tên dài như "Ban lãnh đạo & cổ đông TC" hiện đủ chữ. */
@media (min-width: 768px) and (max-width: 1023px) {
  .dash :deep(.crit) {
    grid-template-columns: minmax(190px, 0.9fr) minmax(0, 1fr) minmax(80px, 1.4fr) 54px;
  }
}

/* Tablet RỘNG (≥1024px): bảng tiêu chí đủ chỗ để chia 2 cột.
   Dưới mức này giữ 1 cột — chia đôi sẽ làm nhãn và giá trị bị cắt chữ. */
@media (min-width: 1024px) and (max-width: 1179px) {
  .dash :deep(.groups) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 2px 24px;
    align-content: start;
  }

  /* Cột hẹp hơn desktop → thu thanh điểm lại để nhãn và giá trị không bị cắt */
  .dash :deep(.crit) {
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr) 46px 44px;
    gap: 8px;
  }
}

/* ══════════════ MOBILE (≤767px) ══════════════
   Một cột. Thứ tự ưu tiên: điểm số → việc cần làm → chi tiết tiêu chí. */
@media (max-width: 767px) {
  .app {
    gap: 12px;
    padding: 10px 12px 8px;
  }

  .dash {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'summary'
      'outlook'
      'criteria';
    gap: 12px;
  }

  /* Thanh trên xếp 3 hàng: tên + tùy chọn · ô tìm kiếm · mã gợi ý */
  .bar {
    gap: 8px;
    padding-bottom: 10px;
  }

  /* 1 1 100%: chiếm trọn hàng NHƯNG vẫn co được, nếu không sẽ tràn ngang ở 320px */
  .search {
    order: 2;
    flex: 1 1 100%;
    min-width: 0;
    max-width: 100%;
  }

  /* 16px để iOS không tự phóng to trang khi bấm vào ô nhập */
  .search input {
    font-size: 16px;
    padding: 11px 14px;
  }

  .search .btn {
    min-height: 44px;
    padding: 10px 16px;
    font-size: 14px;
  }

  /* Mã gợi ý cuộn ngang thay vì xuống dòng thành nhiều hàng */
  .quick {
    order: 3;
    flex: 1 1 100%;
    min-width: 0;
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }

  .quick::-webkit-scrollbar {
    display: none;
  }

  .chip {
    font-size: 13px;
    padding: 8px 14px;
  }

.chip.toggle {
    order: 1;
  }

  /* Chữ trong panel to lên cho dễ đọc trên màn nhỏ */
  .dash :deep(.crit) {
    font-size: 14px;
    gap: 10px;
  }

  .dash :deep(.worst-text),
  .dash :deep(.risk) {
    font-size: 12.5px;
  }

  .dash :deep(.spark) {
    min-height: 150px;
  }

  .foot {
    font-size: 11px;
  }
}

/* Điện thoại (≤480px): mỗi tiêu chí xếp 2 dòng — nhãn + giá trị ở trên,
   thanh điểm + số điểm ở dưới. Gọn hơn và không bao giờ tràn ngang. */
@media (max-width: 480px) {
  .dash :deep(.crit) {
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: 10px;
    row-gap: 4px;
    padding: 7px 0;
  }

  .dash :deep(.crit-track) {
    grid-column: 1;
    align-self: center;
  }
}

</style>
