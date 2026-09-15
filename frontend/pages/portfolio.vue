<script setup lang="ts">
import type { PortfolioRow } from '~/composables/usePortfolio'

/** Tổng quan danh mục: lãi/lỗ toàn bộ vị thế → bấm vào từng mã để xem chi tiết. */
const { data, pending, error, isEmpty, synced, load } = usePortfolio()
const { num, money } = useFormat()
const { isLoggedIn, user } = useAuth()

const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

//  Nạp khi mở, và nạp lại khi quay lại tab (vừa đồng bộ xong bên TCInvest thì
//  chuyển sang tab này sẽ tự thấy danh mục mới, khỏi F5).
onMounted(() => {
  void load()
  if (import.meta.client) {
    const onVisible = () => { if (document.visibilityState === 'visible') void load() }
    document.addEventListener('visibilitychange', onVisible)
    onBeforeUnmount(() => document.removeEventListener('visibilitychange', onVisible))
  }
})
useHead({ title: 'Danh mục — Phân Tích Mã' })

//  Token để extension TCBS đẩy danh mục về (tạo khi đã đăng nhập trên web).
const importToken = ref('')
const tokenErr = ref('')
const tokenPending = ref(false)
const copied = ref(false)

//  Nhập đợt mua đã đồng bộ (server) vào "Vị thế của tôi" (localStorage).
const { importFromServer } = usePositionBook()
const importingLots = ref(false)
const lotsMsg = ref('')
async function importLots(): Promise<void> {
  importingLots.value = true
  lotsMsg.value = ''
  try {
    const r = await importFromServer()
    lotsMsg.value = r.lots
      ? `Đã nhập ${r.lots} đợt mua của ${r.tickers} mã vào "Vị thế của tôi".`
      : 'Chưa có đợt khớp nào được đồng bộ — bấm "Đồng bộ danh mục" trên extension trước.'
    await load()
  } catch {
    lotsMsg.value = 'Không nhập được đợt mua. Thử lại sau.'
  } finally {
    importingLots.value = false
  }
}

async function genToken(): Promise<void> {
  tokenPending.value = true
  tokenErr.value = ''
  try {
    const r = await $fetch<{ token: string; expires_days: number }>(
      `${apiBase}/api/portfolio/import-token`, { method: 'POST', credentials: 'include' })
    importToken.value = r.token
  } catch (e) {
    tokenErr.value = (e as { data?: { detail?: string } })?.data?.detail
      || 'Không tạo được token. Hãy đăng nhập rồi thử lại.'
  } finally {
    tokenPending.value = false
  }
}

