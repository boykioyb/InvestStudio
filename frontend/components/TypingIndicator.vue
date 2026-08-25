<script setup lang="ts">
/**
 * Chỉ báo "đang trả lời" cho trợ lý: xoay vòng nhiều câu cho đỡ nhàm + 3 chấm nhảy.
 * Dùng chung cho widget nổi và trang Trợ lý. Chỉ hiển thị — không chứa logic nghiệp vụ.
 */
const props = withDefaults(
  defineProps<{
    /** Danh sách câu chờ tuỳ biến (rỗng → dùng mặc định). */
    phrases?: string[]
    /** Chu kỳ đổi câu (ms). */
    interval?: number
  }>(),
  { interval: 2200 },
)

//  Câu mặc định — phản ánh đúng các bước trợ lý thực sự làm (tra cứu → đọc → tổng hợp).
const DEFAULT_PHRASES = [
  'Đang suy nghĩ',
  'Đang tra cứu dữ liệu',
  'Đang đọc báo cáo tài chính',
  'Đang xem tin tức mới nhất',
  'Đang tổng hợp thông tin',
  'Đang soạn câu trả lời',
]

const list = computed(() => (props.phrases?.length ? props.phrases : DEFAULT_PHRASES))
const idx = ref(0)
const text = computed(() => list.value[idx.value % list.value.length])

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => { idx.value += 1 }, props.interval)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <span class="typing-ind" role="status" aria-live="polite">
    <Transition name="phrase" mode="out-in">
      <span :key="text" class="phrase">{{ text }}</span>
    </Transition>
    <span class="dots" aria-hidden="true"><i /><i /><i /></span>
  </span>
</template>

<style scoped>
.typing-ind {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-style: italic;
}

/*  Ba chấm nhảy so le. */
.dots {
  display: inline-flex;
  gap: 3px;
}
.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.dots i:nth-child(2) { animation-delay: 0.15s; }
.dots i:nth-child(3) { animation-delay: 0.3s; }

@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/*  Đổi câu mượt: câu cũ trượt lên mờ đi, câu mới trượt vào. */
.phrase-enter-active,
.phrase-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.phrase-enter-from { opacity: 0; transform: translateY(4px); }
.phrase-leave-to { opacity: 0; transform: translateY(-4px); }

/*  Người dùng tắt hiệu ứng chuyển động → giữ tĩnh, vẫn nhìn thấy chấm. */
@media (prefers-reduced-motion: reduce) {
  .dots i { animation: none; opacity: 0.6; }
  .phrase-enter-active,
  .phrase-leave-active { transition: none; }
}
</style>
