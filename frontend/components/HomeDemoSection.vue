<script setup lang="ts">
/**
 * Khối minh hoạ "màn phân tích thu gọn" của trang chủ (VÍ DỤ tĩnh, mã FPT).
 *
 * Bên trái: vòng điểm + 4 nhóm tiêu chí + biểu đồ giá theo khung + tầm nhìn +
 * kịch bản xấu. Bên phải: bảng 14 tiêu chí của nhóm đang chọn + ba quy tắc.
 * Toàn bộ số liệu là hằng số trong `useHomeDemo` — client không chấm điểm.
 */
const { GROUPS, HORIZONS, RANGES, series, paths } = useHomeDemo()
const { num } = useFormat()

const DEMO_SCORE = 81
const DEMO_LAST = 71.4
/** chu vi vòng tròn r = 52 → dùng cho stroke-dasharray/offset */
const RING = 326.73

const activeGroup = ref(0)
const rangeKey = ref('1Q')
/** Mobile gập phần biểu đồ/tầm nhìn lại; desktop luôn mở (CSS lo). */
const detailOpen = ref(false)
const shown = ref(0)

const group = computed(() => GROUPS[activeGroup.value])
const range = computed(() => RANGES.find((r) => r.key === rangeKey.value) ?? RANGES[1])
const spark = computed(() => paths(series(range.value.n, range.value.lo, range.value.hi, DEMO_LAST)))
const dashoffset = computed(() => (RING * (1 - shown.value / 100)).toFixed(2))
const rangeChg = computed(() => range.value.chg.replace('.', ','))
const pct = (a: number, b: number): string => `${Math.round((a / b) * 100)}%`

//  Vòng điểm đếm lên khi vào trang; tôn trọng người tắt hiệu ứng.
let raf = 0
onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    shown.value = DEMO_SCORE
    return
  }
  const t0 = performance.now()
  const step = (t: number): void => {
    const p = Math.min(1, (t - t0) / 1200)
    shown.value = DEMO_SCORE * (1 - Math.pow(1 - p, 3))
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
})
onUnmounted(() => cancelAnimationFrame(raf))
</script>

