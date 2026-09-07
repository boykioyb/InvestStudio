<script setup lang="ts">
import type { ScreenerColumn, ScreenerRow } from '~/types/stock'

/**
 * Danh sách mã theo rổ, sắp xếp theo cột bất kỳ.
 *
 * Bảng dựng HOÀN TOÀN từ metadata cột do máy chủ trả về (nhãn, đơn vị, số chữ
 * số thập phân, giải thích) — trang này không đặt tên cột, không quy đổi đơn vị
 * và không sắp xếp. Bấm tiêu đề cột là gọi lại API.
 */
const { data, pending, error, group, sort, order, load, selectGroup, toggleSort } = useScreener()
const { num } = useFormat()

useHead({ title: 'Danh sách mã — Phân Tích Mã' })

onMounted(load)

/** Ô trống = nguồn không có số liệu. Cố ý hiện "—" chứ không hiện 0. */
function cell(row: ScreenerRow, column: ScreenerColumn): string {
  const value = row[column.key]
  if (value === null || value === undefined || value === '') return '—'
  if (column.type === 'text') return String(value)

  const text = num(value as number, column.digits)
  return column.signed && (value as number) > 0 ? `+${text}` : text
}

/** Máy chủ đánh dấu ô không thuộc phiên hiện tại bằng `<khóa cột>_stale`. */
function isStale(row: ScreenerRow, column: ScreenerColumn): boolean {
  return row[`${column.key}_stale`] === true
}

/** Chỉ tô màu cột có dấu; ô của phiên khác thì KHÔNG tô xanh/đỏ. */
function tone(row: ScreenerRow, column: ScreenerColumn): string {
  if (!column.signed) return ''
  if (isStale(row, column)) return 'stale'
  const value = row[column.key]
  if (typeof value !== 'number' || value === 0) return ''
  return value > 0 ? 'up' : 'down'
}

function ariaSort(column: ScreenerColumn): 'ascending' | 'descending' | 'none' {
  if (sort.value !== column.key) return 'none'
  return order.value === 'asc' ? 'ascending' : 'descending'
}

/** Bấm một dòng là mở màn hình phân tích của đúng mã đó. */
function analyze(row: ScreenerRow): void {
  void navigateTo({ path: '/phan-tich', query: { ma: row.symbol } })
}

/** Dải nhiệt: cường độ theo |change_pct| thật; ẩn khi ngoài phiên (toàn null). */
const heat = computed(() => {
  const rows = data.value?.rows || []
  const cells = rows
    .map((r) => (typeof r.change_pct === 'number' ? (r.change_pct as number) : null))
    .filter((v): v is number => v !== null)
  if (!cells.length) return null
  return cells.map((c) => {
    const a = Math.min(1, Math.abs(c) / 4)
    const col = c >= 0
      ? `rgba(46,230,166,${0.22 + a * 0.6})`
      : `rgba(255,93,115,${0.22 + a * 0.6})`
    return { pct: c, col }
  })
})
</script>

<template>
  <div class="screener">
    <AppHeader />

    <main class="stage">
      <div class="head-row">
        <h1>Danh sách mã</h1>
        <nav class="baskets" aria-label="Chọn rổ cổ phiếu">
          <button
            v-for="g in data?.groups || []"
            :key="g.key"
            type="button"
            :class="{ on: group === g.key }"
            :title="g.hint"
            :disabled="pending"
            @click="selectGroup(g.key)"
          >{{ g.label }}</button>
        </nav>
      </div>

      <p v-if="error" class="msg error" role="alert">{{ error }}</p>

      <template v-if="data">
        <div class="meta">
          <span class="live" :class="{ on: data.session.live }">{{ data.session.label }}</span>
          <span class="count tnum">{{ data.count }} mã</span>
          <span class="note">{{ data.session.note }}</span>
        </div>

        <div v-if="heat" class="heat" :title="`Độ rộng ${data.group}`">
          <i v-for="(h, i) in heat" :key="i" :style="{ background: h.col }" :title="`${h.pct}%`" />
        </div>

        <div class="board">
          <table class="grid">
            <caption class="sr-only">Danh sách rổ {{ data.group }}, sắp theo {{ sort }} {{ order }}</caption>
            <thead>
              <tr>
                <th
                  v-for="c in data.columns"
                  :key="c.key"
                  scope="col"
                  :class="[c.type, { sorted: sort === c.key }]"
                  :aria-sort="ariaSort(c)"
                >
                  <button type="button" class="sorter" :title="c.hint" @click="toggleSort(c)">
                    <span class="lb">{{ c.label }}</span>
                    <small v-if="c.unit" class="un">{{ c.unit }}</small>
                    <span class="arrow" aria-hidden="true">{{ sort === c.key ? (order === 'asc' ? '▲' : '▼') : '↕' }}</span>
                  </button>
                </th>
                <th scope="col" class="star-col"><span class="sr-only">Theo dõi</span></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in data.rows"
                :key="row.symbol"
                tabindex="0"
                class="line"
                @click="analyze(row)"
                @keydown.enter="analyze(row)"
              >
                <td
                  v-for="c in data.columns"
                  :key="c.key"
                  :class="[c.type, tone(row, c), { sym: c.key === 'symbol' }]"
                  :title="isStale(row, c) ? 'Số của phiên trước' : undefined"
                >{{ cell(row, c) }}<template v-if="isStale(row, c)">*</template></td>
                <td class="star-col" @click.stop><FavoriteButton :ticker="String(row.symbol)" compact /></td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="note foot-note">{{ data.note }}</p>
      </template>

      <p v-else-if="pending" class="note loading">Đang tải danh sách…</p>
    </main>
  </div>
