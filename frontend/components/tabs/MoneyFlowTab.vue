<script setup lang="ts">
import type { RangeKey } from '~/types/stock'

/** Tab Dòng tiền: chỉ báo MFI/OBV theo NGÀY + khối ngoại phiên hiện tại. */
const props = defineProps<{ ticker: string }>()

const { flow, isLoading, errorOf, loadFlow } = useStockDetails()
const { textClass, fillClass } = useLevel()

const range = ref<RangeKey>('3m')
const key = computed(() => `${props.ticker.toUpperCase()}:flow:${range.value}`)

watch([() => props.ticker, range], ([t, r]) => t && loadFlow(t, r), { immediate: true })

const num = (v: number | null, digits = 2) =>
  v === null || v === undefined ? '—' : v.toLocaleString('vi-VN', { maximumFractionDigits: digits })

/** Bảng ngày: mới nhất lên đầu cho dễ theo dõi. */
const daysNewestFirst = computed(() => [...(flow.value?.points || [])].reverse())

const changeClass = (v: number | null) =>
  v === null || v === undefined ? '' : v > 0 ? 'lv-good' : v < 0 ? 'lv-bad' : ''

/** Tô màu ô MFI theo đúng hai mốc kinh điển 80/20 đã vẽ trên biểu đồ. */
function mfiCellClass(v: number | null): string {
  if (v === null || v === undefined) return ''
  if (v >= 80 || v < 20) return 'lv-bad'
  if (v >= 60) return 'lv-good'
  return ''
}

