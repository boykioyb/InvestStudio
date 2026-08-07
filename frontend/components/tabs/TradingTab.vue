<script setup lang="ts">
/** Tab Giao dịch: ảnh chụp bảng giá phiên hiện tại + sổ lệnh 3 mức + khối ngoại. */
const props = defineProps<{ ticker: string }>()

const { board, isLoading, errorOf, loadBoard } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:board`)

watch(() => props.ticker, (t) => t && loadBoard(t), { immediate: true })

const num = (v: number | null, digits = 2) =>
  v === null || v === undefined ? '—' : v.toLocaleString('vi-VN', { maximumFractionDigits: digits })

/** Màu theo tương quan với giá tham chiếu — quy ước bảng giá Việt Nam. */
function priceClass(price: number | null): string {
  const b = board.value
  if (!b || price === null || b.reference === null) return ''
  if (b.ceiling !== null && price >= b.ceiling) return 'lv-good'
  if (b.floor !== null && price <= b.floor) return 'lv-bad'
  if (price > b.reference) return 'lv-good'
  if (price < b.reference) return 'lv-bad'
  return 'lv-warn'
}
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải bảng giá…</p>

    <template v-else-if="board">
      <section class="card">
        <header class="head">
          <h3 class="sec-title">Bảng giá phiên hiện tại</h3>
          <span v-if="board.asof" class="hint">Cập nhật {{ board.asof }}</span>
        </header>

        <div class="tiles">
          <div class="tile">
            <span class="k">Giá khớp</span>
            <span class="v" :class="priceClass(board.match_price)">{{ num(board.match_price) }}</span>
            <span v-if="board.change !== null" class="hint" :class="priceClass(board.match_price)">
              {{ board.change > 0 ? '+' : '' }}{{ num(board.change) }}
              ({{ board.change_pct !== null && board.change_pct > 0 ? '+' : '' }}{{ num(board.change_pct) }}%)
            </span>
          </div>
          <div class="tile">
            <span class="k">Tham chiếu</span>
            <span class="v lv-warn">{{ num(board.reference) }}</span>
          </div>
          <div class="tile">
            <span class="k">Trần / Sàn</span>
            <span class="v small">
              <span class="lv-good">{{ num(board.ceiling) }}</span>
              <span class="hint"> / </span>
              <span class="lv-bad">{{ num(board.floor) }}</span>
            </span>
          </div>
          <div class="tile">
            <span class="k">Mở / Cao / Thấp</span>
            <span class="v small">{{ num(board.open) }} · {{ num(board.high) }} · {{ num(board.low) }}</span>
          </div>
          <div class="tile">
            <span class="k">KL khớp</span>
            <span class="v">{{ num(board.match_volume, 0) }}</span>
            <span class="hint">cổ phiếu</span>
          </div>
          <div class="tile">
            <span class="k">Giá bình quân</span>
            <span class="v">{{ num(board.avg_price) }}</span>
          </div>
        </div>
        <p class="hint note">{{ board.note }}</p>
      </section>

      <section class="card">
        <h3 class="sec-title">Sổ lệnh — 3 mức giá tốt nhất</h3>
        <div class="depth">
          <div class="side">
            <span class="side-title lv-good">Dư mua</span>
            <div v-for="(b, i) in board.bids" :key="'b' + i" class="lvl">
              <span class="lvl-price lv-good tnum">{{ num(b.price) }}</span>
              <span class="lvl-vol tnum">{{ num(b.volume, 0) }}</span>
            </div>
            <p v-if="!board.bids.length" class="hint">Không có dữ liệu dư mua.</p>
          </div>
          <div class="side">
            <span class="side-title lv-bad">Dư bán</span>
            <div v-for="(a, i) in board.asks" :key="'a' + i" class="lvl">
              <span class="lvl-price lv-bad tnum">{{ num(a.price) }}</span>
              <span class="lvl-vol tnum">{{ num(a.volume, 0) }}</span>
            </div>
            <p v-if="!board.asks.length" class="hint">Không có dữ liệu dư bán.</p>
          </div>
        </div>
      </section>

      <ForeignFlowCard v-if="board.foreign" :foreign="board.foreign" />
    </template>

    <p v-else class="hint">Chưa có dữ liệu bảng giá.</p>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.head .sec-title {
  margin: 0;
}

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

.tile .v.small {
  font-size: 14px;
}

.note {
  margin: 10px 0 0;
}

.depth {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.side-title {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.lvl {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13.5px;
}

.lvl:last-child {
  border-bottom: none;
}

.lvl-price {
  font-weight: 700;
}

.lvl-vol {
  color: var(--muted);
}
</style>
