<script setup lang="ts">
/**
 * "Ba quy tắc thẳng thắn" — nội dung giới thiệu tĩnh.
 * Desktop: hiện đủ ba đoạn. Mobile: gập lại thành accordion cho gọn.
 */
const { RULES } = useHomeDemo()
const openIndex = ref(-1)
</script>

<template>
  <div class="rules">
    <h3 class="rules-title">Ba quy tắc thẳng thắn</h3>
    <div v-for="(r, i) in RULES" :key="r.title" class="row" :class="{ open: openIndex === i }">
      <button
        type="button"
        class="rhead"
        :aria-expanded="openIndex === i"
        @click="openIndex = openIndex === i ? -1 : i"
      >
        <span class="ic" :class="'ic-' + r.tone">{{ r.icon }}</span>
        <span class="ttl">{{ r.title }}</span>
        <span class="chev" aria-hidden="true">{{ openIndex === i ? '▴' : '▾' }}</span>
      </button>
      <p class="rbody">{{ r.body }}</p>
    </div>
  </div>
</template>

<style scoped>
.rules { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px; padding: 6px 20px; }
.rules-title { display: none; }
.row { border-bottom: 1px solid var(--line); }
.row:last-child { border-bottom: none; }
.rhead { display: grid; grid-template-columns: auto 1fr auto; gap: 14px; align-items: start;
  width: 100%; padding: 14px 0; background: none; border: none; text-align: left;
  color: var(--text); font-family: var(--sans); cursor: default; pointer-events: none; }
.ic { width: 40px; height: 40px; border-radius: 10px; display: grid; place-items: center;
  font-family: var(--mono); font-weight: 700; font-size: 13px; }
.ic-bad { background: var(--bad-soft); color: var(--bad-2); }
.ic-na { background: var(--panel-hi); border: 1px solid var(--line); color: var(--muted); }
.ic-alt { background: rgba(168, 130, 255, 0.14); color: var(--accent2-soft); }
.ttl { font-size: 15px; font-weight: 600; line-height: 1.35; align-self: center; }
.chev { display: none; color: var(--muted-2); font-size: 14px; align-self: center; }
.rbody { margin: 0 0 14px 54px; color: var(--muted); font-size: 13.5px; line-height: 1.55; }

@media (max-width: 700px) {
  .rules { padding: 0; background: none; border: none; border-radius: 0; }
  .rules-title { display: block; margin: 26px 0 6px; font-size: 16px; font-weight: 700; }
  .row { border-top: 1px solid var(--line); border-bottom: none; }
  .row:last-child { border-bottom: 1px solid var(--line); }
  .rhead { min-height: 56px; padding: 8px 0; grid-template-columns: auto 1fr auto; gap: 12px;
    cursor: pointer; pointer-events: auto; }
  .ic { width: 36px; height: 36px; border-radius: 9px; font-size: 12px; }
  .chev { display: block; }
  .rbody { display: none; margin: 0 0 14px 48px; font-size: 13.5px; }
  .row.open .rbody { display: block; }
}
</style>
