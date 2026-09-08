<script setup lang="ts">
/**
 * "Cách chấm điểm" — giải thích mô hình 100 điểm cho người ngoài.
 *
 * Toàn bộ nội dung LẤY TỪ API (`/api/stocks/scoring-model`), sinh từ
 * `backend/app/services/criteria.py`. Cố ý không chép trọng số hay ngưỡng vào
 * đây: mô hình chỉ được tồn tại ở một nơi, nếu không trang này sẽ nói một đằng
 * còn máy chấm một nẻo ngay lần sửa ngưỡng đầu tiên.
 */
import type { ScoringModel } from '~/types/stock'

const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

useHead({ title: 'Cách chấm điểm — Phân Tích Mã' })

const { data: model, pending, error } = await useFetch<ScoringModel>(
  `${apiBase}/api/stocks/scoring-model`, { key: 'scoring-model' })

const moRong = ref<string | null>(null)
const toggle = (key: string) => (moRong.value = moRong.value === key ? null : key)

const NHAN_MUC = ['Yếu', 'Trung bình', 'Tốt']
</script>

<template>
  <div class="wrap scoring">
    <AppHeader />

    <header class="intro">
      <h1>Cách chấm điểm</h1>
      <p class="note">
        Mỗi mã được chấm trên thang <b>{{ model?.total ?? 100 }} điểm</b>, chia thành
        {{ model?.groups.length ?? 4 }} nhóm. Điểm không phải lời khuyên mua bán — nó là
        cách tóm tắt một mã đang <i>mạnh yếu ở đâu</i> để bạn biết cần đào sâu chỗ nào.
      </p>
    </header>

    <p v-if="pending" class="note">Đang tải mô hình…</p>
    <p v-else-if="error" class="msg error">Chưa tải được mô hình chấm điểm. Thử lại sau.</p>

    <template v-else-if="model">
      <section class="card grades">
        <h2>Xếp loại theo tổng điểm</h2>
        <ul class="grade-list">
          <li v-for="g in model.grades" :key="g.min_total" :class="g.level">
            <b>{{ g.min_total > 0 ? `≥ ${g.min_total}` : `< ${model.grades[model.grades.length - 2]?.min_total ?? 50}` }}</b>
            <span>{{ g.text }}</span>
          </li>
        </ul>
      </section>

      <section v-for="group in model.groups" :key="group.name" class="card">
        <h2>
          {{ group.name }}
          <span class="diem">{{ group.max }} điểm</span>
        </h2>

        <ul class="tieu-chi">
          <li v-for="c in group.criteria" :key="c.key">
            <button type="button" class="dong" :aria-expanded="moRong === c.key"
                    @click="toggle(c.key)">
              <span class="ten">
                {{ c.label }}
                <span v-if="c.manual" class="tag">bạn tự chấm</span>
              </span>
              <span class="max">{{ c.max }}đ</span>
              <span class="mui">{{ moRong === c.key ? '−' : '+' }}</span>
            </button>

            <div v-if="moRong === c.key" class="chi-tiet">
              <p><b>Đo cái gì:</b> {{ c.what }}</p>
              <p><b>Vì sao quan trọng:</b> {{ c.why }}</p>
              <p><b>Chấm thế nào:</b> {{ c.how }}</p>
              <ul class="bands">
                <li v-for="(b, i) in c.bands" :key="i" :class="`lv${b.level}`">
                  <span class="muc">{{ NHAN_MUC[b.level] ?? b.level }}</span>
                  <span>{{ b.text }}</span>
                </li>
              </ul>
            </div>
          </li>
        </ul>
      </section>

      <p class="note cuoi">
        Thiếu dữ liệu thì tiêu chí đó nhận <b>0 điểm</b> và được đánh dấu "N/A" — cố ý bảo
        thủ, thà chấm thấp còn hơn bịa số. Vì vậy một mã điểm thấp bất thường có thể là do
        thiếu dữ liệu chứ không phải vì cổ phiếu xấu.
      </p>
    </template>
  </div>
</template>

<style scoped>
.scoring { max-width: 860px; }
.intro { margin: 18px 0 16px; }
h1 { margin: 0 0 6px; font-size: 26px; }
h2 { display: flex; align-items: baseline; gap: 10px; margin: 0 0 10px; font-size: 17px; }
.diem { font-size: 12px; color: var(--muted); font-weight: 500; }
.card + .card { margin-top: 14px; }

.grade-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.grade-list li { display: flex; gap: 12px; font-size: 14px; padding: 6px 10px; border-radius: 8px; background: var(--panel2); }
.grade-list li b { min-width: 52px; }
.grade-list li.good b { color: var(--good); }
.grade-list li.warn b { color: var(--warn, #d9a441); }
.grade-list li.bad b { color: var(--bad); }

.tieu-chi { list-style: none; margin: 0; padding: 0; }
.tieu-chi > li { border-top: 1px solid var(--line); }
.tieu-chi > li:first-child { border-top: 0; }

.dong {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 10px 2px; background: none; border: 0; cursor: pointer;
  color: var(--text); font-size: 14px; text-align: left;
}
.dong:hover .ten { color: var(--accent); }
.ten { flex: 1; font-weight: 600; }
.max { color: var(--muted); font-size: 12px; }
.mui { width: 16px; text-align: center; color: var(--muted); }
.tag { margin-left: 6px; padding: 1px 6px; border-radius: 999px; font-size: 10px; font-weight: 500; color: var(--muted); border: 1px solid var(--line); }

.chi-tiet { padding: 2px 2px 14px; font-size: 13px; }
.chi-tiet p { margin: 0 0 6px; color: var(--muted); }
.chi-tiet p b { color: var(--text); font-weight: 600; }

.bands { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 4px; }
.bands li { display: flex; gap: 10px; padding: 5px 9px; border-radius: 7px; background: var(--panel2); font-size: 12.5px; }
.muc { min-width: 74px; font-weight: 700; }
.bands li.lv2 .muc { color: var(--good); }
.bands li.lv1 .muc { color: var(--warn, #d9a441); }
.bands li.lv0 .muc { color: var(--bad); }

.cuoi { margin: 16px 0 40px; }

@media (max-width: 620px) {
  .muc { min-width: 62px; }
}
</style>
