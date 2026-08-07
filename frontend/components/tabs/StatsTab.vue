<script setup lang="ts">
import type { RangeKey } from '~/types/stock'

/** Tab Thống kê: biên độ, biến động, nhịp giao dịch — tự tính từ lịch sử giá. */
const props = defineProps<{ ticker: string }>()

const { stats, isLoading, errorOf, loadStats } = useStockDetails()

const range = ref<RangeKey>('1y')
const key = computed(() => `${props.ticker.toUpperCase()}:stats:${range.value}`)

watch([() => props.ticker, range], ([t, r]) => t && loadStats(t, r), { immediate: true })
</script>

<template>
  <div class="tab-body">
    <div class="switcher" role="group" aria-label="Khung thời gian">
      <button
        v-for="r in PRICE_RANGES"
        :key="r.key"
        type="button"
        class="sw"
        :class="{ on: range === r.key }"
        :aria-pressed="range === r.key"
        @click="range = r.key"
      >
        {{ r.title }}
      </button>
    </div>

    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tính thống kê…</p>

    <template v-else-if="stats">
      <div class="groups">
        <section v-for="g in stats.groups" :key="g.name" class="card">
          <h3 class="sec-title">{{ g.name }}</h3>
          <div v-for="item in g.items" :key="item.label" class="row">
            <span class="lbl">
              {{ item.label }}
              <span v-if="item.note" class="hint">{{ item.note }}</span>
            </span>
            <span class="val tnum">{{ item.value }}</span>
          </div>
        </section>
      </div>
      <p class="hint">{{ stats.note }}</p>
    </template>

    <p v-else class="hint">Chưa có dữ liệu thống kê.</p>
  </div>
</template>

<style scoped>
.switcher {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.sw {
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--muted);
  border-radius: 8px;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.sw:hover:not(.on) {
  border-color: var(--accent);
  color: var(--accent);
}

.sw.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #04121f;
}

.groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
  align-items: start;
}

.row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 7px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13.5px;
}

.row:last-child {
  border-bottom: none;
}

.lbl {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.val {
  font-weight: 700;
  white-space: nowrap;
}
</style>
