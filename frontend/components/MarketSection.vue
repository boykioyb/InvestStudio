<script setup lang="ts">
import type { Mover } from '~/composables/useMarketOverview'

/**
 * Khối "thị trường" trên trang chủ: chọn rổ chỉ số, độ rộng phiên và ba cột mã
 * đáng chú ý. Toàn bộ số liệu do `useMarketOverview` (máy chủ) đưa vào.
 * Desktop: ba cột cạnh nhau. Mobile: gộp thành tab, mỗi lần xem một cột.
 */
const props = defineProps<{
  group: string
  pending: boolean
  error: string
  inSession: boolean
  sessionLabel: string
  gainers: Mover[]
  losers: Mover[]
  mostActive: Mover[]
  activeLabel: string
  breadth: { up: number; down: number; flat: number }
}>()
const emit = defineEmits<{ pickGroup: [key: string] }>()

const BASKETS = ['VN30', 'VN100', 'HOSE', 'HNX30']
const tab = ref(0)

const title = computed(() =>
  props.inSession
    ? `Thị trường lúc này · ${props.group}`
    : `${props.sessionLabel || 'Ngoài phiên giao dịch'} · ${props.group}`
)
const sub = computed(() =>
  props.inSession
    ? 'Số liệu khớp lệnh cập nhật liên tục trong phiên. Bấm một mã để chấm điểm ngay.'
    : 'Kết quả phiên gần nhất, lấy từ bảng giá cuối phiên. Bấm một mã để chấm điểm ngay.'
)

//  Ngoài phiên nguồn không có % thay đổi → chỉ còn cột "sôi động nhất".
const columns = computed(() =>
  props.inSession
    ? [
        { title: 'Tăng mạnh nhất', short: 'Tăng mạnh', items: props.gainers },
        { title: 'Giảm sâu nhất', short: 'Giảm sâu', items: props.losers },
        { title: `Sôi động nhất · ${props.activeLabel}`, short: 'Sôi động', items: props.mostActive }
      ]
    : [{ title: `Sôi động nhất · ${props.activeLabel}`, short: 'Sôi động', items: props.mostActive }]
)

const total = computed(() => props.breadth.up + props.breadth.down + props.breadth.flat)
const w = (n: number): string => (total.value ? `${(n / total.value) * 100}%` : '0%')

watch(columns, (cols) => { if (tab.value >= cols.length) tab.value = 0 })
</script>

<template>
  <section class="market">
    <div class="head">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ sub }}</p>
      </div>
      <div class="baskets" role="group" aria-label="Rổ chỉ số">
        <button
          v-for="b in BASKETS" :key="b" type="button" :aria-pressed="b === group"
          :class="{ on: b === group }" :disabled="pending" @click="emit('pickGroup', b)"
        >{{ b }}</button>
      </div>
    </div>

    <p v-if="error" class="msg error" role="alert">{{ error }}</p>

    <div v-if="inSession && total" class="breadth">
      <h3 class="sec-title">Độ rộng thị trường · {{ group }}</h3>
      <div class="bd-bar">
        <span class="bg-good" :style="{ width: w(breadth.up) }" />
        <span class="bg-na" :style="{ width: w(breadth.flat) }" />
        <span class="bg-bad" :style="{ width: w(breadth.down) }" />
      </div>
      <div class="bd-nums tnum">
        <span class="lv-good">▲ {{ breadth.up }} tăng</span>
        <span class="muted">■ {{ breadth.flat }}</span>
        <span class="lv-bad">▼ {{ breadth.down }} giảm</span>
      </div>
    </div>

    <LoadingState v-if="pending && !mostActive.length" label="Đang tải bảng giá…" />
    <template v-else>
      <div v-if="columns.length > 1" class="tabs" role="tablist">
        <button
          v-for="(c, i) in columns" :key="c.short" type="button" role="tab"
          :aria-selected="i === tab" :class="{ on: i === tab }" @click="tab = i"
        >{{ c.short }}</button>
      </div>
      <div class="cols" :class="{ single: columns.length === 1 }">
        <div v-for="(c, i) in columns" :key="c.title" class="col" :class="{ on: i === tab }">
          <h3 class="sec-title">{{ c.title }}</h3>
          <MoverList :items="c.items" show-price />
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.market { max-width: 1320px; margin: 0 auto; padding: 48px 26px 0; }
.head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; margin-bottom: 14px; }
h2 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }
.head p { margin: 4px 0 0; font-size: 13.5px; color: var(--muted); }
.baskets { display: flex; gap: 6px; flex-wrap: wrap; }
.baskets button { min-height: 40px; border: 1px solid var(--line); background: var(--panel-solid);
  color: var(--muted); border-radius: 20px; padding: 0 14px; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: var(--sans); transition: 0.15s; }
.baskets button:hover:not(:disabled) { border-color: var(--accent); }
.baskets button.on { border-color: var(--accent); background: var(--accent); color: var(--on-accent); }
.baskets button:disabled { opacity: 0.6; cursor: not-allowed; }

.breadth { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 20px; margin-bottom: 16px; }
.bd-bar { display: flex; height: 10px; border-radius: 6px; overflow: hidden; gap: 2px; }
.bd-bar span { display: block; }
.bd-nums { display: flex; gap: 16px; font-size: 13px; margin-top: 8px; }

.tabs { display: none; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: 16px; }
.cols.single { grid-template-columns: 1fr; }
.col { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; min-width: 0; }
.msg { margin: 0 0 12px; }

@media (max-width: 700px) {
  .market { padding: 28px 16px 0; }
  h2 { font-size: 20px; line-height: 1.25; }
  .head { align-items: flex-start; }
  .baskets { margin-left: -16px; margin-right: -16px; padding: 0 16px; overflow-x: auto;
    scrollbar-width: none; flex-wrap: nowrap; }
  .baskets button { flex: none; min-height: 44px; }
  .tabs { display: flex; gap: 4px; padding: 4px; background: var(--panel-deep);
    border: 1px solid var(--line); border-radius: 12px; margin-bottom: 6px; }
  .tabs button { flex: 1; min-height: 44px; border: none; border-radius: 9px; background: none;
    color: var(--muted); font-size: 13.5px; font-weight: 500; cursor: pointer;
    font-family: var(--sans); white-space: nowrap; padding: 0 6px; }
  .tabs button.on { background: var(--accent); color: var(--on-accent); font-weight: 700; }
  /* mobile: chỉ hiện cột đang chọn */
  .cols { display: block; }
  .col { background: none; border: none; border-radius: 0; padding: 0; display: none; }
  .col.on { display: block; }
}
</style>
