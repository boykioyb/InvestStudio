<script setup lang="ts">
import { Check } from 'lucide-vue-next'

/**
 * Hero trang chủ: nhãn trạng thái phiên (thật), tiêu đề, 3 điểm bán, ô tìm mã
 * và các mã ví dụ. Không có màn loading giả — trang /analysis tự lo phần đó.
 */
const props = defineProps<{ inSession: boolean; sessionLabel: string }>()
const emit = defineEmits<{ pick: [code: string] }>()

const EXAMPLES = ['FPT', 'VCB', 'HPG', 'MWG', 'VNM', 'MBB']
const BULLETS = [
  'Phân tích tài chính, định giá và kỹ thuật',
  'Điểm tổng hợp 0–100 theo 14 tiêu chí',
  'Ước tính rủi ro trong kịch bản xấu'
]

const sessionText = computed(() =>
  props.inSession
    ? 'Thị trường đang mở cửa · cập nhật theo phiên'
    : props.sessionLabel || 'Ngoài phiên giao dịch'
)
</script>

<template>
  <section class="hero">
    <div class="pill">
      <span class="dot" :class="{ live: inSession }" />{{ sessionText }}
    </div>
    <h1>Đánh giá cổ phiếu trước mỗi quyết định đầu tư.</h1>
    <!-- Câu định vị: nói THẲNG người dùng nhận được gì, thay vì để họ tự đoán
         từ ba gạch đầu dòng bên dưới. -->
    <p class="promise">
      Nhập một mã — máy chấm 14 tiêu chí tài chính, định giá và kỹ thuật, rồi nói
      thẳng mã đó <b>mạnh yếu ở đâu</b> và <b>bạn mất bao nhiêu nếu kịch bản xấu xảy ra</b>.
    </p>
    <ul class="bullets">
      <li v-for="b in BULLETS" :key="b"><Check class="ck" />{{ b }}</li>
    </ul>
    <TickerSearch @submit="emit('pick', $event)" />
    <p class="fine">Thông tin mang tính tham khảo, không phải khuyến nghị đầu tư.</p>
    <div class="chips">
      <span class="lbl">Thử nhanh:</span>
      <button v-for="c in EXAMPLES" :key="c" type="button" @click="emit('pick', c)">{{ c }}</button>
    </div>
  </section>
</template>

<style scoped>
.hero { max-width: 1320px; margin: 0 auto; padding: 52px 26px 0; text-align: center; }
.pill { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted);
  border: 1px solid var(--line); background: var(--panel-solid); border-radius: 20px;
  padding: 6px 14px; margin-bottom: 22px; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted-2); }
.dot.live { background: var(--good); box-shadow: 0 0 10px var(--good); animation: hero-pulse 2s infinite; }
@keyframes hero-pulse { 50% { opacity: 0.35; } }

h1 { font-size: clamp(30px, 4vw, 52px); line-height: 1.12; margin: 0 auto 18px; font-weight: 700;
  letter-spacing: -0.8px; max-width: 820px; text-wrap: balance; }
.promise { max-width: 720px; margin: 0 auto 22px; font-size: clamp(15px, 1.6vw, 17px);
  line-height: 1.55; color: var(--text-2); text-wrap: pretty; }
.promise b { color: var(--text); font-weight: 600; }
.bullets { list-style: none; margin: 0 auto 28px; padding: 0; display: flex; flex-wrap: wrap;
  justify-content: center; gap: 8px 22px; font-size: 15.5px; color: var(--text-2); max-width: 1000px; }
.bullets li { display: inline-flex; align-items: center; gap: 8px; }
.ck { color: var(--accent); width: 16px; height: 16px; flex: none; }
.fine { margin: 10px 0 0; font-size: 12.5px; color: var(--muted-2); }
.chips { display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
.chips .lbl { font-size: 13px; color: var(--muted-2); flex: none; white-space: nowrap; }
.chips button { min-height: 40px; font-size: 13px; color: var(--muted); border: 1px solid var(--line);
  background: var(--panel-solid); border-radius: 20px; padding: 0 14px; cursor: pointer;
  font-family: var(--mono); font-weight: 600; transition: 0.15s; }
.chips button:hover { color: var(--text); border-color: var(--accent); }

@media (max-width: 700px) {
  .hero { padding: 22px 16px 0; text-align: left; }
  .pill { margin-bottom: 12px; font-size: 12px; border: none; background: none; padding: 0; }
  h1 { font-size: 28px; line-height: 1.2; letter-spacing: -0.5px; margin-bottom: 10px; }
  .bullets { justify-content: flex-start; gap: 6px 16px; font-size: 13.5px; margin-bottom: 16px; }
  .chips { justify-content: flex-start; margin-left: -16px; margin-right: -16px; padding: 0 16px;
    overflow-x: auto; scrollbar-width: none; flex-wrap: nowrap; }
  .chips button { flex: none; min-height: 44px; }
}
</style>
