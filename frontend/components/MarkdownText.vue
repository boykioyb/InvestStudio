<script setup lang="ts">
/**
 * Render Markdown an toàn cho câu trả lời trợ lý.
 *
 * Nội dung do LLM sinh (không tin tuyệt đối) → ESCAPE HTML trước rồi mới cho
 * marked xử lý cú pháp Markdown. Nhờ vậy **đậm**, danh sách, xuống dòng hiển thị
 * đúng, còn thẻ HTML thô (nếu lọt vào) bị vô hiệu — không chạy được (chống XSS).
 */
import { marked } from 'marked'

const props = defineProps<{ text: string }>()

function escapeHtml(raw: string): string {
  return raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const html = computed(() =>
  marked.parse(escapeHtml(props.text || ''), { async: false, breaks: true, gfm: true }) as string
)
</script>

<template>
  <div class="md" v-html="html" />
</template>

<style scoped>
.md :deep(p) {
  margin: 0 0 8px;
}

.md :deep(p:last-child) {
  margin-bottom: 0;
}

.md :deep(ul),
.md :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.md :deep(li) {
  margin: 2px 0;
}

.md :deep(strong) {
  color: var(--text);
  font-weight: 700;
}

.md :deep(code) {
  background: var(--panel2);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.92em;
}

.md :deep(a) {
  color: var(--accent);
}
</style>
