<script setup lang="ts">
/**
 * Bộ chọn ngày cho giao diện tối.
 *
 * Vì sao không dùng `<input type="date">`: lịch mặc định của trình duyệt là nền
 * trắng, tên tháng tiếng Anh và định dạng mm/dd/yyyy theo máy — chọi với giao
 * diện tối và sai thói quen đọc ngày của người Việt.
 *
 * Giá trị vào/ra vẫn là chuỗi ISO `YYYY-MM-DD` để backend không phải đoán,
 * chỉ phần HIỂN THỊ là dd/mm/yyyy.
 */
const props = withDefaults(
  defineProps<{
    modelValue: string
    label?: string
    placeholder?: string
    /** Chặn ngày tương lai — mặc định bật vì không thể đã mua ở ngày chưa tới. */
    maxToday?: boolean
    id?: string
  }>(),
  { label: '', placeholder: 'Chọn ngày', maxToday: true, id: '' }
)

const emit = defineEmits<{ 'update:modelValue': [string] }>()

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
const MONTHS = [
  'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
  'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
]

const open = ref(false)
const trigger = ref<HTMLButtonElement | null>(null)
const panel = ref<HTMLElement | null>(null)
const pos = ref({ top: 0, left: 0 })

/** Ngày local dạng YYYY-MM-DD. Cố ý KHÔNG dùng toISOString (lệch múi giờ). */
function toISO(d: Date): string {
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function parseISO(text: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text || '')
  if (!m) return null
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(d.getTime()) ? null : d
}

const todayISO = toISO(new Date())

/** Chuỗi hiển thị dd/mm/yyyy. */
const display = computed(() => {
  const d = parseISO(props.modelValue)
  if (!d) return ''
  return `${`${d.getDate()}`.padStart(2, '0')}/${`${d.getMonth() + 1}`.padStart(2, '0')}/${d.getFullYear()}`
})

//  Tháng đang xem trong lịch (không nhất thiết là tháng của giá trị đã chọn).
const cursor = ref(parseISO(props.modelValue) || new Date())
watch(() => props.modelValue, (v) => {
  const d = parseISO(v)
  if (d) cursor.value = d
})

interface Cell {
  iso: string
  day: number
  outside: boolean
  disabled: boolean
}

/** Lưới 6 hàng × 7 cột, bắt đầu từ Thứ Hai theo thói quen Việt Nam. */
const cells = computed<Cell[]>(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const first = new Date(year, month, 1)
  //  getDay(): 0 = Chủ nhật → đổi sang 0 = Thứ Hai.
  const offset = (first.getDay() + 6) % 7
  const start = new Date(year, month, 1 - offset)

  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    const iso = toISO(d)
    return {
      iso,
      day: d.getDate(),
      outside: d.getMonth() !== month,
      disabled: props.maxToday && iso > todayISO
    }
  })
})

const title = computed(() => `${MONTHS[cursor.value.getMonth()]} ${cursor.value.getFullYear()}`)

/** Không cho lật sang tháng hoàn toàn ở tương lai khi đang chặn ngày tương lai. */
const canGoNext = computed(() => {
  if (!props.maxToday) return true
  const now = new Date()
  const c = cursor.value
  return c.getFullYear() < now.getFullYear() ||
    (c.getFullYear() === now.getFullYear() && c.getMonth() < now.getMonth())
})

function shiftMonth(delta: number): void {
  const c = cursor.value
  cursor.value = new Date(c.getFullYear(), c.getMonth() + delta, 1)
}

function place(): void {
  const el = trigger.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const width = 288
  const height = 336
  //  Bật lên trên nếu dưới không đủ chỗ; kẹp trong màn hình để không bị cắt.
  const below = window.innerHeight - r.bottom
  const top = below < height && r.top > height ? r.top - height - 6 : r.bottom + 6
  const left = Math.min(Math.max(8, r.left), window.innerWidth - width - 8)
  pos.value = { top, left }
}

function toggle(): void {
  open.value = !open.value
  if (open.value) nextTick(place)
}

function pick(cell: Cell): void {
  if (cell.disabled) return
  emit('update:modelValue', cell.iso)
  open.value = false
  trigger.value?.focus()
}

function clear(): void {
  emit('update:modelValue', '')
  open.value = false
  trigger.value?.focus()
}

