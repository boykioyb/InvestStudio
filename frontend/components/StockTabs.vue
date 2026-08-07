<script setup lang="ts">
//  Import tường minh: Nuxt tự thêm tiền tố thư mục cho component (components/tabs/
//  → "TabsProfileTab"), nên gọi bằng tên trần sẽ không resolve được.
import AlertsTab from '~/components/tabs/AlertsTab.vue'
import CapitalTab from '~/components/tabs/CapitalTab.vue'
import FinancialsTab from '~/components/tabs/FinancialsTab.vue'
import MoneyFlowTab from '~/components/tabs/MoneyFlowTab.vue'
import NewsTab from '~/components/tabs/NewsTab.vue'
import PositionTab from '~/components/tabs/PositionTab.vue'
import ProfileTab from '~/components/tabs/ProfileTab.vue'
import RatiosTab from '~/components/tabs/RatiosTab.vue'
import StatsTab from '~/components/tabs/StatsTab.vue'
import TradingTab from '~/components/tabs/TradingTab.vue'

/**
 * Khung tab cho một mã cổ phiếu.
 *
 * "Phân tích AI" là tab mặc định và nhận nội dung qua slot, nhờ vậy dashboard
 * một-màn-hình hiện có giữ nguyên markup và CSS scoped của nó trong index.vue.
 * Các tab dữ liệu chỉ tải khi được mở lần đầu (lazy) và giữ lại sau đó.
 */
const props = defineProps<{ ticker: string }>()

type TabKey =
  | 'ai' | 'alerts' | 'position' | 'trading' | 'moneyflow' | 'news' | 'profile'
  | 'capital' | 'ratios' | 'financials' | 'stats'

interface TabDef {
  key: TabKey
  label: string
}

//  Thứ tự theo yêu cầu, nhưng "Phân tích AI" đứng đầu vì là tab mặc định.
const TABS: TabDef[] = [
  { key: 'ai', label: 'Phân tích AI' },
  { key: 'alerts', label: '⚠️ Cảnh báo' },
  { key: 'position', label: 'Vị thế của tôi' },
  { key: 'trading', label: 'Giao dịch' },
  { key: 'moneyflow', label: 'Dòng tiền' },
  { key: 'news', label: 'Tin tức' },
  { key: 'profile', label: 'Hồ sơ' },
  { key: 'capital', label: 'Vốn & cổ tức' },
  { key: 'ratios', label: 'Chỉ số' },
  { key: 'financials', label: 'Tài chính' },
  { key: 'stats', label: 'Thống kê' }
]

const active = ref<TabKey>('ai')
/** Tab đã từng mở → gắn vào DOM và giữ lại, tránh gọi mạng lặp. */
const visited = ref<Set<TabKey>>(new Set<TabKey>(['ai']))

watch(active, (key) => visited.value = new Set(visited.value).add(key))
//  Đổi mã thì quay về tab mặc định cho khỏi lạc.
watch(() => props.ticker, () => {
  active.value = 'ai'
  visited.value = new Set<TabKey>(['ai'])
})

const tabRefs = ref<HTMLButtonElement[]>([])

/** Điều hướng bằng phím mũi tên theo chuẩn tablist. */
function onKey(event: KeyboardEvent, index: number): void {
  const last = TABS.length - 1
  let next: number | null = null
  if (event.key === 'ArrowRight') next = index === last ? 0 : index + 1
  else if (event.key === 'ArrowLeft') next = index === 0 ? last : index - 1
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = last
  if (next === null) return

  event.preventDefault()
  active.value = TABS[next].key
  nextTick(() => tabRefs.value[next as number]?.focus())
}
</script>

<template>
  <div class="tabs">
    <div class="strip" role="tablist" aria-label="Các mục phân tích">
      <button
        v-for="(t, i) in TABS"
        :key="t.key"
        :ref="(el) => { if (el) tabRefs[i] = el as HTMLButtonElement }"
        type="button"
        role="tab"
        class="tab"
        :class="{ on: active === t.key }"
        :aria-selected="active === t.key"
        :aria-controls="`panel-${t.key}`"
        :id="`tab-${t.key}`"
        :tabindex="active === t.key ? 0 : -1"
        @click="active = t.key"
        @keydown="onKey($event, i)"
      >
        {{ t.label }}
      </button>
    </div>

    <div
      v-for="t in TABS"
      v-show="active === t.key"
      :key="t.key"
      :id="`panel-${t.key}`"
      role="tabpanel"
      :aria-labelledby="`tab-${t.key}`"
      class="panel"
      :class="{ 'panel-ai': t.key === 'ai' }"
    >
      <template v-if="visited.has(t.key)">
        <slot v-if="t.key === 'ai'" />
        <AlertsTab v-else-if="t.key === 'alerts'" :ticker="ticker" />
        <PositionTab v-else-if="t.key === 'position'" :ticker="ticker" />
        <TradingTab v-else-if="t.key === 'trading'" :ticker="ticker" />
        <MoneyFlowTab v-else-if="t.key === 'moneyflow'" :ticker="ticker" />
        <NewsTab v-else-if="t.key === 'news'" :ticker="ticker" />
        <ProfileTab v-else-if="t.key === 'profile'" :ticker="ticker" />
        <CapitalTab v-else-if="t.key === 'capital'" :ticker="ticker" />
        <RatiosTab v-else-if="t.key === 'ratios'" :ticker="ticker" />
        <FinancialsTab v-else-if="t.key === 'financials'" :ticker="ticker" />
        <StatsTab v-else-if="t.key === 'stats'" :ticker="ticker" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Cuộn ngang thay vì xuống dòng thành nhiều hàng — quan trọng trên màn hẹp */
.strip {
  display: flex;
  gap: 4px;
  flex: none;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
  border-bottom: 1px solid var(--line);
  padding-bottom: 4px;
}

.strip::-webkit-scrollbar {
  display: none;
}

.tab {
  flex: none;
  border: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  border-radius: 8px 8px 0 0;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

.tab:hover:not(.on) {
  color: var(--accent);
}

.tab.on {
  background: var(--panel);
  border-color: var(--line);
  border-bottom-color: var(--panel);
  color: var(--text);
}

.tab:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Tab dữ liệu tự cuộn bên trong để trang vẫn không cuộn ở desktop */
.panel:not(.panel-ai) {
  overflow: auto;
}

.panel :deep(.tab-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 6px;
}

@media (max-width: 767px) {
  .tab {
    padding: 10px 14px;
    font-size: 14px;
    min-height: 44px;
  }

  .panel:not(.panel-ai) {
    overflow: visible;
  }
}
</style>
