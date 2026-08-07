<script setup lang="ts">
import type { EffectKind } from '~/types/stock'

/**
 * Tab Cảnh báo.
 *
 * Nguyên tắc hiển thị: mức độ chắc chắn của mỗi cảnh báo phải HIỆN RÕ, không
 * để tất cả trông giống nhau. Một điều chỉnh giá ngày chốt quyền là chắc chắn;
 * một tin mới thì không nói lên hướng giá — trộn hai thứ vào cùng một kiểu
 * trình bày là làm người đọc hiểu sai.
 */
const props = defineProps<{ ticker: string }>()

const { alerts, isLoading, errorOf, loadAlerts } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:alerts`)

watch(() => props.ticker, (t) => t && loadAlerts(t), { immediate: true })

/** Nhãn nhóm cho từng mức chắc chắn — chữ chi tiết do máy chủ gửi. */
const KIND: Record<EffectKind, { icon: string; short: string }> = {
  mechanical: { icon: '⚙️', short: 'Chắc chắn' },
  observed: { icon: '📊', short: 'Đã đo được' },
  info: { icon: 'ℹ️', short: 'Thông tin' }
}

const viDate = (iso: string) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '')
  return m ? `${m[3]}/${m[2]}/${m[1]}` : ''
}
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang rà soát cảnh báo…</p>

    <template v-else-if="alerts">
      <p class="msg warn lead">{{ alerts.note }}</p>

      <article
        v-for="a in alerts.alerts"
        :key="a.key + a.date"
        class="card alert"
        :class="[`lv-border-${a.level}`, `kind-${a.effect_kind}`]"
      >
        <header class="a-head">
          <span class="a-kind">
            <span aria-hidden="true">{{ KIND[a.effect_kind].icon }}</span>
            {{ KIND[a.effect_kind].short }}
          </span>
          <span v-if="a.date" class="hint tnum">{{ viDate(a.date) }}</span>
        </header>

        <h3 class="a-title" :class="`lv-${a.level}`">{{ a.title }}</h3>
        <p class="a-detail">{{ a.detail }}</p>

        <footer class="a-foot">
          <span v-if="a.evidence" class="a-evidence">📌 {{ a.evidence }}</span>
          <span class="a-effect" :class="`eff-${a.effect_kind}`">{{ a.effect_label }}</span>
        </footer>
      </article>
    </template>

    <p v-else class="hint">Chưa có dữ liệu cảnh báo.</p>
  </div>
</template>

<style scoped>
.lead {
  margin: 0;
}

.alert {
  border-left-width: 4px;
  border-left-style: solid;
}

.lv-border-good {
  border-left-color: var(--good);
}

.lv-border-warn {
  border-left-color: var(--warn);
}

.lv-border-bad {
  border-left-color: var(--bad);
}

.a-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.a-kind {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--muted);
}

.a-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
}

.a-detail {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.a-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--line);
  font-size: 11px;
}

.a-evidence {
  color: var(--muted);
}

/* Nhãn mức chắc chắn: màu khác nhau để không ai nhầm "thông tin" với "chắc chắn" */
.a-effect {
  border-radius: 20px;
  padding: 3px 10px;
  font-weight: 700;
}

.eff-mechanical {
  background: var(--good-soft);
  color: var(--good);
}

.eff-observed {
  background: rgba(90, 200, 255, 0.16);
  color: var(--accent);
}

.eff-info {
  background: var(--warn-soft);
  color: var(--warn);
}
</style>
