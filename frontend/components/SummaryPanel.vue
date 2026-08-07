<script setup lang="ts">
import type { RangeKey, StockAnalysis } from '~/types/stock'

/** Cột tóm tắt: mã, điểm tổng, kết luận, giá và biểu đồ giá thật nhiều khung. */
const props = defineProps<{ data: StockAnalysis }>()

const { textClass, fillClass } = useLevel()
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
</script>

<template>
  <section class="card panel">
    <header class="head">
      <div class="id">
        <h2 class="ticker" :class="textClass(data.score.verdict.level)">{{ data.ticker }}</h2>
        <p class="name" :title="data.name">{{ data.name }}</p>
      </div>
      <div class="px">
        <span class="px-val tnum">{{ price(data.price) }}</span>
        <span class="px-unit">nghìn đ/cp</span>
      </div>
    </header>

    <div class="score">
      <div class="score-num tnum" :class="textClass(data.score.verdict.level)">
        {{ data.score.total }}<span class="score-max">/100</span>
      </div>
      <div class="score-side">
        <p class="verdict" :class="textClass(data.score.verdict.level)">
          {{ data.score.verdict.text }}
        </p>
        <span class="track" aria-hidden="true">
          <span
            class="fill"
            :class="fillClass(data.score.verdict.level)"
            :style="{ width: `${Math.min(100, Math.max(0, data.score.total))}%` }"
          />
        </span>
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

.score {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.score-num {
  font-size: 42px;
  font-weight: 900;
  line-height: 1;
}

.score-max {
  font-size: 15px;
  color: var(--muted);
}

.score-side {
  flex: 1;
  min-width: 0;
}

.verdict {
  margin: 0 0 6px;
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1.35;
}

.track {
  display: block;
  height: 6px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}

.fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
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