/** Đường MFI: chuẩn hóa trực tiếp theo thang 0–100 nên đọc được tuyệt đối. */
const mfiPath = computed(() => {
  const pts = (flow.value?.points || []).filter((p) => p.mfi !== null)
  if (pts.length < 2) return ''
  const w = 100
  const h = 100
  return pts
    .map((p, i) => {
      const x = (i / (pts.length - 1)) * w
      const y = h - (p.mfi as number)
      return `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})
</script>

<template>
  <div class="tab-body">
    <div class="switcher" role="group" aria-label="Khung thời gian">
      <button
        v-for="r in PRICE_RANGES"
        :key="r.key"
        type="button"
        class="sw"
        :class="{ on: range === r.key }"
        :aria-pressed="range === r.key"
        :title="r.title"
        @click="range = r.key"
      >
        {{ r.title }}
      </button>
    </div>

    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tính dòng tiền…</p>

    <template v-else-if="flow">
      <section class="card">
        <h3 class="sec-title">MFI — chỉ số dòng tiền ({{ flow.label }})</h3>
        <div class="mfi-head">
          <span class="mfi-val" :class="textClass(flow.mfi_level)">{{ num(flow.mfi_latest, 1) }}</span>
          <span class="mfi-state" :class="textClass(flow.mfi_level)">{{ flow.mfi_state }}</span>
        </div>

        <svg v-if="mfiPath" class="chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img"
             :aria-label="`Đường MFI ${flow.label}`">
          <!-- Hai mốc kinh điển: 80 quá mua, 20 quá bán -->
          <line x1="0" y1="20" x2="100" y2="20" class="grid over" />
          <line x1="0" y1="50" x2="100" y2="50" class="grid" />
          <line x1="0" y1="80" x2="100" y2="80" class="grid under" />
          <path :d="mfiPath" class="line" />
        </svg>
        <!-- Chú thích cho các đường NGANG trong biểu đồ. Cố ý dùng gạch màu thay vì
             ba con số xếp ngang — xếp ngang dễ bị đọc nhầm thành trục thời gian. -->
        <div class="legend">
          <span class="lg"><i class="dash over" aria-hidden="true" />Trên 80 — quá mua</span>
          <span class="lg"><i class="dash mid" aria-hidden="true" />50 — cân bằng</span>
          <span class="lg"><i class="dash under" aria-hidden="true" />Dưới 20 — quá bán</span>
        </div>

        <p class="hint note">
          MFI (Money Flow Index — chỉ số dòng tiền): giống RSI nhưng có nhân khối lượng,
          nên phản ánh tiền vào/ra chứ không chỉ biến động giá.
        </p>
      </section>

      <section class="card">
        <h3 class="sec-title">Tiền vào hay ra trong {{ flow.label.toLowerCase() }}?</h3>
        <div class="tiles">
          <div class="tile">
            <span class="k">OBV thay đổi</span>
            <span class="v" :class="flow.obv_change_pct !== null && flow.obv_change_pct >= 0 ? 'lv-good' : 'lv-bad'">
              {{ flow.obv_change_pct !== null && flow.obv_change_pct > 0 ? '+' : '' }}{{ num(flow.obv_change_pct, 1) }}%
            </span>
            <span class="hint">khối lượng tích lũy</span>
          </div>
          <div class="tile">
            <span class="k">Phiên tăng / giảm</span>
            <span class="v">{{ flow.up_sessions }} / {{ flow.down_sessions }}</span>
          </div>
          <div class="tile">
            <span class="k">KL phiên tăng</span>
            <span class="v lv-good">{{ num(flow.up_volume) }}</span>
            <span class="hint">triệu cp</span>
          </div>
          <div class="tile">
            <span class="k">KL phiên giảm</span>
            <span class="v lv-bad">{{ num(flow.down_volume) }}</span>
            <span class="hint">triệu cp</span>
          </div>
        </div>

        <div class="bar-wrap" v-if="flow.up_volume !== null && flow.down_volume !== null">
          <span class="track">
            <span
              class="fill bg-good"
              :style="{ width: `${(flow.up_volume / Math.max(1e-9, flow.up_volume + flow.down_volume)) * 100}%` }"
            />
          </span>
          <span class="hint">Phần xanh = tỷ trọng khối lượng rơi vào các phiên tăng giá</span>
        </div>

        <p class="hint note">
          OBV (On-Balance Volume — khối lượng tích lũy): cộng dồn khối lượng phiên tăng,
          trừ khối lượng phiên giảm.
        </p>
      </section>

      <section class="card">
        <header class="head">
          <h3 class="sec-title">Chi tiết từng ngày ({{ flow.points.length }} phiên)</h3>
          <span class="hint">mới nhất ở trên</span>
        </header>
        <div class="scroller">
          <table class="daily">
            <thead>
              <tr>
                <th class="lbl">Ngày</th>
                <th class="num">Đóng cửa</th>
                <th class="num">+/−</th>
                <th class="num">KL (tr cp)</th>
                <th class="num">GT (tỷ đ)</th>
                <th class="num">MFI</th>
                <th class="num">OBV (tr cp)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in daysNewestFirst" :key="p.d">
                <td class="lbl tnum">{{ p.d }}</td>
                <td class="num tnum">{{ num(p.close) }}</td>
                <td class="num tnum" :class="changeClass(p.change_pct)">
                  {{ p.change_pct === null ? '—' : (p.change_pct > 0 ? '+' : '') + num(p.change_pct) + '%' }}
                </td>
                <td class="num tnum">{{ num(p.volume) }}</td>
                <td class="num tnum">{{ num(p.value, 0) }}</td>
                <td class="num tnum" :class="mfiCellClass(p.mfi)">{{ num(p.mfi, 1) }}</td>
                <td class="num tnum">{{ num(p.obv, 0) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="hint note">
          <b>GT (giá trị khớp)</b> là số ƯỚC TÍNH = giá đóng cửa × khối lượng — nguồn không
          trả sẵn giá trị theo ngày, mà mỗi lệnh trong phiên khớp ở giá khác nhau.
        </p>
      </section>

      <ForeignFlowCard v-if="flow.foreign" :foreign="flow.foreign" />

      <p class="msg warn">{{ flow.note }}</p>
    </template>

    <p v-else class="hint">Chưa có dữ liệu dòng tiền.</p>
  </div>
</template>

<style scoped>
.switcher {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.sw {
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--muted);
  border-radius: 8px;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.sw:hover:not(.on) {
  border-color: var(--accent);
  color: var(--accent);
}

.sw.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #04121f;
}

.mfi-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.mfi-val {
  font-size: 34px;
  font-weight: 900;
  line-height: 1;
}

.mfi-state {
  font-size: 13px;
  font-weight: 700;
}

.chart {
  width: 100%;
  height: 150px;
  display: block;
}

.grid {
  stroke: var(--line);
  stroke-width: 0.6;
  vector-effect: non-scaling-stroke;
}

.grid.over {
  stroke: var(--bad);
  stroke-dasharray: 3 3;
  opacity: 0.6;
}

.grid.under {
  stroke: var(--good);
  stroke-dasharray: 3 3;
  opacity: 0.6;
}

.line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.6;
  vector-effect: non-scaling-stroke;
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.lg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--muted);
}

.dash {
  display: inline-block;
  width: 18px;
  height: 0;
  border-top: 2px dashed var(--line);
}

.dash.over {
  border-color: var(--bad);
}

.dash.mid {
  border-color: var(--line);
}

.dash.under {
  border-color: var(--good);
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.tile {
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tile .k {
  font-size: 10.5px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--muted);
}

.tile .v {
  font-size: 19px;
  font-weight: 800;
}

.bar-wrap {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.track {
  display: block;
  height: 9px;
  border-radius: 5px;
  background: var(--bad);
  overflow: hidden;
}

.fill {
  display: block;
  height: 100%;
  border-radius: 5px 0 0 5px;
}

.note {
  margin: 10px 0 0;
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.head .sec-title {
  margin: 0;
}

/* Bảng có thể dài (784 phiên ở khung 3 năm) → cuộn trong khung, tiêu đề dính trên */
.scroller {
  max-height: 46vh;
  overflow: auto;
}

.daily {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.daily th,
.daily td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--line);
}

.daily thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--panel);
  font-size: 11.5px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.daily .lbl {
  text-align: left;
  white-space: nowrap;
}

.daily .num {
  text-align: right;
  white-space: nowrap;
}

.daily tbody td {
  font-weight: 600;
}

@media (max-width: 767px) {
  .scroller {
    max-height: none;
  }

  .daily {
    font-size: 12px;
  }
}
</style>
