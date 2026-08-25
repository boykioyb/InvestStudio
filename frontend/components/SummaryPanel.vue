<script setup lang="ts">
import type { RangeKey, StockAnalysis } from '~/types/stock'

/** Cột tóm tắt: mã, điểm tổng, kết luận, giá và biểu đồ giá thật nhiều khung. */
const props = defineProps<{ data: StockAnalysis }>()

const { textClass } = useLevel()
const { price, date } = useFormat()
const { history, range, pending: loadingChart, error: chartError, load } = usePriceHistory()

// Đổi mã → tải lại khung đang chọn.
watch(() => props.data.ticker, (t) => t && load(t, range.value), { immediate: true })

/** Giá đóng cửa của khung đang xem; chưa tải xong thì dùng tạm 30 phiên có sẵn. */
const series = computed(() =>
  history.value ? history.value.points.map((p) => p.c) : props.data.prices
)

/** Đổi khung: chỉ gọi lại API, không tự tính gì thêm. */
function pickRange(next: RangeKey) {
  if (next !== range.value || !history.value) load(props.data.ticker, next)
}

/* ── Vòng điểm số (chỉ trình bày) ──────────────────────────────────────── */
const GAUGE_R = 52
const GAUGE_C = 2 * Math.PI * GAUGE_R
const clamped = computed(() => Math.min(100, Math.max(0, props.data.score.total)))
const shown = ref(0)
const dashoffset = computed(() => GAUGE_C * (1 - shown.value / 100))
const gaugeColor = computed(() => {
  const lv = props.data.score.verdict.level
  return lv === 'good' ? 'var(--good)' : lv === 'bad' ? 'var(--bad)'
    : lv === 'warn' ? 'var(--warn)' : 'var(--muted)'
})

let raf = 0
function animateTo(target: number): void {
  cancelAnimationFrame(raf)
  const reduce = import.meta.client && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduce || !import.meta.client) { shown.value = target; return }
  const t0 = performance.now()
  const dur = 1200
  const step = (t: number): void => {
    const p = Math.min(1, (t - t0) / dur)
    shown.value = target * (1 - Math.pow(1 - p, 3))
    if (p < 1) raf = requestAnimationFrame(step)
    else shown.value = target
  }
  raf = requestAnimationFrame(step)
}

onMounted(() => animateTo(clamped.value))
//  Đổi mã → điểm mới thì chạy lại hiệu ứng đếm.
watch(clamped, (v) => animateTo(v))
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <section class="card panel">
    <header class="head">
      <div class="id">
        <h2 class="ticker" :class="textClass(data.score.verdict.level)">{{ data.ticker }}</h2>
        <p class="name" :title="data.name">{{ data.name }}</p>
        <FavoriteButton :ticker="data.ticker" class="follow" />
      </div>
      <div class="px">
        <span class="px-val tnum">{{ price(data.price) }}</span>
        <span class="px-unit">nghìn đ/cp</span>
      </div>
    </header>

    <div class="gauge-block">
      <div class="gauge" :style="{ '--gc': gaugeColor }" role="img"
           :aria-label="`Điểm ${data.score.total} trên 100`">
        <svg viewBox="0 0 120 120">
          <circle class="g-track" cx="60" cy="60" r="52" />
          <circle
            class="g-prog" cx="60" cy="60" r="52" transform="rotate(-90 60 60)"
            :stroke-dasharray="GAUGE_C" :stroke-dashoffset="dashoffset"
          />
        </svg>
        <div class="g-center">
          <span class="g-num tnum" :class="textClass(data.score.verdict.level)">{{ Math.round(shown) }}</span>
          <span class="g-max">/100</span>
        </div>
      </div>
      <div class="score-side">
        <p class="verdict" :class="textClass(data.score.verdict.level)">
          {{ data.score.verdict.text }}
        </p>
        <p class="score-cap hint">điểm sức khỏe tổng hợp · 14 tiêu chí</p>
      </div>
    </div>

    <!-- Chọn khung thời gian: nhìn xu hướng dài để đối chiếu với điểm kỹ thuật -->
    <div class="ranges" role="group" aria-label="Khung thời gian biểu đồ">
      <button
        v-for="r in PRICE_RANGES"
        :key="r.key"
        type="button"
        class="range"
        :class="{ on: range === r.key }"
        :title="r.title"
        :aria-pressed="range === r.key"
        :disabled="loadingChart"
        @click="pickRange(r.key)"
      >
        {{ r.short }}
      </button>
      <span v-if="loadingChart" class="range-load">…</span>
    </div>

    <PriceSparkline :prices="series" class="spark" />

    <p v-if="chartError" class="hint chart-err">{{ chartError }}</p>
    <div v-else-if="history" class="range-stats">
      <span>
        {{ history.label }}:
        <b :class="history.stats.change_pct >= 0 ? 'lv-good' : 'lv-bad'">
          {{ history.stats.change_pct > 0 ? '+' : '' }}{{ history.stats.change_pct }}%
        </b>
      </span>
      <span class="hint">{{ history.stats.sessions }} phiên</span>
    </div>

    <footer class="meta">
      <div class="meta-row">
        <span class="hint">Dữ liệu đến</span>
        <span class="meta-val">{{ date(data.asof) }}</span>
      </div>
      <div class="meta-row srcs">
        <span class="hint">Nguồn</span>
        <span class="badges">
          <span v-for="s in data.sources" :key="s" class="badge">{{ s }}</span>
          <span v-if="!data.sources?.length" class="hint">—</span>
        </span>
      </div>
      <p v-if="data.hint" class="msg warn tiny">{{ data.hint }}</p>
    </footer>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  padding: 12px 14px;
  overflow: auto;
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.follow {
  margin-top: 8px;
}

