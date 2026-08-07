<script setup lang="ts">
import { useId } from 'vue'

/**
 * Biểu đồ giá dạng đường (inline SVG).
 * Chỉ vẽ đúng mảng `prices` mà API trả về — KHÔNG bịa thêm dữ liệu.
 * Nếu không có đủ 2 điểm giá thì không vẽ gì cả.
 */
const props = withDefaults(
  defineProps<{
    prices: number[]
    /** Ghi chú nguồn hiển thị dưới biểu đồ. */
    caption?: string
  }>(),
  { caption: '' }
)

const { price } = useFormat()

const uid = useId()
const gradId = computed(() => `spark-grad-${uid}`)

// Kích thước hệ tọa độ SVG (co giãn theo bề ngang màn hình).
const W = 600
const H = 140
const PAD_X = 10
const PAD_Y = 14

/** Chỉ giữ các số hợp lệ; không thay thế, không nội suy giá trị thiếu. */
const series = computed<number[]>(() =>
  (Array.isArray(props.prices) ? props.prices : []).filter(
    (n): n is number => typeof n === 'number' && Number.isFinite(n)
  )
)

const hasChart = computed(() => series.value.length >= 2)

const stats = computed(() => {
  const s = series.value
  if (!s.length) return null
  return {
    min: Math.min(...s),
    max: Math.max(...s),
    first: s[0]!,
    last: s[s.length - 1]!,
    count: s.length
  }
})

/** Chuẩn hóa min–max về khung vẽ. Series phẳng thì vẽ đường giữa khung. */
const points = computed<{ x: number; y: number }[]>(() => {
  const s = series.value
  if (s.length < 2) return []

  const min = Math.min(...s)
  const max = Math.max(...s)
  const span = max - min
  const innerW = W - PAD_X * 2
  const innerH = H - PAD_Y * 2

  return s.map((v, i) => ({
    x: PAD_X + (innerW * i) / (s.length - 1),
    y: span === 0 ? PAD_Y + innerH / 2 : PAD_Y + innerH * (1 - (v - min) / span)
  }))
})

const linePath = computed(() =>
  points.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')
)

const areaPath = computed(() => {
  const pts = points.value
  if (!pts.length) return ''
  const first = pts[0]!
  const last = pts[pts.length - 1]!
  return `${linePath.value} L${last.x.toFixed(2)} ${H - PAD_Y} L${first.x.toFixed(2)} ${H - PAD_Y} Z`
})

const lastPoint = computed(() => points.value[points.value.length - 1] ?? null)

/** Bề rộng vùng bắt chuột cho mỗi phiên (để hiện tooltip gốc của trình duyệt). */
const hitWidth = computed(() => (W - PAD_X * 2) / Math.max(1, series.value.length - 1))
</script>

<template>
  <div class="spark-wrap">
    <template v-if="hasChart">
      <svg
        class="spark"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="none"
        role="img"
        :aria-label="`Diễn biến giá ${stats?.count} phiên gần nhất`"
      >
        <defs>
          <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.28" />
            <stop offset="100%" stop-color="var(--accent)" stop-opacity="0" />
          </linearGradient>
        </defs>

        <!-- đường kẻ chân, mảnh và chìm -->
        <line
          :x1="PAD_X"
          :y1="H - PAD_Y"
          :x2="W - PAD_X"
          :y2="H - PAD_Y"
          stroke="var(--line)"
          stroke-width="1"
          vector-effect="non-scaling-stroke"
        />

        <path :d="areaPath" :fill="`url(#${gradId})`" />
        <path
          :d="linePath"
          fill="none"
          stroke="var(--accent)"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
          vector-effect="non-scaling-stroke"
        />

        <!--
          Điểm cuối. Dùng đoạn thẳng dài 0 + đầu bo tròn + non-scaling-stroke để
          chấm luôn tròn đều dù khung SVG bị kéo giãn theo bề ngang.
        -->
        <template v-if="lastPoint">
          <line
            :x1="lastPoint.x"
            :y1="lastPoint.y"
            :x2="lastPoint.x"
            :y2="lastPoint.y"
            stroke="var(--panel)"
            stroke-width="12"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
          <line
            :x1="lastPoint.x"
            :y1="lastPoint.y"
            :x2="lastPoint.x"
            :y2="lastPoint.y"
            stroke="var(--accent)"
            stroke-width="8"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
        </template>

        <!-- vùng bắt chuột: tooltip gốc của trình duyệt cho từng phiên -->
        <rect
          v-for="(p, i) in points"
          :key="i"
          :x="p.x - hitWidth / 2"
          :y="0"
          :width="hitWidth"
          :height="H"
          fill="transparent"
        >
          <title>Phiên {{ i + 1 }}/{{ points.length }}: {{ price(series[i]) }}</title>
        </rect>
      </svg>

      <div v-if="stats" class="legendrow">
        <span>Thấp nhất <b class="tnum">{{ price(stats.min) }}</b></span>
        <span>Cao nhất <b class="tnum">{{ price(stats.max) }}</b></span>
        <span>Gần nhất <b class="tnum">{{ price(stats.last) }}</b></span>
        <span class="cnt">{{ stats.count }} phiên</span>
      </div>

      <p v-if="caption" class="hint">{{ caption }}</p>
    </template>

    <p v-else class="hint na">
      Chưa lấy được chuỗi giá lịch sử nên không vẽ được biểu đồ. Công cụ không tạo dữ liệu giả
      để lấp chỗ trống.
    </p>
  </div>
</template>

<style scoped>
.spark-wrap {
  width: 100%;
}

.spark {
  display: block;
  width: 100%;
  height: 140px;
}

.legendrow {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 8px;
}

.legendrow b {
  color: var(--text);
  font-weight: 700;
}

.cnt {
  margin-left: auto;
}

.na {
  color: var(--muted);
  font-style: italic;
}
</style>
