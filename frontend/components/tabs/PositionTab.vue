<script setup lang="ts">
import DatePicker from '~/components/DatePicker.vue'

/** Tab Vị thế: nhập các đợt mua → đối chiếu giá vốn với điểm số và giá thị trường. */
const props = defineProps<{ ticker: string }>()

const {
  lots, accountValue, review, pending, error,
  load, addLot, removeLot, clear, saveAccount, evaluate
} = usePositionBook()

const price = ref('')
const quantity = ref('')
const date = ref('')

watch(() => props.ticker, (t) => t && load(t), { immediate: true })

const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? '—' : v.toLocaleString('vi-VN', { maximumFractionDigits: digits })

/** Hiển thị ngày kiểu Việt Nam; dữ liệu vẫn lưu dạng ISO. */
function viDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '')
  return m ? `${m[3]}/${m[2]}/${m[1]}` : 'chưa ghi ngày'
}

const signClass = (v: number | null | undefined) =>
  v === null || v === undefined ? '' : v > 0 ? 'lv-good' : v < 0 ? 'lv-bad' : 'lv-warn'

/** Màu viền theo hành động máy chủ khuyên — good/warn/bad do API quyết định. */
const actionClass = computed(() => `act-${review.value?.action.level || 'warn'}`)

const canAdd = computed(() => Number(price.value) > 0 && Number(quantity.value) > 0)

function submitLot() {
  if (!canAdd.value) return
  addLot(props.ticker, {
    price: Number(price.value),
    quantity: Number(quantity.value),
    date: date.value
  })
  price.value = ''
  quantity.value = ''
  date.value = ''
}
</script>

<template>
  <div class="tab-body">
    <section class="card">
      <h3 class="sec-title">Các đợt mua {{ ticker }}</h3>
      <p class="hint">
        Nhập từng đợt bạn đã mua. Dữ liệu lưu <b>ngay trong trình duyệt này</b> —
        không gửi lên máy chủ để lưu trữ, không đồng bộ sang máy khác.
      </p>

      <form class="lot-form" @submit.prevent="submitLot">
        <div class="fg">
          <label for="lot-price">Giá mua (nghìn đ/cp)</label>
          <input id="lot-price" v-model="price" type="number" step="0.01" min="0"
                 inputmode="decimal" placeholder="VD: 62.5" />
        </div>
        <div class="fg">
          <label for="lot-qty">Số lượng (cp)</label>
          <input id="lot-qty" v-model="quantity" type="number" step="1" min="0"
                 inputmode="numeric" placeholder="VD: 1000" />
        </div>
        <DatePicker id="lot-date" v-model="date" label="Ngày mua" placeholder="Chọn ngày mua" />
        <button class="btn primary add" type="submit" :disabled="!canAdd">Thêm đợt</button>
      </form>

      <div v-if="lots.length" class="lot-list">
        <div v-for="(l, i) in lots" :key="i" class="lot">
          <span class="lot-main">
            <b class="tnum">{{ num(l.price) }}</b>
            <span class="hint">× {{ num(l.quantity, 0) }} cp</span>
          </span>
          <span class="hint">{{ viDate(l.date) }}</span>
          <span class="tnum lot-cost">{{ num(l.price * l.quantity, 0) }} nghìn đ</span>
          <button type="button" class="del" :aria-label="`Xóa đợt mua thứ ${i + 1}`"
                  @click="removeLot(ticker, i)">✕</button>
        </div>
      </div>
      <p v-else class="hint">Chưa có đợt mua nào.</p>

      <div class="actions">
        <div class="fg acc">
          <label for="acc">Tổng vốn tài khoản (nghìn đ) — tùy chọn</label>
          <input id="acc" v-model="accountValue" type="number" step="1000" min="0"
                 inputmode="numeric" placeholder="để tính tỷ trọng vị thế"
                 @change="saveAccount(ticker)" />
        </div>
        <button class="btn primary" type="button" :disabled="!lots.length || pending"
                @click="evaluate(ticker)">
          {{ pending ? 'Đang đánh giá…' : 'Đánh giá vị thế →' }}
        </button>
        <button v-if="lots.length" class="btn" type="button" @click="clear(ticker)">Xóa hết</button>
      </div>
    </section>

    <p v-if="error" class="msg error" role="alert">{{ error }}</p>

    <template v-if="review">
      <section class="card" :class="actionClass">
        <h3 class="sec-title">Nên làm gì bây giờ?</h3>
        <p class="act-label" :class="`lv-${review.action.level}`">{{ review.action.label }}</p>
        <p class="act-reason">{{ review.action.reason }}</p>
        <p v-if="review.action.detail" class="act-detail">{{ review.action.detail }}</p>
      </section>

      <section class="card">
        <h3 class="sec-title">Vị thế của bạn</h3>
        <div class="tiles">
          <div class="tile">
            <span class="k">Giá vốn bình quân</span>
            <span class="v tnum">{{ num(review.avg_cost) }}</span>
            <span class="hint">nghìn đ/cp</span>
          </div>
          <div class="tile">
            <span class="k">Giá thị trường</span>
            <span class="v tnum">{{ num(review.current_price) }}</span>
            <span class="hint">{{ review.asof }}</span>
          </div>
          <div class="tile">
            <span class="k">Lãi / lỗ</span>
            <span class="v tnum" :class="signClass(review.pnl)">
              {{ review.pnl > 0 ? '+' : '' }}{{ num(review.pnl, 0) }}
            </span>
            <span class="hint" :class="signClass(review.pnl_pct)">
              {{ review.pnl_pct > 0 ? '+' : '' }}{{ num(review.pnl_pct) }}%
            </span>
          </div>
          <div class="tile">
            <span class="k">Ngưỡng cắt lỗ</span>
            <span class="v tnum" :class="review.stop_breached ? 'lv-bad' : ''">
              {{ num(review.stop_price) }}
            </span>
            <span class="hint" :class="review.stop_breached ? 'lv-bad' : ''">
              {{ review.stop_breached ? 'ĐÃ THỦNG' : 'chưa chạm' }}
            </span>
          </div>
          <div class="tile">
            <span class="k">Tổng số lượng</span>
            <span class="v tnum">{{ num(review.total_quantity, 0) }}</span>
            <span class="hint">cổ phiếu</span>
          </div>
          <div class="tile">
            <span class="k">Điểm của mã</span>
            <span class="v tnum" :class="`lv-${review.verdict_level}`">{{ review.score_total }}/100</span>
            <span class="hint">{{ review.verdict }}</span>
          </div>
          <div v-if="review.weight_pct !== null" class="tile">
            <span class="k">Tỷ trọng tài khoản</span>
            <span class="v tnum">{{ num(review.weight_pct) }}%</span>
            <span v-if="review.max_weight_pct" class="hint">
              trần theo điểm: {{ num(review.max_weight_pct, 0) }}%
            </span>
          </div>
        </div>
      </section>

      <section v-if="review.warnings.length" class="card warn-box">
        <h3 class="sec-title">Điều cần biết trước khi hành động</h3>
        <p v-for="(w, i) in review.warnings" :key="i" class="warn-line">⚠️ {{ w }}</p>
      </section>

      <section class="card">
        <h3 class="sec-title">Chi tiết từng đợt</h3>
        <div class="scroller">
          <table class="lots">
            <thead>
              <tr>
                <th class="lbl">Ngày</th>
                <th class="num">Giá</th>
                <th class="num">SL</th>
                <th class="num">Vốn</th>
                <th class="num">Lãi/lỗ</th>
                <th class="num">%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(l, i) in review.lots" :key="i">
                <td class="lbl">{{ l.date ? viDate(l.date) : '—' }}</td>
                <td class="num tnum">{{ num(l.price) }}</td>
                <td class="num tnum">{{ num(l.quantity, 0) }}</td>
                <td class="num tnum">{{ num(l.cost, 0) }}</td>
                <td class="num tnum" :class="signClass(l.pnl)">
                  {{ l.pnl > 0 ? '+' : '' }}{{ num(l.pnl, 0) }}
                </td>
                <td class="num tnum" :class="signClass(l.pnl_pct)">
                  {{ l.pnl_pct > 0 ? '+' : '' }}{{ num(l.pnl_pct) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="hint note">{{ review.note }}</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* Cột tường minh: repeat(auto-fit, …) đi kèm một cột `auto` ở cuối bị co về
   một cột duy nhất, khiến mỗi ô chiếm trọn một hàng. */
.lot-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(130px, 1fr)) auto;
  gap: 10px;
  align-items: end;
  margin: 12px 0;
}