<template>
  <section class="demo">
    <div class="grid">
      <!-- ===== màn phân tích thu gọn ===== -->
      <div class="panel card-plain">
        <div class="phead">
          <span class="kicker">Màn phân tích thu gọn · FPT <b class="demo-tag">ví dụ</b></span>
          <span class="tnum muted">24/08/2026</span>
        </div>
        <div class="pbody">
          <div class="top">
            <div class="ring" role="img" :aria-label="`Điểm ${DEMO_SCORE} trên 100`">
              <svg viewBox="0 0 120 120">
                <circle class="ring-bg" cx="60" cy="60" r="52" fill="none" stroke-width="11" />
                <circle
                  class="ring-fg" cx="60" cy="60" r="52" fill="none" stroke-width="11"
                  stroke-linecap="round" transform="rotate(-90 60 60)"
                  :stroke-dasharray="RING" :stroke-dashoffset="dashoffset"
                />
              </svg>
              <div class="ring-val">
                <span class="s tnum lv-good">{{ Math.round(shown) }}</span>
                <span class="m tnum muted">/100</span>
              </div>
            </div>
            <div class="gbars">
              <button
                v-for="(g, i) in GROUPS" :key="g.name" type="button" class="gbar"
                :class="{ on: i === activeGroup }" @click="activeGroup = i"
              >
                <span class="gn">{{ g.name }}</span>
                <span class="gv tnum" :class="'lv-' + g.level">{{ g.sum }}<span class="muted">/{{ g.max }}</span></span>
                <span class="track"><span class="fill" :class="'bg-' + g.level" :style="{ width: pct(g.sum, g.max) }" /></span>
              </button>
            </div>
          </div>

          <button type="button" class="detail-toggle" :aria-expanded="detailOpen" @click="detailOpen = !detailOpen">
            {{ detailOpen ? 'Thu gọn chi tiết' : 'Xem chi tiết biểu đồ & tầm nhìn' }}
            <span aria-hidden="true">{{ detailOpen ? '▴' : '▾' }}</span>
          </button>

          <div class="detail" :class="{ open: detailOpen }">
            <div class="ranges" role="group" aria-label="Khung thời gian biểu đồ">
              <button
                v-for="r in RANGES" :key="r.key" type="button"
                :class="{ on: r.key === rangeKey }" :aria-pressed="r.key === rangeKey"
                @click="rangeKey = r.key"
              >{{ r.key }}</button>
            </div>
            <svg class="spark" viewBox="0 0 600 140" preserveAspectRatio="none" role="img" aria-label="Diễn biến giá FPT">
              <defs>
                <linearGradient id="home-spark" x1="0" y1="0" x2="0" y2="1">
                  <stop class="g0" offset="0%" />
                  <stop class="g1" offset="100%" />
                </linearGradient>
              </defs>
              <line class="axis" x1="10" y1="126" x2="590" y2="126" vector-effect="non-scaling-stroke" />
              <path class="sk-area" :d="spark.area" fill="url(#home-spark)" />
              <path
                class="sk-line" :d="spark.line" fill="none" stroke-width="2"
                stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"
              />
              <line
                class="sk-halo" :x1="spark.lastX" :y1="spark.lastY" :x2="spark.lastX" :y2="spark.lastY"
                stroke-width="12" stroke-linecap="round" vector-effect="non-scaling-stroke"
              />
              <line
                class="sk-dot" :x1="spark.lastX" :y1="spark.lastY" :x2="spark.lastX" :y2="spark.lastY"
                stroke-width="8" stroke-linecap="round" vector-effect="non-scaling-stroke"
              />
            </svg>
            <div class="rstats">
              <span>Thấp nhất <b class="tnum">{{ num(range.lo) }}</b></span>
              <span>Cao nhất <b class="tnum">{{ num(range.hi) }}</b></span>
              <span>{{ range.label }}:
                <b class="tnum" :class="rangeChg.startsWith('-') ? 'lv-bad' : 'lv-good'">{{ rangeChg }}</b>
              </span>
              <span class="tnum sessions">{{ range.n }} phiên</span>
            </div>

            <div class="horizons">
              <div v-for="h in HORIZONS" :key="h.label" class="hz" :class="{ best: h.best }">
                <div class="hz-top">
                  <span class="hz-l">{{ h.best ? '★ ' : '' }}{{ h.label }}</span>
                  <span class="tnum lv-good">{{ h.value }}<span class="muted">/100</span></span>
                </div>
                <span class="track"><span class="fill bg-good" :style="{ width: h.value + '%' }" /></span>
                <span class="hz-note lv-good">Phù hợp cao</span>
              </div>
            </div>

            <div class="worst">
              <div class="worst-top">
                <span class="wt">Kịch bản xấu nhất</span>
                <span class="wnums">
                  <span><span class="k">Chạm cắt lỗ tại</span><span class="v tnum">65,69</span></span>
                  <span><span class="k">Thiệt hại</span><span class="v">≈ <span class="tnum">1,6%</span> tài khoản</span></span>
                </span>
              </div>
              <p>
                Bạn mua ở giá 71,4, giá quay đầu và chạm cắt lỗ 8% tại 65,69 nghìn đ/cp. Nếu đã dồn
                mức tối đa 20% tài khoản, bạn mất khoảng 1,6% tổng tài khoản trong lần này.
              </p>
            </div>
          </div>

          <div class="ctas">
            <NuxtLink :to="{ path: '/phan-tich', query: { ma: 'FPT' } }" class="cta-main">Mở phân tích đầy đủ FPT →</NuxtLink>
            <NuxtLink to="/theo-doi" class="cta-alt">☆ Theo dõi FPT <span class="muted">· cần đăng nhập</span></NuxtLink>
          </div>
        </div>
      </div>

      <!-- ===== 14 tiêu chí + ba quy tắc ===== -->
      <div class="right">
        <div class="panel card-plain pad">
          <h3 class="kicker">Điểm 81 của FPT đến từ đâu?</h3>
          <p class="intro">
            100 điểm chia cho 4 nhóm theo trọng số cố định — mọi mã đều được đo bằng cùng một thước.
            Chạm vào từng nhóm để xem tiêu chí bên trong.
          </p>
          <div class="segs" role="tablist">
            <button
              v-for="(g, i) in GROUPS" :key="g.name" type="button" role="tab"
              :aria-selected="i === activeGroup" :title="g.name" :style="{ flex: g.max }"
              :class="{ on: i === activeGroup }" @click="activeGroup = i"
            >{{ g.max }}</button>
          </div>
          <div class="ghead">
            <span class="gname">{{ group.name }}</span>
            <span class="gsum">FPT đạt <b class="tnum">{{ group.sum }}</b><span class="tnum">/{{ group.max }}</span></span>
          </div>
          <div class="items">
            <div v-for="it in group.items" :key="it.label" class="item">
              <span class="il">{{ it.label }}</span>
              <span class="ir tnum" :class="'lv-' + it.level">{{ it.raw }}</span>
              <span class="track"><span class="fill" :class="'bg-' + it.level" :style="{ width: pct(it.points, it.max) }" /></span>
              <span class="ip tnum" :class="'lv-' + it.level">{{ it.points }}<span class="muted">/{{ it.max }}</span></span>
            </div>
          </div>
          <p class="note">{{ group.note }}</p>
          <div class="scale tnum">
            <span><b class="lv-good">≥80</b> xuất sắc</span>
            <span><b class="lv-good">65–79</b> tốt</span>
            <span><b class="lv-warn">50–64</b> trung bình</span>
            <span><b class="lv-bad">&lt;50</b> yếu</span>
          </div>
        </div>

        <HomePrinciples />
      </div>
    </div>
  </section>
