<script setup lang="ts">
/** Chỉ báo đang tải — spinner căn GIỮA vùng chứa, kèm nhãn tùy chọn. */
defineProps<{ label?: string }>()
</script>

<template>
  <div class="loading-state" role="status" aria-live="polite">
    <span class="spinner" aria-hidden="true" />
    <p v-if="label" class="lbl">{{ label }}</p>
  </div>
</template>

<style scoped>
.loading-state {
  flex: 1;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 32px 16px;
  text-align: center;
  color: var(--muted);
}

.spinner {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 3px solid var(--panel-hi);
  border-top-color: var(--accent);
  border-right-color: var(--accent2);
  animation: ls-spin 0.9s linear infinite;
}

.lbl {
  margin: 0;
  font-size: 13px;
}

@keyframes ls-spin {
  to {
    transform: rotate(360deg);
  }
}

/* Tôn trọng người dùng tắt hiệu ứng: giữ vòng tĩnh, không quay. */
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
  }
}
</style>