.add {
  white-space: nowrap;
}

.lot-list {
  display: flex;
  flex-direction: column;
}

.lot {
  display: grid;
  grid-template-columns: 1fr auto auto 30px;
  gap: 12px;
  align-items: center;
  padding: 7px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}

.lot:last-child {
  border-bottom: none;
}

.lot-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.lot-cost {
  color: var(--muted);
  white-space: nowrap;
}

.del {
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--muted);
  border-radius: 6px;
  width: 26px;
  height: 26px;
  cursor: pointer;
  line-height: 1;
}

.del:hover {
  border-color: var(--bad);
  color: var(--bad);
}

.actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.acc {
  flex: 1;
  min-width: 220px;
}

/* Viền theo mức độ của lời khuyên — màu do máy chủ quyết định */
.act-good {
  border-color: var(--good);
}

.act-warn {
  border-color: var(--warn);
}

.act-bad {
  border-color: var(--bad);
}

.act-label {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 900;
}

.act-reason {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.55;
}

.act-detail {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--muted);
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

.warn-box {
  border-color: var(--warn);
}

.warn-line {
  margin: 0 0 8px;
  font-size: 12.5px;
  line-height: 1.6;
}

.warn-line:last-child {
  margin-bottom: 0;
}

.scroller {
  overflow: auto;
}

.lots {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.lots th,
.lots td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--line);
}

.lots thead th {
  font-size: 11.5px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.lbl {
  text-align: left;
  white-space: nowrap;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.note {
  margin: 10px 0 0;
}

@media (max-width: 767px) {
  .lot-form {
    grid-template-columns: minmax(0, 1fr);
  }

  .lot {
    grid-template-columns: 1fr auto 30px;
  }

  .lot-cost {
    display: none;
  }
}
</style>
