<script setup lang="ts">
/**
 * Miễn trừ trách nhiệm cạnh MỖI điểm số / khu vực phân tích (legal-checklist L1).
 *
 * Định vị sản phẩm là công cụ THÔNG TIN/GIÁO DỤC, không phải tư vấn đầu tư. Thuần
 * hiển thị — không có số liệu, không logic. `compact` dùng cho chỗ chật (dưới điểm
 * tổng); mặc định là dạng đầy đủ một dòng.
 */
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<template>
  <p class="disclaimer" :class="{ compact }" role="note">
    <span aria-hidden="true" class="ic">ⓘ</span>
    <span>
      Đây là thông tin tham khảo, <b>không phải khuyến nghị đầu tư</b>. Quyết định và
      rủi ro đầu tư là của bạn.
    </span>
  </p>
</template>

<style scoped>
.disclaimer {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  padding: 7px 9px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  background: var(--panel2);
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.disclaimer .ic {
  flex: none;
  line-height: 1.5;
  opacity: 0.8;
}

.disclaimer b {
  color: var(--text);
  font-weight: 700;
}

.disclaimer.compact {
  padding: 5px 8px;
  font-size: 10.5px;
  border-style: solid;
}
</style>
