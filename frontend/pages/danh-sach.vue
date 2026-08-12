<script setup lang="ts">
import { List, Search } from 'lucide-vue-next'
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

useHead({ title: 'Danh sách mã — InvestStudio' })

onMounted(load)

/** Ô trống = nguồn không có số liệu. Cố ý hiện "—" chứ không hiện 0. */
function cell(row: ScreenerRow, column: ScreenerColumn): string {
  const value = row[column.key]
  if (value === null || value === undefined || value === '') return '—'
  if (column.type === 'text') return String(value)

  const text = num(value as number, column.digits)
  return column.signed && (value as number) > 0 ? `+${text}` : text
}

/**
 * Máy chủ đánh dấu ô không thuộc phiên hiện tại bằng trường `<khóa cột>_stale`.
 * Quy ước theo TÊN nên không phải viết riêng cho từng cột.
 */
function isStale(row: ScreenerRow, column: ScreenerColumn): boolean {
  return row[`${column.key}_stale`] === true
}

/**
 * Chỉ tô màu cột có dấu. Ô mang dữ liệu của phiên khác thì KHÔNG tô xanh/đỏ —
 * tô lên sẽ bị đọc thành dòng tiền của hôm nay.
 */
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
  void navigateTo({ path: '/', query: { ma: row.symbol } })
}
</script>

<template>
  <div class="app">
    <header class="bar">
      <h1 class="brand"><List /> Danh sách mã</h1>

      <nav class="chips" aria-label="Chọn rổ cổ phiếu">
        <button
          v-for="g in data?.groups || []"
          :key="g.key"
          type="button"
          class="chip"
          :class="{ on: group === g.key }"
          :title="g.hint"
          :disabled="pending"
          @click="selectGroup(g.key)"
        >
          {{ g.label }}
        </button>
      </nav>

      <NuxtLink to="/" class="chip link"><Search /> Phân tích mã</NuxtLink>
    </header>

    <p v-if="error" class="msg error" role="alert">{{ error }}</p>

    <template v-if="data">
      <div class="meta">
        <span class="badge" :class="{ live: data.session.live }">{{ data.session.label }}</span>
        <span class="count">{{ data.count }} mã</span>
        <span class="note">{{ data.session.note }}</span>
      </div>

      <div class="board">
        <table class="grid">
          <caption class="sr-only">
            Danh sách mã rổ {{ data.group }}, đang sắp xếp theo {{ sort }} {{ order }}
          </caption>
          <thead>
            <tr>
              <th
                v-for="c in data.columns"
                :key="c.key"
                scope="col"
                :class="[c.type, { active: sort === c.key }]"
                :aria-sort="ariaSort(c)"
              >
                <button type="button" class="sorter" :title="c.hint" @click="toggleSort(c)">
                  <span class="lb">{{ c.label }}</span>
                  <small v-if="c.unit" class="un">{{ c.unit }}</small>
                  <span class="arrow" aria-hidden="true">
                    {{ sort === c.key ? (order === 'asc' ? '▲' : '▼') : '↕' }}
                  </span>
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
                :title="isStale(row, c) ? 'Số của phiên trước — nguồn chưa xóa khi mở phiên mới' : undefined"
              >
                {{ cell(row, c) }}<template v-if="isStale(row, c)">*</template>
              </td>
              <td class="star-col"><FavoriteButton :ticker="row.symbol" compact /></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="msg warn">{{ data.note }}</p>
    </template>

    <p v-else-if="pending" class="hint">Đang tải danh sách…</p>
  </div>
</template>

<style scoped>
.app {
  height: 100dvh;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  overflow: hidden;
}

.bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: none;
}

.brand {
  margin: 0;
  font-size: 17px;
  white-space: nowrap;
}

.chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.chip {
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}

/*  :not(.on) để trạng thái hover không đè mất màu của nút đang chọn. */
.chip:hover:not(:disabled):not(.on) {
  border-color: var(--accent);
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chip.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #0b1020;
}

.chip.link {
  margin-left: auto;
}

.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--muted);
  flex: none;
}

.badge {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 10px;
  font-weight: 700;
  color: var(--muted);
}

.badge.live {
  border-color: var(--good);
  color: var(--good);
}

.count {
  font-weight: 700;
  color: var(--text);
}

.note {
  min-width: 0;
}

/*  Cố ý KHÔNG đặt tên .wrap / .row: main.css đã có hai utility class trùng tên
    (.row là flex container, .wrap có padding + max-width). Scoped style không
    chặn được CSS toàn cục, nên trùng tên là dòng bảng vỡ layout ngay. */
.board {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
}

.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--panel2);
  border-bottom: 1px solid var(--line);
  padding: 0;
  white-space: nowrap;
}

th.active {
  color: var(--accent);
}

.sorter {
  width: 100%;
  display: flex;
  align-items: baseline;
  gap: 5px;
  background: none;
  border: 0;
  color: inherit;
  font: inherit;
  font-weight: 700;
  padding: 9px 10px;
  cursor: pointer;
}

th.number .sorter {
  justify-content: flex-end;
}

.un {
  font-weight: 400;
  font-size: 10.5px;
  color: var(--muted);
}

.arrow {
  font-size: 10px;
  opacity: 0.75;
}

.line {
  cursor: pointer;
}

.line:hover,
.row:focus-visible {
  background: var(--panel2);
  outline: none;
}

td {
  padding: 7px 10px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

td.number {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

td.text {
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}

td.sym {
  font-weight: 800;
  color: var(--accent);
}

td.up {
  color: var(--good);
}

td.down {
  color: var(--bad);
}

/*  Ô của phiên khác: xám và nghiêng, kèm dấu * — nhìn là biết không phải hôm nay. */
td.stale {
  color: var(--muted);
  font-style: italic;
}

.star-col {
  width: 42px;
  text-align: center;
  padding: 0 4px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/*  Máy tính bảng trở xuống: bỏ cột Tên công ty — nó ngốn chiều ngang nhất mà
    ít người cần, các cột số vẫn còn đủ. */
@media (max-width: 1023px) {
  th:nth-child(2),
  td:nth-child(2) {
    display: none;
  }
}

/*  Điện thoại: KHÔNG ẩn thêm cột nào nữa. Cột bị ẩn thì tiêu đề của nó cũng
    biến mất, tức là mất luôn khả năng sắp xếp theo cột đó — nên để bảng cuộn
    ngang trong khung. Trang vẫn không tràn vì .wrap tự cuộn. */
@media (max-width: 640px) {
  .app {
    padding: 8px;
  }

  .brand {
    font-size: 15px;
  }

  .chip.link {
    margin-left: 0;
  }

  .grid {
    font-size: 12.5px;
    /*  Không cho co lại thành cột chữ xuống dòng lộn xộn. */
    min-width: max-content;
  }

  td,
  .sorter {
    padding-left: 8px;
    padding-right: 8px;
  }
}
</style>
