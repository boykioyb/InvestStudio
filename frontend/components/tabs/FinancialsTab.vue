<script setup lang="ts">
import type { StatementKey } from '~/types/stock'

/** Tab Tài chính: 3 báo cáo theo năm. Số liệu đã được máy chủ quy về tỷ đồng. */
const props = defineProps<{ ticker: string }>()

const STATEMENTS: { key: StatementKey; label: string }[] = [
  { key: 'income', label: 'Kết quả kinh doanh' },
  { key: 'balance', label: 'Cân đối kế toán' },
  { key: 'cashflow', label: 'Lưu chuyển tiền tệ' }
]

const kind = ref<StatementKey>('income')
const { statement, isLoading, errorOf, loadStatement } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:fin:${kind.value}`)

watch([() => props.ticker, kind], ([t, k]) => t && loadStatement(t, k), { immediate: true })

/** Chỉ định dạng hiển thị, không đổi giá trị (backend đã làm tròn). */
function money(value: number | null): string {
  if (value === null || value === undefined) return '—'
  return value.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="tab-body">
    <div class="switcher" role="group" aria-label="Chọn báo cáo">
      <button
        v-for="s in STATEMENTS"
        :key="s.key"
        type="button"
        class="sw"
        :class="{ on: kind === s.key }"
        :aria-pressed="kind === s.key"
        @click="kind = s.key"
      >
        {{ s.label }}
      </button>
    </div>

    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải báo cáo…</p>

    <section v-else-if="statement" class="card">
      <header class="head">
        <h3 class="sec-title">{{ statement.title }}</h3>
        <span class="hint">Đơn vị: <b>{{ statement.unit }}</b></span>
      </header>

      <div class="scroller">
        <table class="fin">
          <thead>
            <tr>
              <th class="lbl">Chỉ tiêu</th>
              <th v-for="p in statement.periods" :key="p" class="num">{{ p }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in statement.rows" :key="r.label">
              <td class="lbl" :title="r.label">{{ r.label }}</td>
              <td
                v-for="(v, i) in r.values"
                :key="i"
                class="num tnum"
                :class="{ neg: v !== null && v < 0 }"
              >
                {{ money(v) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="statement.note" class="hint note">{{ statement.note }}</p>
    </section>

    <p v-else class="hint">Chưa có dữ liệu báo cáo.</p>
  </div>
</template>

<style scoped>
.switcher {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
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

/* Loại trừ .on để chữ không trùng màu nền khi rê chuột vào mục đang chọn */
.sw:hover:not(.on) {
  border-color: var(--accent);
  color: var(--accent);
}

.sw.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #04121f;
}

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

/* Bảng dài (cân đối kế toán 121 dòng) → cuộn trong khung, tiêu đề dính trên */
.scroller {
  max-height: 62vh;
  overflow: auto;
}

.fin {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.fin th,
.fin td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}

.fin thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--panel);
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.lbl {
  text-align: left;
  min-width: 190px;
}

.num {
  text-align: right;
  white-space: nowrap;
}

td.num {
  font-weight: 600;
}

td.num.neg {
  color: var(--bad);
}

.note {
  margin: 10px 0 0;
}

@media (max-width: 767px) {
  .fin {
    font-size: 12px;
  }

  .lbl {
    min-width: 150px;
  }

  .scroller {
    max-height: none;
  }
}
</style>