</template>

<style scoped>
.screener { min-height: 100dvh; display: flex; flex-direction: column; }
.stage { max-width: 1320px; width: 100%; margin: 0 auto; padding: 20px 26px 60px; flex: 1;
  display: flex; flex-direction: column; gap: 12px; min-height: 0; }

.head-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.head-row h1 { font-size: 26px; margin: 0; font-weight: 800; }
.baskets { display: flex; gap: 7px; flex-wrap: wrap; }
.baskets button { border: 1px solid var(--line); background: var(--panel-hi); color: var(--muted);
  border-radius: 20px; padding: 7px 15px; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.15s; }
.baskets button:hover:not(:disabled):not(.on) { color: var(--text); border-color: var(--line-hi); }
.baskets button:disabled { opacity: 0.5; cursor: not-allowed; }
.baskets button.on { color: #04121f; background: linear-gradient(135deg, var(--accent), var(--accent2)); border: none; }

.meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12.5px; color: var(--muted); }
.live { border: 1px solid var(--line); border-radius: 20px; padding: 3px 10px; font-weight: 700; font-size: 11px; color: var(--muted); }
.live.on { color: var(--good); border-color: var(--good); }
.live.on::before { content: '● '; animation: pulse 2s infinite; }
@keyframes pulse { 50% { opacity: 0.4; } }
.count { font-weight: 700; color: var(--text); }

.heat { display: flex; gap: 2px; height: 9px; border-radius: 6px; overflow: hidden; }
.heat i { flex: 1; }

.board { flex: 1 1 auto; min-height: 0; overflow: auto; border: 1px solid var(--line);
  border-radius: var(--radius); background: var(--panel); backdrop-filter: blur(12px); }
.grid { width: 100%; border-collapse: collapse; font-size: 13.5px; }

thead th { position: sticky; top: 0; z-index: 1; background: rgba(15, 22, 38, 0.96); backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line-hi); padding: 0; white-space: nowrap; }
th.sorted { color: var(--accent); }
.sorter { width: 100%; display: flex; align-items: baseline; gap: 5px; background: none; border: 0;
  color: inherit; font: inherit; font-weight: 700; padding: 11px 12px; cursor: pointer;
  text-transform: uppercase; letter-spacing: 0.4px; font-size: 11px; color: var(--muted); }
th.sorted .sorter { color: var(--accent); }
th.number .sorter { justify-content: flex-end; }
.un { font-weight: 400; font-size: 10px; color: var(--muted-2); }
.arrow { font-size: 10px; opacity: 0.75; }

.line { cursor: pointer; }
.line:hover, .line:focus-visible { background: var(--panel-hi); outline: none; }
td { padding: 10px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
td.number { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }
td.text { overflow: hidden; text-overflow: ellipsis; max-width: 320px; color: var(--muted); }
td.sym { font-weight: 800; color: var(--accent); font-family: var(--sans); }
td.up { color: var(--good); }
td.down { color: var(--bad); }
td.stale { color: var(--muted); font-style: italic; }
.star-col { width: 42px; text-align: center; padding: 0 4px; }

.foot-note { margin: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 1023px) {
  th:nth-child(2), td:nth-child(2) { display: none; }
}
@media (max-width: 640px) {
  .stage { padding: 14px 12px 40px; }
  .grid { font-size: 12.5px; min-width: max-content; }
}
</style>