async function copyToken(): Promise<void> {
  try {
    await navigator.clipboard.writeText(importToken.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch { /* trình duyệt chặn clipboard — người dùng tự chọn + copy */ }
}

function fmtDate(s: string | null): string {
  if (!s) return ''
  try { return new Date(s).toLocaleString('vi-VN') } catch { return s }
}

const sign = (v: number | null | undefined) =>
  v == null ? '' : v > 0 ? 'lv-good' : v < 0 ? 'lv-bad' : 'lv-na'
const withSign = (v: number | null | undefined) => (v != null && v > 0 ? '+' : '')

function open(row: PortfolioRow): void {
  void navigateTo({ path: '/analysis', query: { symbol: row.ticker } })
}
</script>

<template>
  <div class="portfolio">
    <AppHeader />

    <main class="stage">
      <div class="head-row">
        <h1>Danh mục của tôi</h1>
        <span v-if="data" class="pill" :class="data.in_session ? 'good' : 'warn'">
          {{ data.in_session ? 'Giá khớp trong phiên' : 'Giá tham chiếu (ngoài phiên)' }}
        </span>
      </div>

      <!-- Kết nối TCInvest (TCBS) để đồng bộ danh mục -->
      <details class="card sync-card" :open="!synced">
        <summary>
          <span class="sync-title">Đồng bộ từ TCInvest (TCBS)</span>
          <span v-if="synced" class="pill good">
            Đã đồng bộ {{ synced.count }} mã{{ synced.account ? ' · ' + synced.account : '' }}
          </span>
          <span v-else class="pill warn">Chưa kết nối</span>
        </summary>
        <div class="sync-body">
          <p v-if="synced" class="hint">
            Đã đồng bộ vào tài khoản <b>{{ user?.email }}</b>{{ synced.account ? ' · tiểu khoản ' + synced.account : '' }},
            cập nhật lúc {{ fmtDate(synced.updated_at) }} từ {{ synced.source }}. Danh mục này chỉ bạn thấy. Bấm vào từng mã để xem điểm.
          </p>
          <template v-if="isLoggedIn">
            <p class="hint">
              Cài extension <code>tools/tcinvest-capture</code>, tạo token dưới đây rồi dán vào extension —
              nó sẽ tự lấy cổ phiếu bạn đang giữ trên TCInvest và đẩy về đây.
            </p>
            <div class="token-row">
              <button class="btn" :disabled="tokenPending" @click="genToken">
                {{ tokenPending ? 'Đang tạo…' : 'Tạo token đồng bộ' }}
              </button>
              <input v-if="importToken" class="token-input" :value="importToken" readonly
                     @focus="(e) => (e.target as HTMLInputElement).select()">
              <button v-if="importToken" class="btn" @click="copyToken">
                {{ copied ? 'Đã copy ✓' : 'Copy' }}
              </button>
            </div>
            <p v-if="importToken" class="hint small">
              Token dùng được 30 ngày, chỉ để đẩy danh mục (không đăng nhập được). Đổi mật khẩu là token hết hiệu lực.
            </p>
            <p v-if="tokenErr" class="msg error">{{ tokenErr }}</p>

            <div class="token-row" style="margin-top:4px">
              <button class="btn" :disabled="importingLots" @click="importLots">
                {{ importingLots ? 'Đang nhập…' : 'Nhập đợt mua vào Vị thế của tôi' }}
              </button>
            </div>
            <p v-if="lotsMsg" class="hint small">{{ lotsMsg }}</p>
          </template>
          <p v-else class="hint">
            Bạn cần <NuxtLink to="/login">đăng nhập</NuxtLink> để tạo token đồng bộ.
          </p>
        </div>
      </details>

      <p v-if="error" class="msg error" role="alert">{{ error }}</p>

      <!-- rỗng -->
      <div v-else-if="isEmpty" class="empty card">
        <p class="empty-title">Chưa có vị thế nào</p>
        <p class="hint">
          Vào một mã → tab <b>“Vị thế của tôi”</b> để nhập các đợt mua. Dữ liệu lưu
          ngay trong trình duyệt này, tổng hợp sẽ hiện ở đây.
        </p>
        <NuxtLink to="/screener" class="btn primary">Khám phá danh sách mã →</NuxtLink>
      </div>

      <p v-else-if="pending && !data" class="note loading">Đang tổng hợp danh mục…</p>

      <template v-else-if="data">
        <!-- thẻ tổng -->
        <section class="tiles">
          <div class="card tile">
            <span class="k">Tổng vốn</span>
            <span class="v tnum">{{ money(data.totals.total_cost) }} đ</span>
          </div>
          <div class="card tile">
            <span class="k">Giá trị thị trường</span>
            <span class="v tnum">{{ money(data.totals.market_value) }} đ</span>
          </div>
          <div class="card tile hero" :class="sign(data.totals.pnl)">
            <span class="k">Tổng lãi / lỗ</span>
            <span class="v big tnum">{{ withSign(data.totals.pnl) }}{{ money(data.totals.pnl) }} đ</span>
            <span class="sub tnum" :class="sign(data.totals.pnl_pct)">
              {{ withSign(data.totals.pnl_pct) }}{{ num(data.totals.pnl_pct) }}%
            </span>
          </div>
          <div class="card tile">
            <span class="k">Số mã</span>
            <span class="v tnum">{{ data.totals.positions }}</span>
            <span class="sub">
              <span class="lv-good">{{ data.totals.winners }} lãi</span> ·
              <span class="lv-bad">{{ data.totals.losers }} lỗ</span>
            </span>
          </div>
        </section>

        <!-- bảng chi tiết -->
        <section class="card table-card">
          <div class="scroller">
            <table class="grid">
              <thead>
                <tr>
                  <th class="l">Mã</th>
                  <th>SL</th>
                  <th>Giá vốn BQ</th>
                  <th>Giá TT</th>
                  <th>Vốn (đ)</th>
                  <th>Lãi/lỗ (đ)</th>
                  <th>%</th>
                  <th v-if="synced" title="Lãi/lỗ đã chốt (bán) — đồng bộ từ TCBS">Lãi/lỗ đã TH</th>
                  <th>Tỷ trọng</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in data.rows" :key="row.ticker" tabindex="0"
                    @click="open(row)" @keydown.enter="open(row)">
                  <td class="l">
                    <span class="sym">{{ row.ticker }}</span>
                    <span class="nm">{{ row.name }}</span>
                  </td>
                  <td class="tnum">{{ num(row.quantity, 0) }}</td>
                  <td class="tnum">{{ num(row.avg_cost) }}</td>
                  <td class="tnum">
                    {{ num(row.current_price) }}<span v-if="row.price_is_ref" class="ref" title="Giá tham chiếu (ngoài phiên)">*</span>
                  </td>
                  <td class="tnum">{{ money(row.total_cost) }}</td>
                  <td class="tnum" :class="sign(row.pnl)">{{ withSign(row.pnl) }}{{ money(row.pnl) }}</td>
                  <td class="tnum" :class="sign(row.pnl_pct)">{{ withSign(row.pnl_pct) }}{{ num(row.pnl_pct) }}%</td>
                  <td v-if="synced" class="tnum" :class="sign(row.realized_pnl)">
                    {{ row.realized_pnl != null ? withSign(row.realized_pnl) + money(row.realized_pnl) : '—' }}
                  </td>
                  <td class="tnum">{{ row.weight_pct != null ? num(row.weight_pct) + '%' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="note foot">{{ data.note }}</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.portfolio { min-height: 100dvh; }
.stage { max-width: 1320px; margin: 0 auto; padding: 20px 26px 60px; display: flex; flex-direction: column; gap: 16px; }
.head-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.head-row h1 { font-size: 26px; margin: 0; font-weight: 800; }

.empty { text-align: center; padding: 40px 20px; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.empty-title { font-size: 18px; font-weight: 700; margin: 0; }
.empty .hint { max-width: 460px; }
.empty .btn { margin-top: 8px; text-decoration: none; }
.loading { padding: 30px 0; }

.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 0; }
.tile { margin: 0; display: flex; flex-direction: column; gap: 4px; }
.tile .k { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
.tile .v { font-size: 22px; font-weight: 800; }
.tile .v.big { font-size: 26px; }
.tile .sub { font-size: 12.5px; color: var(--muted); }
.tile.hero.lv-good { border-color: var(--good); }
.tile.hero.lv-bad { border-color: var(--bad); }

.sync-card { margin: 0; padding: 0; }
.sync-card > summary { list-style: none; cursor: pointer; padding: 14px 16px; display: flex;
  align-items: center; gap: 12px; }
.sync-card > summary::-webkit-details-marker { display: none; }
.sync-title { font-weight: 700; }
.sync-body { padding: 0 16px 16px; display: flex; flex-direction: column; gap: 8px; }
.sync-body code { background: var(--panel-hi); padding: 1px 6px; border-radius: 5px; font-size: 12px; }
.token-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.token-input { flex: 1; min-width: 220px; font-family: ui-monospace, monospace; font-size: 12px;
  padding: 8px 10px; border: 1px solid var(--line-hi); border-radius: 8px; background: var(--panel-hi);
  color: inherit; }
.hint.small { font-size: 12px; color: var(--muted); }

.table-card { margin: 0; padding: 6px 6px 10px; }
.scroller { overflow: auto; }
.grid { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.grid th { text-align: right; padding: 10px 12px; font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.4px; color: var(--muted); border-bottom: 1px solid var(--line-hi); white-space: nowrap; }
.grid th.l { text-align: left; }
.grid td { text-align: right; padding: 11px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.grid td.l { text-align: left; }
.grid tbody tr { cursor: pointer; transition: background 0.12s; }
.grid tbody tr:hover, .grid tbody tr:focus-visible { background: var(--panel-hi); outline: none; }
.grid tbody tr:last-child td { border-bottom: none; }
.sym { font-weight: 800; color: var(--accent); }
.nm { color: var(--muted); font-size: 11.5px; margin-left: 8px; }
.ref { color: var(--muted); margin-left: 1px; }
.foot { margin: 8px 12px 0; }

@media (max-width: 900px) {
  .tiles { grid-template-columns: 1fr 1fr; }
  .nm { display: none; }
}
@media (max-width: 560px) { .tiles { grid-template-columns: 1fr; } }
</style>
