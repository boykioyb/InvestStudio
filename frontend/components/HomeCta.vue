<script setup lang="ts">
/** Khối kêu gọi hành động cuối trang chủ: nhập mã là chấm điểm ngay. */
const emit = defineEmits<{ pick: [code: string] }>()
</script>

<template>
  <section class="cta">
    <div class="box">
      <div>
        <h2>Mã bạn đang cầm được mấy điểm?</h2>
        <p>Khoảng 20 giây. Đăng nhập chỉ cần khi muốn lưu mã theo dõi và hỏi trợ lý.</p>
      </div>
      <TickerSearch variant="cta" placeholder="VD: HPG" @submit="emit('pick', $event)" />
    </div>
  </section>
</template>

<style scoped>
.cta { max-width: 1320px; margin: 0 auto; padding: 48px 26px 0; }
.box { background: var(--panel-solid); border: 1px solid rgba(90, 200, 255, 0.3); border-radius: 14px;
  padding: 28px 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: 20px; align-items: center; }
h2 { margin: 0 0 6px; font-size: clamp(20px, 2.4vw, 28px); font-weight: 700; letter-spacing: -0.4px; line-height: 1.2; }
p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.55; }

@media (max-width: 700px) {
  .cta { padding: 28px 16px 0; }
  .box { padding: 18px 16px; gap: 14px; }
  h2 { font-size: 20px; }
  p { font-size: 13.5px; }
}
</style>
