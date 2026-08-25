<script setup lang="ts">
import type { Mover } from '~/composables/useMarketOverview'

/** Danh sách mã (tăng/giảm/sôi động) trên trang Home. Bấm → mở phân tích mã. */
defineProps<{ items: Mover[]; showPrice?: boolean }>()
const { num } = useFormat()

function open(code: string): void {
  void navigateTo({ path: '/phan-tich', query: { ma: code } })
}
</script>

<template>
  <div v-if="items.length" class="mv-list">
    <button v-for="m in items" :key="m.symbol" type="button" class="mv" @click="open(m.symbol)">
      <span class="sym">{{ m.symbol }}</span>
      <span class="nm">{{ m.name }}</span>
      <span class="vals">
        <span v-if="showPrice" class="px tnum">{{ num(m.price) }}</span>
        <span v-if="m.change != null" class="chg tnum" :class="m.change >= 0 ? 'lv-good' : 'lv-bad'">
          {{ m.change >= 0 ? '▲ +' : '▼ ' }}{{ num(m.change) }}%
        </span>
      </span>
    </button>
  </div>
  <p v-else class="hint">Chưa có dữ liệu.</p>
</template>

<style scoped>
.mv-list { display: flex; flex-direction: column; }
.mv { display: grid; grid-template-columns: 58px 1fr auto; gap: 10px; align-items: center;
  padding: 9px 4px; border: none; border-bottom: 1px solid var(--line); background: none;
  color: var(--text); cursor: pointer; text-align: left; font-family: var(--sans); transition: background 0.12s; }
.mv:last-child { border-bottom: none; }
.mv:hover { background: var(--panel-hi); border-radius: 8px; }
.sym { font-weight: 800; color: var(--accent); }
.nm { color: var(--muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* Giá + % gộp một cột bên phải, xếp dọc canh phải → không rớt dòng. */
.vals { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; white-space: nowrap; }
.px { font-size: 13px; }
.chg { font-size: 12px; }
</style>
