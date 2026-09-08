<script setup lang="ts">
/**
 * Chân trang dùng chung: miễn trừ trách nhiệm + lối vào các trang pháp lý.
 *
 * Vì sao miễn trừ phải nằm ở ĐÂY chứ không chỉ trong README: người dùng không
 * đọc README. Công cụ đưa ra điểm số và chữ "cắt lỗ / mua thêm" thì dòng "không
 * phải khuyến nghị đầu tư" phải ở nơi họ thật sự nhìn thấy.
 */
const route = useRoute()

//  Trang trợ lý là bố cục cao đúng một màn hình — chèn chân trang vào sẽ vỡ.
const an = computed(() => route.path === '/assistant')

const nam = new Date().getFullYear()
</script>

<template>
  <footer v-if="!an" class="ft">
    <p class="mien-tru">
      <b>Không phải khuyến nghị đầu tư.</b>
      Đây là công cụ hỗ trợ tư duy. Dữ liệu lấy từ nguồn công khai, có thể trễ hoặc
      sai lệch — hãy tự kiểm chứng trước mọi quyết định liên quan tới tiền.
    </p>
    <nav class="lien-ket">
      <NuxtLink to="/scoring">Cách chấm điểm</NuxtLink>
      <NuxtLink to="/terms">Điều khoản sử dụng</NuxtLink>
      <NuxtLink to="/privacy">Chính sách quyền riêng tư</NuxtLink>
    </nav>
    <p class="ban-quyen">© {{ nam }} Phân Tích Mã</p>
  </footer>
</template>

<style scoped>
.ft {
  max-width: 1320px;
  margin: 40px auto 0;
  padding: 22px 26px 34px;
  border-top: 1px solid var(--line);
  font-size: 12.5px;
  color: var(--muted);
}

.mien-tru { margin: 0 0 12px; max-width: 760px; line-height: 1.6; }
.mien-tru b { color: var(--text-2); }

.lien-ket { display: flex; flex-wrap: wrap; gap: 6px 18px; }
.lien-ket a { color: var(--muted); text-decoration: none; }
.lien-ket a:hover { color: var(--accent); text-decoration: underline; }

.ban-quyen { margin: 14px 0 0; color: var(--muted-2); }

@media (max-width: 620px) {
  .ft { padding: 18px 14px 28px; }
}
</style>