function onPointerDown(event: PointerEvent): void {
  const target = event.target as Node
  if (panel.value?.contains(target) || trigger.value?.contains(target)) return
  open.value = false
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape' && open.value) {
    open.value = false
    trigger.value?.focus()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown, true)
  document.addEventListener('keydown', onKey)
  window.addEventListener('resize', place)
  window.addEventListener('scroll', place, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onPointerDown, true)
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', place)
  window.removeEventListener('scroll', place, true)
})
</script>

<template>
  <div class="dp">
    <label v-if="label" :for="id || undefined" class="dp-label">{{ label }}</label>

    <button
      :id="id || undefined"
      ref="trigger"
      type="button"
      class="dp-trigger"
      :class="{ empty: !display }"
      :aria-expanded="open"
      aria-haspopup="dialog"
      @click="toggle"
    >
      <span>{{ display || placeholder }}</span>
      <span class="dp-icon" aria-hidden="true">📅</span>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="panel"
        class="dp-panel"
        role="dialog"
        aria-label="Chọn ngày"
        :style="{ top: `${pos.top}px`, left: `${pos.left}px` }"
      >
        <header class="dp-head">
          <button type="button" class="nav" aria-label="Tháng trước" @click="shiftMonth(-1)">‹</button>
          <span class="dp-title">{{ title }}</span>
          <button
            type="button"
            class="nav"
            aria-label="Tháng sau"
            :disabled="!canGoNext"
            @click="shiftMonth(1)"
          >
            ›
          </button>
        </header>

        <div class="dp-week" aria-hidden="true">
          <span v-for="w in WEEKDAYS" :key="w">{{ w }}</span>
        </div>

        <div class="dp-grid">
          <button
            v-for="c in cells"
            :key="c.iso"
            type="button"
            class="day"
            :class="{
              outside: c.outside,
              today: c.iso === todayISO,
              on: c.iso === modelValue
            }"
            :disabled="c.disabled"
            :aria-current="c.iso === todayISO ? 'date' : undefined"
            @click="pick(c)"
          >
            {{ c.day }}
          </button>
        </div>

        <footer class="dp-foot">
          <button type="button" class="link" @click="clear">Xóa</button>
          <button
            type="button"
            class="link accent"
            @click="pick({ iso: todayISO, day: 0, outside: false, disabled: false })"
          >
            Hôm nay
          </button>
        </footer>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.dp {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.dp-label {
  font-size: 12px;
  color: var(--muted);
}

.dp-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  background: var(--panel2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
}

.dp-trigger:hover {
  border-color: var(--accent);
}

.dp-trigger.empty span:first-child {
  color: var(--muted);
}

.dp-icon {
  font-size: 12px;
  opacity: 0.75;
}
</style>

<style>
/* Panel được Teleport ra body nên không dùng được style scoped. */
.dp-panel {
  position: fixed;
  z-index: 90;
  width: 288px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.5);
  padding: 12px;
}

.dp-panel .dp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.dp-panel .dp-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.dp-panel .nav {
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--text);
  border-radius: 8px;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.dp-panel .nav:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.dp-panel .nav:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.dp-panel .dp-week,
.dp-panel .dp-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.dp-panel .dp-week {
  margin-bottom: 4px;
}

.dp-panel .dp-week span {
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  padding: 4px 0;
}

.dp-panel .day {
  aspect-ratio: 1;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  border-radius: 8px;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
}

.dp-panel .day:hover:not(:disabled):not(.on) {
  background: var(--panel2);
  border-color: var(--accent);
}

.dp-panel .day.outside {
  color: var(--muted);
  opacity: 0.45;
}

/* Hôm nay: viền nhấn để phân biệt với ngày ĐANG CHỌN (nền đặc) */
.dp-panel .day.today {
  border-color: var(--accent);
}

.dp-panel .day.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #04121f;
  font-weight: 800;
}

.dp-panel .day:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.dp-panel .dp-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--line);
}

.dp-panel .link {
  border: none;
  background: none;
  color: var(--muted);
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
  padding: 2px 4px;
}

.dp-panel .link:hover {
  color: var(--text);
}

.dp-panel .link.accent {
  color: var(--accent);
  font-weight: 600;
}
</style>
