<script setup lang="ts">
import type { RatioItem } from '~/types/stock'

/** Tab Chỉ số: bộ chỉ số tài chính kỳ gần nhất, gom nhóm. */
const props = defineProps<{ ticker: string }>()

const { ratios, isLoading, errorOf, loadRatios } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:ratios`)

watch(() => props.ticker, (t) => t && loadRatios(t), { immediate: true })

/** Ghép giá trị với hậu tố do máy chủ quy định — không tự đổi đơn vị. */
function show(item: RatioItem): string {
  if (item.value === null || item.value === undefined) return '—'
  const num = item.value.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
  if (item.percent) return `${num}%`
  return item.unit ? `${num} ${item.unit}` : num
}
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải chỉ số tài chính…</p>

    <template v-else-if="ratios">
      <p class="hint period">
        Số liệu của <b>{{ ratios.period_label }}</b>. Nguồn chỉ cho biết kỳ gần nhất một cách
        chắc chắn nên chỉ hiển thị một kỳ, không suy đoán năm cho các kỳ trước.
      </p>

      <div class="groups">
        <section v-for="g in ratios.groups" :key="g.name" class="card">
          <h3 class="sec-title">{{ g.name }}</h3>
          <div v-for="item in g.items" :key="item.label" class="row">
            <span class="lbl">{{ item.label }}</span>
            <span class="val tnum">{{ show(item) }}</span>
          </div>
        </section>
      </div>
    </template>

    <p v-else class="hint">Chưa có dữ liệu chỉ số.</p>
  </div>
</template>

<style scoped>
.period {
  margin: 0 0 12px;
}

.groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
  align-items: start;
}

.row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13.5px;
}

.row:last-child {
  border-bottom: none;
}

.lbl {
  color: var(--muted);
  min-width: 0;
}

.val {
  font-weight: 700;
  white-space: nowrap;
}
</style>