.ticker {
  margin: 0;
  font-size: 30px;
  font-weight: 900;
  letter-spacing: 1px;
  line-height: 1;
}

.name {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: var(--muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.px {
  text-align: right;
  white-space: nowrap;
}

.px-val {
  display: block;
  font-size: 20px;
  font-weight: 800;
}

.px-unit {
  font-size: 10.5px;
  color: var(--muted);
}

.gauge-block {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.gauge {
  position: relative;
  width: 116px;
  height: 116px;
  flex: none;
}

.gauge svg {
  width: 100%;
  height: 100%;
  display: block;
}

.g-track {
  fill: none;
  stroke: var(--panel-hi);
  stroke-width: 11;
}

.g-prog {
  fill: none;
  stroke: var(--gc);
  stroke-width: 11;
  stroke-linecap: round;
  filter: drop-shadow(0 0 6px var(--gc));
}

.g-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.g-num {
  font-size: 36px;
  font-weight: 900;
  line-height: 1;
}

.g-max {
  font-size: 11px;
  color: var(--muted);
  margin-top: 1px;
}

.score-side {
  flex: 1;
  min-width: 0;
}

.verdict {
  margin: 0 0 4px;
  font-size: 13.5px;
  font-weight: 800;
  line-height: 1.35;
}

.score-cap {
  margin: 0;
}

/* Biểu đồ giãn lấp hết khoảng trống giữa điểm số và phần chú thích */
.spark {
  flex: 1;
  min-height: 110px;
  display: flex;
  flex-direction: column;
}

.spark :deep(.spark-wrap) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.spark :deep(svg.spark) {
  flex: 1;
  height: auto;
  min-height: 0;
}

.ranges {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: none;
}

.range {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--muted);
  border-radius: 7px;
  padding: 4px 0;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
}

/* Loại trừ .on: quy tắc :hover có độ ưu tiên cao hơn .on, nếu không loại trừ
   thì rê chuột vào nút đang chọn sẽ thành chữ xanh trên nền xanh — mất chữ. */
.range:hover:not(:disabled):not(.on) {
  border-color: var(--accent);
  color: var(--accent);
}

.range.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #04121f;
}

.range:disabled {
  opacity: 0.6;
  cursor: progress;
}

.range-load {
  font-size: 12px;
  color: var(--muted);
}

.range-stats {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 11.5px;
  flex: none;
}

.chart-err {
  flex: none;
  margin: 0;
}

.meta {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 11px;
}

.meta-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.meta-row.srcs {
  align-items: flex-start;
}

.meta-val {
  font-weight: 600;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tiny {
  font-size: 11px;
  padding: 6px 9px;
  margin: 2px 0 0;
}
</style>
