<script setup lang="ts">
import type { ForeignFlow } from '~/types/stock'

/** Khối ngoại phiên hiện tại — dùng chung cho tab Giao dịch và Dòng tiền. */
defineProps<{ foreign: ForeignFlow }>()

const num = (v: number | null, digits = 0) =>
  v === null || v === undefined ? '—' : v.toLocaleString('vi-VN', { maximumFractionDigits: digits })

const signClass = (v: number | null) =>
  v === null || v === undefined ? '' : v > 0 ? 'lv-good' : v < 0 ? 'lv-bad' : 'lv-warn'
</script>

<template>
  <section class="card">
    <h3 class="sec-title">Khối ngoại — phiên hiện tại</h3>

    <div class="tiles">
      <div class="tile">
        <span class="k">Mua</span>
        <span class="v lv-good">{{ num(foreign.buy_volume) }}</span>
        <span class="hint">cp · {{ num(foreign.buy_value, 2) }} tỷ</span>
      </div>
      <div class="tile">
        <span class="k">Bán</span>
        <span class="v lv-bad">{{ num(foreign.sell_volume) }}</span>
        <span class="hint">cp · {{ num(foreign.sell_value, 2) }} tỷ</span>
      </div>
      <div class="tile">
        <span class="k">Mua ròng</span>
        <span class="v" :class="signClass(foreign.net_volume)">
          {{ foreign.net_volume !== null && foreign.net_volume > 0 ? '+' : '' }}{{ num(foreign.net_volume) }}
        </span>
        <span class="hint" :class="signClass(foreign.net_value)">
          {{ foreign.net_value !== null && foreign.net_value > 0 ? '+' : '' }}{{ num(foreign.net_value, 2) }} tỷ
        </span>
      </div>
      <div class="tile">
        <span class="k">Room còn lại</span>
        <span class="v">{{ num(foreign.room_left, 2) }}</span>
        <span class="hint">/ {{ num(foreign.room_total, 2) }} triệu cp</span>
      </div>
    </div>

    <p v-if="foreign.note" class="hint note" :class="{ stale: foreign.stale }">
      {{ foreign.note }}
    </p>

    <p class="hint note">
      Số liệu của <b>một phiên</b>, không phải xu hướng nhiều ngày — mua ròng một phiên
      chưa nói lên điều gì chắc chắn.
    </p>
  </section>
</template>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.tile {
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tile .k {
  font-size: 10.5px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--muted);
}

.tile .v {
  font-size: 19px;
  font-weight: 800;
}

.note.stale {
  color: var(--warn);
}

.note {
  margin: 10px 0 0;
}
</style>
