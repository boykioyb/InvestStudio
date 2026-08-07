<script lang="ts">
import { ref } from 'vue'

/**
 * Trạng thái dùng chung ở cấp module: chỉ cho phép MỘT hộp mở tại một thời điểm.
 * Chỉ bị thay đổi bởi thao tác của người dùng phía client nên không rò rỉ giữa
 * các request khi render phía máy chủ.
 */
const activeId = ref(0)
let seq = 0

function nextInstanceId(): number {
  seq += 1
  return seq
}
</script>

<script setup lang="ts">
import type { Explain } from '~/types/stock'

/**
 * Nút ⓘ + hộp giải thích cho một tiêu chí / tầm nhìn.
 *
 * TOÀN BỘ chữ trong hộp đều lấy nguyên văn từ `explain` do API trả về.
 * Component này KHÔNG chứa ngưỡng, công thức hay nhận định nào — chỉ lo
 * việc bày ra màn hình (định vị, lật hướng, khóa trong khung nhìn).
 *
 * Không có `explain` (phản hồi cũ) ⇒ không vẽ gì cả.
 */

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  /** Nội dung giải thích do máy chủ soạn. */
  explain?: Explain | null
  /** Tên tiêu chí/tầm nhìn — chỉ dùng cho nhãn trợ năng và tiêu đề hộp. */
  label: string
}>()

/** Dưới ngưỡng này thì hiện dạng tấm trượt từ đáy thay vì hộp nổi tí hon. */
const MOBILE_MAX = 640
/** Khoảng chừa tối thiểu với mép khung nhìn. */
const EDGE = 8
/** Bề rộng tối đa của hộp nổi. */
const MAX_W = 340

const myId = nextInstanceId()

const triggerEl = ref<HTMLButtonElement | null>(null)
const panelEl = ref<HTMLElement | null>(null)

const isOpen = computed(() => activeId.value === myId)
/** true = tấm trượt toàn màn (mobile), false = hộp nổi neo vào nút. */
const sheet = ref(false)
/** Đã tính xong tọa độ chưa (tránh nháy ở góc trên trái). */
const placed = ref(false)
const boxStyle = ref<Record<string, string>>({})

const hasExplain = computed(() => {
  const e = props.explain
  if (!e) return false
  return Boolean(e.what || e.why || e.how || e.applied || e.scale?.length)
})

const scale = computed<string[]>(() =>
  Array.isArray(props.explain?.scale) ? props.explain!.scale.filter(Boolean) : []
)