</template>

<style scoped>
.demo { max-width: 1320px; margin: 0 auto; padding: 48px 26px 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
  gap: 16px; align-items: start; }
.right { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.card-plain { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px; min-width: 0; }
.card-plain.pad { padding: 20px; }
.kicker { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin: 0; }
.demo-tag { color: var(--warn); font-weight: 700; }

.panel { overflow: hidden; }
.phead { display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 12px 16px; border-bottom: 1px solid var(--line); font-size: 12px; }
.pbody { padding: 16px; }
.top { display: flex; align-items: center; gap: 16px; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
.ring { position: relative; width: 110px; height: 110px; flex: none; }
.ring svg { width: 100%; height: 100%; display: block; }
.ring-val { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-val .s { font-size: 34px; font-weight: 700; line-height: 1; }
.ring-val .m { font-size: 11px; }

.gbars { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.gbar { display: grid; grid-template-columns: 1fr auto; gap: 3px 10px; align-items: center;
  background: none; border: none; padding: 2px 0; cursor: pointer; text-align: left;
  font-family: var(--sans); color: var(--text); opacity: 0.6; transition: opacity 0.2s; border-radius: 6px; }
.gbar:hover, .gbar.on { opacity: 1; }
.gn { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gv { font-size: 12px; font-weight: 700; }
.track { grid-column: 1 / -1; display: block; height: 5px; border-radius: 3px;
  background: rgba(120, 140, 190, 0.2); overflow: hidden; }
.fill { display: block; height: 100%; border-radius: 3px; }

/* nút gập chi tiết: chỉ có nghĩa trên mobile */
.detail-toggle { display: none; }

.ranges { display: flex; align-items: center; gap: 4px; margin-top: 14px; }
.ranges button { flex: 1; min-height: 36px; border: 1px solid var(--line); background: var(--panel-deep);
  color: var(--muted); border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--sans); }
.ranges button.on { border-color: var(--accent); background: var(--accent); color: var(--on-accent); }
.ring-bg { stroke: rgba(30, 42, 70, 0.9); }
.ring-fg { stroke: var(--good); }
.spark { display: block; width: 100%; height: 120px; margin-top: 8px; }
/* Màu SVG khai báo bằng CSS (thuộc tính presentation không hiểu var()). */
.spark .g0 { stop-color: var(--accent); stop-opacity: 0.22; }
.spark .g1 { stop-color: var(--accent); stop-opacity: 0; }
.spark .axis { stroke: var(--line); }
.spark .sk-line { stroke: var(--accent); }
.spark .sk-halo { stroke: var(--panel-solid); }
.spark .sk-dot { stroke: var(--accent); }
.rstats { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12.5px; color: var(--muted); margin-top: 6px; }
.rstats b { color: var(--text); font-weight: 600; }
.rstats .sessions { margin-left: auto; }

.horizons { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
  gap: 8px; margin-top: 14px; }
.hz { background: var(--panel-deep); border: 1px solid var(--line); border-radius: 10px; padding: 10px; }
.hz.best { border-color: rgba(168, 130, 255, 0.5); }
.hz-top { display: flex; justify-content: space-between; gap: 6px; font-size: 11.5px; color: var(--muted); }
.hz-l { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hz.best .hz-l { color: var(--text); font-weight: 600; }
.hz .track { grid-column: auto; height: 6px; margin: 7px 0 5px; }
.hz-note { font-size: 11.5px; font-weight: 600; }

.worst { margin-top: 12px; padding: 12px 14px; border: 1px solid rgba(255, 93, 115, 0.35);
  border-left: 4px solid var(--bad); border-radius: 10px; background: rgba(255, 93, 115, 0.06); }
.worst-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.wt { font-size: 11.5px; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; color: var(--bad-2); }
.wnums { display: flex; gap: 16px; white-space: nowrap; }
.wnums > span { display: flex; flex-direction: column; align-items: flex-end; }
.wnums .k { font-size: 10.5px; color: var(--muted); }
.wnums .v { font-size: 14px; font-weight: 700; color: var(--bad-2); }
.worst p { margin: 6px 0 0; font-size: 12.5px; line-height: 1.55; color: var(--text-2); }

.ctas { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.cta-main { flex: 1; min-width: 180px; display: inline-flex; align-items: center; justify-content: center;
  min-height: 44px; text-decoration: none; background: var(--accent); color: var(--on-accent);
  border-radius: 10px; padding: 0 16px; font-size: 14px; font-weight: 700; }
.cta-main:hover { background: var(--accent-hi); }
.cta-alt { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px;
  text-decoration: none; border: 1px solid var(--line); background: var(--panel-deep); color: var(--text);
  border-radius: 10px; padding: 0 14px; font-size: 13.5px; font-weight: 600; white-space: nowrap; }
.cta-alt:hover { border-color: var(--accent); color: var(--accent); }
.cta-alt .muted { font-size: 12px; font-weight: 400; }

/* ----- bảng tiêu chí ----- */
.intro { margin: 6px 0 16px; font-size: 14.5px; color: var(--text-2); line-height: 1.55; text-wrap: pretty; }
.segs { display: flex; gap: 3px; height: 40px; border-radius: 9px; overflow: hidden; }
.segs button { border: none; cursor: pointer; background: rgba(30, 42, 70, 0.9); color: var(--muted);
  font-family: var(--mono); font-size: 13px; font-weight: 700; transition: background 0.2s; min-width: 0; }
.segs button:hover { filter: brightness(1.15); }
.segs button.on { background: var(--accent); color: var(--on-accent); }
.ghead { display: flex; justify-content: space-between; gap: 10px; margin: 12px 0 14px; flex-wrap: wrap; }
.gname { font-size: 13px; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.4px; }
.gsum { font-size: 13px; color: var(--muted); white-space: nowrap; }
.gsum b { color: var(--text); }
.items { display: flex; flex-direction: column; gap: 10px; }
.item { display: grid; grid-template-columns: minmax(100px, 1.1fr) minmax(90px, 1fr) minmax(60px, 2fr) auto;
  gap: 10px; align-items: center; font-size: 13px; }
.il { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ir { font-weight: 600; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item .track { grid-column: auto; height: 7px; border-radius: 4px; }
.ip { font-weight: 700; }
.note { margin: 16px 0 0; font-size: 12.5px; color: var(--muted); line-height: 1.55; }
.scale { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 14px; padding-top: 12px;
  border-top: 1px solid var(--line); font-size: 12.5px; color: var(--muted); }

@media (max-width: 700px) {
  .demo { padding: 22px 16px 0; }
  .grid { gap: 22px; }
  .right { gap: 22px; }
  .card-plain.pad { padding: 16px 14px; }
  .pbody { padding: 14px; }
  .phead { padding: 10px 14px; }
  .ring { width: 88px; height: 88px; }
  .ring-val .s { font-size: 26px; }

  /* mobile: gập biểu đồ + tầm nhìn + kịch bản xấu lại cho ngắn trang */
  .detail-toggle { display: flex; width: 100%; min-height: 48px; margin-top: 12px;
    align-items: center; justify-content: center; gap: 8px; background: none;
    border: 1px solid rgba(90, 200, 255, 0.45); color: var(--accent); border-radius: 10px;
    font-size: 14px; font-weight: 600; cursor: pointer; font-family: var(--sans); }
  .detail { display: none; }
  .detail.open { display: block; margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--line-hi); }
  .ranges button { min-height: 44px; font-size: 13px; }
  .spark { height: 140px; }
  .rstats .sessions { margin-left: 0; }
  .ctas { flex-direction: column; }
  .cta-main, .cta-alt { min-height: 48px; width: 100%; }
  .item { grid-template-columns: 1fr auto; gap: 2px 10px; padding: 9px 0;
    border-bottom: 1px solid var(--line); }
  .items { gap: 0; }
  .il { font-size: 14px; color: var(--text); }
  .ir { grid-row: 2; grid-column: 1; }
  .item .track { grid-row: 2; grid-column: 2; max-width: 120px; }
  .ip { grid-row: 1; grid-column: 2; }
}
</style>
