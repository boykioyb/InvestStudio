<script setup lang="ts">
/**
 * Ba khối điểm nhấn dưới phần thị trường: lịch sự kiện sắp tới, tin công bố mới
 * và bảng điểm cao nhất của rổ. Dữ liệu thật từ `/api/market/highlights`.
 *
 * Cả ba mảng có thể rỗng → mỗi cột tự hiện "Chưa có dữ liệu". Gọi lỗi thì ẩn
 * toàn khối, trang vẫn dùng bình thường.
 * Desktop: ba cột. Mobile: gộp thành tab.
 */
const props = defineProps<{ group: string }>()

//  Tin có link ngoài → thẻ <a>; không có link → mở phân tích mã trong app.
const NuxtLinkComp = resolveComponent('NuxtLink')

const { pending, failed, events, news, leaders, load } = useMarketHighlights()
const tab = ref(0)

//  Ngày ISO -> "10" + "Th9" cho ô lịch (chỉ là định dạng hiển thị).
const day = (iso: string): string => iso.slice(8, 10) || '—'
const mon = (iso: string): string => {
  const m = Number(iso.slice(5, 7))
  return Number.isFinite(m) && m ? `Th${m}` : ''
}
const shortDate = (iso: string): string => {
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}` : iso
}

onMounted(() => void load(props.group))
watch(() => props.group, (g) => void load(g))
</script>

<template>
  <section v-if="!failed" class="highlights">
    <div class="mhead">
      <h2>Sắp tới &amp; mới nhất</h2>
      <p>Lịch cổ tức, tin công bố và bảng điểm sau phiên.</p>
    </div>
    <div class="tabs" role="tablist">
      <button
        v-for="(t, i) in ['Sự kiện', 'Tin công bố', `Điểm ${group}`]" :key="t" type="button" role="tab"
        :aria-selected="i === tab" :class="{ on: i === tab }" @click="tab = i"
      >{{ t }}</button>
    </div>

    <div class="cols">
      <!-- lịch sự kiện -->
      <div class="col" :class="{ on: tab === 0 }">
        <h3 class="sec-title">Lịch sự kiện sắp tới · cổ tức &amp; ĐHCĐ</h3>
        <LoadingState v-if="pending" />
        <div v-else-if="events.length" class="rows">
          <NuxtLink
            v-for="e in events" :key="e.date + e.symbol + e.kind"
            :to="{ path: '/analysis', query: { symbol: e.symbol } }" class="row ev"
          >
            <span class="cal tnum"><span class="d">{{ day(e.date) }}</span><span class="m">{{ mon(e.date) }}</span></span>
            <span class="sym tnum">{{ e.symbol }}</span>
            <span class="txt">
              <span class="kind" :class="'lv-' + e.level">{{ e.kind }}</span>
              <span class="muted"> · {{ e.detail }}</span>
            </span>
          </NuxtLink>
        </div>
        <p v-else class="hint">Chưa có dữ liệu.</p>
      </div>

      <!-- tin công bố -->
      <div class="col" :class="{ on: tab === 1 }">
        <h3 class="sec-title">Tin công bố mới · {{ group }}</h3>
        <LoadingState v-if="pending" />
        <div v-else-if="news.length" class="rows">
          <component
            :is="n.url ? 'a' : NuxtLinkComp"
            v-for="n in news" :key="n.symbol + n.title"
            v-bind="n.url
              ? { href: n.url, target: '_blank', rel: 'noopener noreferrer' }
              : { to: { path: '/analysis', query: { symbol: n.symbol } } }"
            class="row nw"
          >
            <span class="sym tnum">{{ n.symbol }}</span>
            <span class="txt">
              <span class="ttl">{{ n.title }}</span>
              <span class="meta"><span class="tnum">{{ shortDate(n.date) }}</span><span v-if="n.url"> · nguồn ↗</span></span>
            </span>
          </component>
        </div>
        <p v-else class="hint">Chưa có dữ liệu.</p>
      </div>

      <!-- bảng điểm -->
      <div class="col" :class="{ on: tab === 2 }">
        <div class="lead-head">
          <h3 class="sec-title">Điểm cao nhất {{ group }}</h3>
          <span class="hint">chấm lại sau mỗi phiên</span>
        </div>
        <LoadingState v-if="pending" />
        <template v-else-if="leaders.length">
          <div class="rows">
            <NuxtLink
              v-for="l in leaders" :key="l.symbol"
              :to="{ path: '/analysis', query: { symbol: l.symbol } }" class="row ld"
            >
              <span class="sym tnum">{{ l.symbol }}</span>
              <span class="track"><span class="fill" :style="{ width: l.score + '%' }" /></span>
              <span class="score tnum">{{ l.score }}<span class="muted">/100</span></span>
            </NuxtLink>
          </div>
          <NuxtLink to="/screener" class="all">Xem cả bảng {{ group }} →</NuxtLink>
        </template>
        <p v-else class="hint">Chưa có dữ liệu.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.highlights { max-width: 1320px; margin: 0 auto; padding: 16px 26px 0; }
/* Tiêu đề chỉ cần trên mobile — desktop khối này nối tiếp phần thị trường. */
.mhead { display: none; }
.tabs { display: none; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 16px; }
.col { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 18px; min-width: 0; }
.lead-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.lead-head .sec-title { margin-bottom: 8px; }

.rows { display: flex; flex-direction: column; }
.row { display: grid; gap: 10px; align-items: center; min-height: 44px; padding: 8px 6px;
  border-bottom: 1px solid var(--line); text-decoration: none; color: var(--text); border-radius: 8px; }
.row:last-child { border-bottom: none; }
.row:hover { background: var(--panel-hi); }
.row.ev { grid-template-columns: auto 58px 1fr; }
.row.nw { grid-template-columns: 58px 1fr; align-items: start; }
.row.ld { grid-template-columns: 58px 1fr auto; }
.sym { font-weight: 700; color: var(--accent); }
.cal { display: flex; flex-direction: column; align-items: center; min-width: 42px;
  background: var(--panel-deep); border: 1px solid var(--line); border-radius: 8px;
  padding: 4px 6px; line-height: 1.15; }
.cal .d { font-size: 15px; font-weight: 700; }
.cal .m { font-size: 10px; color: var(--muted); }
.txt { min-width: 0; font-size: 13px; line-height: 1.45; }
.kind { font-weight: 600; }
.ttl { display: block; }
.meta { display: block; font-size: 11.5px; color: var(--muted-2); margin-top: 2px; }
.track { display: block; height: 6px; border-radius: 3px; background: rgba(120, 140, 190, 0.2); overflow: hidden; }
.fill { display: block; height: 100%; border-radius: 3px; background: var(--accent); }
.score { font-weight: 700; color: var(--accent); }
.score .muted { font-weight: 500; font-size: 11px; }
.all { display: flex; align-items: center; justify-content: center; min-height: 44px; margin-top: 12px;
  text-decoration: none; border: 1px solid var(--line); background: var(--panel-deep); color: var(--text);
  border-radius: 10px; padding: 0 16px; font-size: 13.5px; font-weight: 600; }
.all:hover { border-color: var(--accent); color: var(--accent); }
.col :deep(.loading-state) { min-height: 120px; }

@media (max-width: 700px) {
  .highlights { padding: 28px 16px 0; }
  .mhead { display: block; }
  .mhead h2 { margin: 0 0 4px; font-size: 20px; font-weight: 700; letter-spacing: -0.3px; line-height: 1.25; }
  .mhead p { margin: 0 0 14px; font-size: 13.5px; color: var(--muted); line-height: 1.5; }
  .tabs { display: flex; gap: 4px; padding: 4px; background: var(--panel-deep);
    border: 1px solid var(--line); border-radius: 12px; margin-bottom: 6px; }
  .tabs button { flex: 1; min-height: 44px; border: none; border-radius: 9px; background: none;
    color: var(--muted); font-size: 13.5px; font-weight: 500; cursor: pointer;
    font-family: var(--sans); white-space: nowrap; padding: 0 6px; }
  .tabs button.on { background: var(--accent); color: var(--on-accent); font-weight: 700; }
  .cols { display: block; }
  .col { background: none; border: none; border-radius: 0; padding: 0; display: none; }
  .col.on { display: block; }
}
</style>
