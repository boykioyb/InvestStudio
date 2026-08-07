<script setup lang="ts">
import type { EventItem } from '~/types/stock'

/** Tab Vốn & cổ tức: cổ tức, phát hành thêm, giao dịch nội bộ. */
const props = defineProps<{ ticker: string }>()

const { actions, isLoading, errorOf, loadActions } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:actions`)

watch(() => props.ticker, (t) => t && loadActions(t), { immediate: true })

const num = (v: number | null, digits = 2) =>
  v === null || v === undefined ? '' : v.toLocaleString('vi-VN', { maximumFractionDigits: digits })

/** Các mốc ngày quan trọng của một sự kiện, chỉ hiện mốc nào có thật. */
function dates(e: EventItem): { label: string; value: string }[] {
  return [
    { label: 'Ngày chốt quyền', value: e.exright_date },
    { label: 'Ngày đăng ký cuối', value: e.record_date },
    { label: 'Ngày thanh toán', value: e.payout_date }
  ].filter((d) => d.value)
}
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải sự kiện doanh nghiệp…</p>

    <template v-else-if="actions">
      <section v-if="actions.dividends.length" class="card">
        <h3 class="sec-title">Cổ tức tiền mặt ({{ actions.dividends.length }})</h3>
        <article v-for="(e, i) in actions.dividends" :key="'d' + i" class="event">
          <div class="ev-head">
            <span class="ev-title">{{ e.title || e.name }}</span>
            <span class="ev-date tnum">{{ e.date }}</span>
          </div>
          <div class="ev-meta">
            <span v-if="e.value_per_share" class="chip-val lv-good">
              {{ num(e.value_per_share, 0) }} đ/cp
            </span>
            <span v-if="e.ratio" class="chip-val">Tỷ lệ {{ num(e.ratio) }}%</span>
            <span v-for="d in dates(e)" :key="d.label" class="hint">
              {{ d.label }}: <b>{{ d.value }}</b>
            </span>
          </div>
        </article>
      </section>

      <section v-if="actions.issues.length" class="card">
        <h3 class="sec-title">Phát hành thêm & niêm yết bổ sung ({{ actions.issues.length }})</h3>
        <article v-for="(e, i) in actions.issues" :key="'i' + i" class="event">
          <div class="ev-head">
            <span class="ev-title">{{ e.title || e.name }}</span>
            <span class="ev-date tnum">{{ e.date }}</span>
          </div>
          <div class="ev-meta">
            <span v-if="e.ratio" class="chip-val lv-warn">Tỷ lệ {{ num(e.ratio) }}%</span>
            <span v-for="d in dates(e)" :key="d.label" class="hint">
              {{ d.label }}: <b>{{ d.value }}</b>
            </span>
          </div>
        </article>
        <p class="hint note">
          Phát hành thêm làm <b>tăng số cổ phiếu lưu hành</b> — phần sở hữu của bạn bị
          pha loãng nếu không được mua theo tỷ lệ.
        </p>
      </section>

      <section v-if="actions.insider.length" class="card">
        <h3 class="sec-title">Giao dịch nội bộ ({{ actions.insider.length }})</h3>
        <article v-for="(e, i) in actions.insider" :key="'n' + i" class="event compact">
          <div class="ev-head">
            <span class="ev-title">{{ e.title || e.name }}</span>
            <span class="ev-date tnum">{{ e.date }}</span>
          </div>
          <span v-if="e.action" class="chip-val" :class="e.action === 'Mua' ? 'lv-good' : 'lv-bad'">
            {{ e.action }}
          </span>
        </article>
        <p class="hint note">{{ actions.note }}</p>
      </section>

      <section v-if="actions.others.length" class="card">
        <h3 class="sec-title">Sự kiện khác ({{ actions.others.length }})</h3>
        <article v-for="(e, i) in actions.others" :key="'o' + i" class="event compact">
          <div class="ev-head">
            <span class="ev-title">{{ e.title || e.name }}</span>
            <span class="ev-date tnum">{{ e.date }}</span>
          </div>
        </article>
      </section>
    </template>

    <p v-else class="hint">Chưa có dữ liệu sự kiện.</p>
  </div>
</template>

<style scoped>
.event {
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
}

.event:last-of-type {
  border-bottom: none;
}

.ev-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  font-size: 13.5px;
}

.ev-title {
  min-width: 0;
}

.ev-date {
  flex: none;
  color: var(--muted);
  font-size: 12px;
}

.ev-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 5px;
  font-size: 11.5px;
}

.chip-val {
  border: 1px solid var(--line);
  background: var(--panel2);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 11.5px;
  font-weight: 700;
}

.event.compact .chip-val {
  margin-top: 5px;
  display: inline-block;
}

.note {
  margin: 10px 0 0;
}
</style>