/** Neo hộp vào nút, tự lật lên trên và ép vào trong khung nhìn khi thiếu chỗ. */
function place() {
  const trigger = triggerEl.value
  const panel = panelEl.value
  if (!trigger || !panel || sheet.value) {
    placed.value = true
    return
  }

  const vw = window.innerWidth
  const vh = window.innerHeight
  const rect = trigger.getBoundingClientRect()

  const width = Math.min(MAX_W, vw - EDGE * 2)
  const maxHeight = vh - EDGE * 2

  // Áp bề rộng trước rồi mới đo chiều cao thật.
  panel.style.width = `${width}px`
  panel.style.maxHeight = `${maxHeight}px`
  const height = Math.min(panel.offsetHeight, maxHeight)

  let left = rect.left + rect.width / 2 - width / 2
  left = Math.max(EDGE, Math.min(left, vw - width - EDGE))

  const roomBelow = vh - rect.bottom - EDGE
  const roomAbove = rect.top - EDGE
  let top = roomBelow >= height || roomBelow >= roomAbove ? rect.bottom + 6 : rect.top - 6 - height
  top = Math.max(EDGE, Math.min(top, vh - height - EDGE))

  boxStyle.value = {
    width: `${width}px`,
    maxHeight: `${maxHeight}px`,
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`
  }
  placed.value = true
}

function lockPageScroll(on: boolean) {
  document.documentElement.style.overflow = on ? 'hidden' : ''
}

function open() {
  sheet.value = window.innerWidth <= MOBILE_MAX
  placed.value = false
  boxStyle.value = {}
  activeId.value = myId
  if (sheet.value) lockPageScroll(true)
  nextTick(() => {
    place()
    panelEl.value?.focus()
  })
}

/** `restoreFocus` = true khi người dùng chủ động đóng (Esc, nút ✕). */
function close(restoreFocus = true) {
  if (!isOpen.value) return
  activeId.value = 0
  placed.value = false
  lockPageScroll(false)
  if (restoreFocus) nextTick(() => triggerEl.value?.focus())
}

function toggle() {
  if (isOpen.value) close()
  else open()
}

function onDocPointerDown(e: Event) {
  const target = e.target as Node | null
  if (!target) return
  if (panelEl.value?.contains(target)) return
  // Bấm lại chính nút ⓘ: để handler @click tự đảo trạng thái.
  if (triggerEl.value?.contains(target)) return
  close(false)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    close(true)
  }
}

/** Cuộn bất kỳ khung nào bên ngoài hộp ⇒ đóng (hộp đã neo sai chỗ). */
function onScrollCapture(e: Event) {
  if (sheet.value) return
  const target = e.target as Node | null
  if (target && panelEl.value?.contains(target)) return
  close(false)
}

function onResize() {
  if (!isOpen.value) return
  const shouldSheet = window.innerWidth <= MOBILE_MAX
  if (shouldSheet !== sheet.value) {
    sheet.value = shouldSheet
    lockPageScroll(shouldSheet)
    boxStyle.value = {}
  }
  nextTick(place)
}

function bind(on: boolean) {
  const fn = on ? 'addEventListener' : 'removeEventListener'
  document[fn]('pointerdown', onDocPointerDown, true)
  document[fn]('keydown', onKeydown as EventListener, true)
  window[fn]('scroll', onScrollCapture, true)
  window[fn]('resize', onResize)
}

watch(isOpen, (v) => bind(v))

// Chuyển trang cũng phải đóng.
const router = useRouter()
const stopAfterEach = router.afterEach(() => close(false))

onBeforeUnmount(() => {
  stopAfterEach()
  if (isOpen.value) {
    activeId.value = 0
    lockPageScroll(false)
  }
  bind(false)
})
</script>

<template>
  <button
    v-if="hasExplain"
    ref="triggerEl"
    type="button"
    class="info-trigger"
    :class="{ on: isOpen }"
    :aria-label="`Giải thích ${label}`"
    :aria-expanded="isOpen"
    aria-haspopup="dialog"
    @click="toggle"
  >
    <span aria-hidden="true">ⓘ</span>
  </button>

  <Teleport to="body">
    <template v-if="hasExplain && isOpen">
      <div v-if="sheet" class="info-backdrop" @click="close(false)" />

      <div
        ref="panelEl"
        class="info-pop"
        :class="{ sheet, placed }"
        :style="sheet ? undefined : boxStyle"
        role="dialog"
        :aria-label="`Giải thích ${label}`"
        tabindex="-1"
      >
        <header class="pop-head">
          <h3 class="pop-title">{{ label }}</h3>
          <button type="button" class="pop-close" aria-label="Đóng giải thích" @click="close(true)">
            ✕
          </button>
        </header>

        <div class="pop-body">
          <section v-if="explain?.what" class="pop-sec">
            <h4 class="pop-h">Là gì</h4>
            <p class="pop-p">{{ explain.what }}</p>
          </section>

          <section v-if="explain?.why" class="pop-sec">
            <h4 class="pop-h">Vì sao quan trọng</h4>
            <p class="pop-p">{{ explain.why }}</p>
          </section>

          <section v-if="explain?.how" class="pop-sec">
            <h4 class="pop-h">Tính thế nào</h4>
            <p class="pop-p">{{ explain.how }}</p>
          </section>

          <section v-if="scale.length" class="pop-sec">
            <h4 class="pop-h">Thang điểm</h4>
            <ul class="pop-scale">
              <li v-for="(step, i) in scale" :key="i">{{ step }}</li>
            </ul>
          </section>

          <section v-if="explain?.applied" class="pop-sec applied">
            <h4 class="pop-h">Áp vào mã này</h4>
            <p class="pop-p strong">{{ explain.applied }}</p>
          </section>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<style scoped>
/* ---------- Nút ⓘ ---------- */
/* Ô chữ nhỏ 16px để không làm giãn hàng, vùng bấm nới rộng bằng ::after. */
.info-trigger {
  position: relative;
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--muted);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  border-radius: 50%;
}

/* Vùng bấm 24×24 (con trỏ chuột) — không chiếm chỗ trong bố cục. */
.info-trigger::after {
  content: '';
  position: absolute;
  inset: -4px;
}

.info-trigger:hover,
.info-trigger:focus-visible,
.info-trigger.on {
  color: var(--accent);
  opacity: 1;
}

.info-trigger:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

/* Thiết bị cảm ứng: nới vùng bấm lên 44×44 theo khuyến nghị trợ năng. */
@media (hover: none) and (pointer: coarse) {
  .info-trigger {
    font-size: 15px;
    opacity: 1;
  }

  .info-trigger::after {
    inset: -14px;
  }
}

/* ---------- Hộp giải thích ---------- */
.info-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(4, 8, 18, 0.6);
}

.info-pop {
  position: fixed;
  z-index: 100;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 22px 48px rgba(0, 0, 0, 0.55);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  opacity: 1;
  transition: opacity 0.12s ease;
}

/* Chưa tính xong tọa độ thì giấu đi để không nháy ở góc màn hình. */
.info-pop:not(.placed) {
  opacity: 0;
  pointer-events: none;
}

.info-pop:focus {
  outline: none;
}

.pop-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--panel2);
}

.pop-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.pop-close {
  flex: none;
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--muted);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
}

.pop-close:hover {
  color: var(--text);
  border-color: var(--accent);
}

.pop-body {
  padding: 10px 12px 12px;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}

.pop-sec + .pop-sec {
  margin-top: 9px;
}

.pop-h {
  margin: 0 0 3px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--accent);
}

.pop-p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text);
}

.pop-scale {
  margin: 0;
  padding-left: 16px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text);
}

.pop-scale li::marker {
  color: var(--muted);
}

/* Bằng chứng cho điểm số — làm nổi lên rõ nhất trong hộp. */
.applied {
  margin-top: 11px;
  padding: 8px 10px;
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  background: rgba(90, 200, 255, 0.09);
}

.applied .pop-h {
  color: var(--accent);
}

.pop-p.strong {
  font-weight: 700;
}

/* ---------- Mobile: tấm trượt từ đáy ---------- */
.info-pop.sheet {
  left: 0;
  right: 0;
  bottom: 0;
  top: auto;
  width: auto;
  max-height: 82dvh;
  border-radius: 16px 16px 0 0;
  border-bottom: 0;
  animation: sheet-up 0.18s ease-out;
}

.info-pop.sheet .pop-head {
  padding: 12px 14px;
}

.info-pop.sheet .pop-title {
  font-size: 15px;
}

.info-pop.sheet .pop-close {
  width: 40px;
  height: 40px;
  font-size: 15px;
}

.info-pop.sheet .pop-body {
  padding: 12px 14px calc(16px + env(safe-area-inset-bottom, 0px));
}

.info-pop.sheet .pop-p,
.info-pop.sheet .pop-scale {
  font-size: 14px;
}

.info-pop.sheet .pop-h {
  font-size: 11px;
}

@keyframes sheet-up {
  from {
    transform: translateY(16px);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .info-pop {
    transition: none;
  }

  .info-pop.sheet {
    animation: none;
  }
}
</style>
