<script setup lang="ts">
import type { BestHorizon, Decision, Horizon } from '~/types/stock'

/** Cột phải: hợp khung thời gian nào + nếu mua thì làm thế nào. */
defineProps<{
  horizons: Horizon[]
  bestHorizon?: BestHorizon | null
  decision: Decision
}>()

const { textClass, fillClass } = useLevel()
</script>

<template>
  <section class="card panel">
    <h2 class="sec-title">Hợp với tầm nhìn nào?</h2>

    <div class="horizons">
      <div v-for="h in horizons" :key="h.key" class="hz" :class="{ best: h.key === bestHorizon?.key }">
        <div class="hz-top">
          <span class="hz-label">
            <span v-if="h.key === bestHorizon?.key" class="star" aria-label="phù hợp nhất">★</span>
            <span class="hz-label-text">{{ h.label }}</span>
            <!-- Chỉ hiện khi máy chủ có gửi lời giải thích. -->
            <InfoPopover :explain="h.explain" :label="h.label" />
          </span>
          <span class="hz-val tnum" :class="textClass(h.level)">{{ h.value }}<span class="muted">/100</span></span>
        </div>
        <span class="track" aria-hidden="true">
          <span class="fill" :class="fillClass(h.level)" :style="{ width: `${h.value}%` }" />
        </span>
        <span class="hz-fit" :class="textClass(h.level)">{{ h.fit }}</span>
      </div>
    </div>

    <h2 class="sec-title mt">Nếu mua thì làm thế nào?</h2>

    <div class="dboxes">
      <div class="dbox">
        <span class="k" title="Tối đa bao nhiêu phần trăm tài khoản nên dồn vào mã này.">
          Quy mô vị thế
        </span>
        <span class="v">{{ decision.position_size }}</span>
      </div>
      <div class="dbox">
        <span class="k" title="Mức lỗ tối đa chấp nhận trước khi bán để bảo toàn vốn.">
          Cắt lỗ kỷ luật
        </span>
        <span class="v lv-bad">{{ decision.stop_loss }}</span>
      </div>
    </div>

    <p class="line">
      <span class="k">Thời điểm</span>
      <span>{{ decision.timing }}</span>
    </p>

    <!-- Kịch bản xấu nhất: nói thẳng con số thay vì bảo người dùng tự hỏi -->
    <section class="worst">
      <div class="worst-head">
        <h3 class="worst-title">⚠️ Kịch bản xấu nhất</h3>
        <div v-if="decision.worst_case.stop_price !== null" class="worst-stats">
          <span class="ws">
            <span class="ws-k">Chạm cắt lỗ tại</span>
            <span class="ws-v lv-bad tnum">{{ decision.worst_case.stop_price }}</span>
          </span>
          <span class="ws">
            <span class="ws-k">Thiệt hại</span>
            <span class="ws-v lv-bad">{{ decision.worst_case.account_loss }}</span>
          </span>
        </div>
      </div>

      <p class="worst-text">{{ decision.worst_case.narrative }}</p>

      <ul class="risks">
        <li v-for="risk in decision.worst_case.risks" :key="risk.label" class="risk">
          <span class="risk-label">{{ risk.label }}</span>
          <span class="risk-detail">{{ risk.detail }}</span>
        </li>
      </ul>
    </section>

    <p class="note-line">{{ decision.note }}</p>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 14px;
  overflow: auto;
}

.sec-title {
  margin: 0 0 8px;
}

.sec-title.mt {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.horizons {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: none;
}

.hz-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.hz-label {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  color: var(--muted);
}

.hz-label-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hz.best .hz-label {
  color: var(--text);
  font-weight: 700;
}

.star {
  color: var(--accent);
}

.hz-val {
  font-size: 12px;
  font-weight: 700;
}

.hz-val .muted {
  font-weight: 500;
}

.track {
  display: block;
  height: 8px;
  margin: 4px 0 2px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}

.fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.hz-fit {
  font-size: 10.5px;
  font-weight: 600;
}

.dboxes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.dbox {
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 8px 10px;
}

.k {
  display: block;
  font-size: 10px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--muted);
}

.dbox .v {
  display: block;
  margin-top: 2px;
  font-size: 15px;
  font-weight: 800;
}

.line {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.45;
}

.line .k {
  margin-bottom: 2px;
}

.worst {
  margin: 11px 0 0;
  padding: 9px 11px;
  border-left: 3px solid var(--bad);
  border-radius: 8px;
  background: rgba(255, 107, 125, 0.07);
}

.worst-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.worst-title {
  margin: 0;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--bad);
}

.worst-stats {
  display: flex;
  gap: 12px;
}

.ws {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.ws-k {
  font-size: 9.5px;
  color: var(--muted);
}

.ws-v {
  font-size: 13px;
  font-weight: 800;
}

.worst-text {
  margin: 6px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
}

.risks {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.risk {
  font-size: 11px;
  line-height: 1.45;
  padding-left: 9px;
  border-left: 2px solid var(--line);
}

.risk-label {
  font-weight: 700;
  color: var(--warn);
}

.risk-label::after {
  content: ' — ';
  color: var(--muted);
  font-weight: 400;
}

.risk-detail {
  color: var(--muted);
}

.note-line {
  margin: auto 0 0;
  padding-top: 10px;
  font-size: 11px;
  color: var(--muted);
}
</style>
