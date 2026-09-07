<script setup lang="ts">
import type { Mover } from '~/composables/useMarketOverview'

/**
 * Băng giá chạy ngang ở đầu trang chủ (mã sôi động thật).
 * Desktop: chạy tự động; mobile: đứng yên, cuộn ngang bằng tay.
 */
const props = defineProps<{ items: Mover[] }>()
const { num } = useFormat()

//  Nhân đôi danh sách để vòng lặp marquee không thấy chỗ nối.
const track = computed(() => [...props.items, ...props.items])
</script>

<template>
  <div v-if="items.length" class="tape" aria-hidden="true">
    <div class="tape-track">
      <span v-for="(m, i) in track" :key="m.symbol + '-' + i" class="ti">
        <b>{{ m.symbol }}</b>
        <span class="tnum px">{{ num(m.price) }}</span>
        <span v-if="m.change != null" class="tnum" :class="m.change >= 0 ? 'lv-good' : 'lv-bad'">
          {{ m.change >= 0 ? '+' : '' }}{{ num(m.change) }}%
        </span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.tape { overflow: hidden; border-bottom: 1px solid var(--line); background: rgba(10, 17, 34, 0.6);
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent); }
.tape-track { display: inline-flex; gap: 30px; padding: 8px 0; white-space: nowrap;
  animation: tape 45s linear infinite; font-size: 13px; font-family: var(--mono); }
.tape:hover .tape-track { animation-play-state: paused; }
.ti { display: inline-flex; gap: 7px; align-items: baseline; }
.ti b { color: var(--text); font-weight: 600; }
.px { color: var(--text-2); }
@keyframes tape { to { transform: translateX(-50%); } }

@media (max-width: 700px) {
  .tape { overflow-x: auto; scrollbar-width: none; mask-image: none; -webkit-mask-image: none; }
  .tape-track { animation: none; gap: 18px; padding: 6px 16px; font-size: 12.5px; }
}

@media (prefers-reduced-motion: reduce) {
  .tape-track { animation: none; }
}
</style>
