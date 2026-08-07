<script setup lang="ts">
import type { ScoreCategory } from '~/types/stock'

/**
 * Bảng 14 tiêu chí ở dạng DÀY ĐẶC — gộp "chỉ số chính" và "bảng điểm chi tiết"
 * làm một để vừa trọn một màn hình.
 *
 * Thuần trình bày: bề rộng thanh = points/max, màu lấy từ useLevel().
 * KHÔNG có ngưỡng hay công thức tính điểm ở đây (xem backend/services/scoring.py).
 */
defineProps<{ categories: ScoreCategory[] }>()

const { itemTextClass, itemFillClass } = useLevel()
const { glossFor } = useGlossary()
</script>

<template>
  <section class="card panel">
    <header class="panel-head">
      <h2 class="sec-title">Chi tiết 14 tiêu chí</h2>
      <span class="hint">Điểm mỗi tiêu chí do máy chủ chấm · <b>N/A</b> = chưa lấy được dữ liệu</span>
    </header>

    <div class="groups">
      <article v-for="group in categories" :key="group.name" class="group">
        <div class="group-head">
          <span class="group-name">{{ group.name }}</span>
          <span class="group-score tnum">{{ group.sum }}/{{ group.max }}</span>
        </div>

        <div
          v-for="item in group.items"
          :key="item.label"
          class="crit"
          :class="{ na: !item.available }"
        >
          <span class="crit-label">
            <span class="crit-label-text" :title="glossFor(item.label) || undefined">
              {{ item.label }}
            </span>
            <!-- Chỉ hiện khi máy chủ có gửi lời giải thích. -->
            <InfoPopover :explain="item.explain" :label="item.label" />
          </span>

          <span class="crit-raw" :class="itemTextClass(item.level, item.available)">{{ item.raw }}</span>

          <span class="crit-track" aria-hidden="true">
            <span
              class="crit-fill"
              :class="itemFillClass(item.level, item.available)"
              :style="{ width: `${item.max ? (item.points / item.max) * 100 : 0}%` }"
            />
          </span>

          <span class="crit-pts tnum" :class="itemTextClass(item.level, item.available)">
            {{ item.points }}<span class="muted">/{{ item.max }}</span>
          </span>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 14px;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.panel-head .sec-title {
  margin: 0;
}

/* Một cột, trải đều hết chiều cao — dễ đọc hơn là dồn cụm ở trên */
.groups {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 2px;
  min-height: 0;
  overflow: auto;
}

.group {
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  flex: 1 1 auto;
  min-height: 0;
}

.group-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin: 2px 0 4px;
  padding-bottom: 4px;
  border-bottom: 1px dashed var(--line);
}

.group-name {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--accent);
}

.group-score {
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.crit {
  display: grid;
  grid-template-columns: minmax(110px, 0.9fr) minmax(0, 1fr) minmax(90px, 1.6fr) 54px;
  align-items: center;
  gap: 14px;
  padding: 5px 0;
  font-size: 13.5px;
  line-height: 1.35;
}

/* Nhãn + nút ⓘ: nút cố định 16px, phần chữ vẫn tự cắt bớt như cũ. */
.crit-label {
  display: flex;
  align-items: center;
  gap: 3px;
  min-width: 0;
  color: var(--muted);
}

.crit-label-text {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crit-raw {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crit-track {
  height: 7px;
  border-radius: 3px;
  background: var(--line);
  overflow: hidden;
}

.crit-fill {
  display: block;
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.crit-pts {
  font-size: 13px;
  font-weight: 700;
  text-align: right;
}

.crit-pts .muted {
  font-weight: 500;
}

.crit.na .crit-raw {
  font-weight: 500;
  font-style: italic;
}

@media (max-width: 1179px) {
  .groups {
    justify-content: flex-start;
  }

  .group {
    flex: none;
  }
}
</style>
