<script setup lang="ts">
/**
 * Hướng dẫn 3 bước cho lần đầu vào — hiện MỘT lần, tự tắt vĩnh viễn khi đóng.
 *
 * Vì sao không dùng tour bám theo từng nút: người mới chưa có gì trên màn hình
 * để bám vào (chưa nhập mã, chưa có mã theo dõi). Ba thẻ nói rõ dùng công cụ
 * này theo trình tự nào là đủ, và không chặn ai muốn bỏ qua.
 *
 * Trạng thái lưu ở localStorage của chính trình duyệt — không cần tài khoản,
 * và người dùng xóa dữ liệu duyệt web thì hiện lại cũng không sao.
 */
const KEY = 'phantichma.onboarding.v1'

const hien = ref(false)
const buoc = ref(0)

const BUOC = [
  {
    icon: '1',
    title: 'Nhập một mã cổ phiếu',
    body: 'Gõ mã (VD: FPT) vào ô tìm kiếm. Máy crawl dữ liệu công khai rồi chấm 14 tiêu chí '
        + 'tài chính · định giá · kỹ thuật, trả về điểm 0–100 kèm lý do từng tiêu chí.'
  },
  {
    icon: '2',
    title: 'Đọc kịch bản xấu nhất',
    body: 'Phần Quyết định nói thẳng giá cắt lỗ cụ thể và số tiền có thể mất trên tổng tài '
        + 'khoản. Đây là phần quan trọng hơn điểm số: nó cho biết bạn chịu được rủi ro nào.'
  },
  {
    icon: '3',
    title: 'Theo dõi và hỏi thêm',
    body: 'Bấm ☆ để theo dõi mã và đặt ngưỡng giá — hệ thống tự báo khi chạm. Cần đào sâu '
        + 'thì hỏi trợ lý; nó trả lời dựa trên dữ liệu đã lập chỉ mục, kèm nguồn để bạn kiểm chứng.'
  }
]

onMounted(() => {
  try {
    hien.value = !localStorage.getItem(KEY)
  } catch {
    //  Trình duyệt chặn localStorage (ẩn danh, chặn cookie) → coi như đã xem,
    //  thà không hiện còn hơn hiện lại mỗi lần tải trang.
    hien.value = false
  }
})

function dong(): void {
  hien.value = false
  try {
    localStorage.setItem(KEY, new Date().toISOString())
  } catch { /* không lưu được thì thôi */ }
}
</script>

<template>
  <div v-if="hien" class="ob-mask" role="dialog" aria-modal="true"
       aria-labelledby="ob-title" @click.self="dong">
    <div class="ob">
      <p class="ob-step">Bước {{ buoc + 1 }}/{{ BUOC.length }}</p>
      <div class="ob-icon">{{ BUOC[buoc].icon }}</div>
      <h2 id="ob-title">{{ BUOC[buoc].title }}</h2>
      <p class="ob-body">{{ BUOC[buoc].body }}</p>

      <div class="ob-dots" aria-hidden="true">
        <i v-for="(_, i) in BUOC" :key="i" :class="{ on: i === buoc }" />
      </div>

      <div class="ob-act">
        <button type="button" class="btn ghost" @click="dong">Bỏ qua</button>
        <button v-if="buoc < BUOC.length - 1" type="button" class="btn primary" @click="buoc++">
          Tiếp →
        </button>
        <button v-else type="button" class="btn primary" @click="dong">Bắt đầu</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ob-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(4, 8, 18, 0.72);
  backdrop-filter: blur(4px);
}

.ob {
  width: min(440px, 100%);
  padding: 24px;
  text-align: center;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-solid, #0f1626);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}

.ob-step { margin: 0 0 14px; font-size: 12px; color: var(--muted); }

.ob-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-weight: 800;
  color: var(--bg, #0b1020);
  background: var(--accent);
}

h2 { margin: 0 0 8px; font-size: 19px; }
.ob-body { margin: 0; font-size: 14px; line-height: 1.6; color: var(--text-2); text-wrap: pretty; }

.ob-dots { display: flex; justify-content: center; gap: 6px; margin: 18px 0 16px; }
.ob-dots i { width: 6px; height: 6px; border-radius: 50%; background: var(--line-hi, #2a3550); }
.ob-dots i.on { background: var(--accent); width: 18px; border-radius: 3px; }

.ob-act { display: flex; justify-content: center; gap: 10px; }
.ob-act .btn.ghost { background: none; }

@media (max-width: 520px) {
  .ob { padding: 20px 16px; }
}
</style>
