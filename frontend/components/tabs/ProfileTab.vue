<script setup lang="ts">
/** Tab Hồ sơ: tổng quan doanh nghiệp, lãnh đạo, cổ đông, công ty con/liên kết. */
const props = defineProps<{ ticker: string }>()

const { profile, isLoading, errorOf, loadProfile } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:profile`)

watch(() => props.ticker, (t) => t && loadProfile(t), { immediate: true })

/** Chỉ định dạng để đọc — không đổi giá trị. */
function shares(quantity: number | null): string {
  if (quantity === null || quantity === undefined) return '—'
  return `${(quantity / 1_000_000).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} tr cp`
}
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải hồ sơ doanh nghiệp…</p>

    <template v-else-if="profile">
      <section class="card">
        <h3 class="sec-title">{{ profile.name }}</h3>
        <div class="meta-line">
          <span v-if="profile.short_name" class="badge">{{ profile.short_name }}</span>
          <span v-if="profile.sector" class="badge">{{ profile.sector }}</span>
          <span v-if="profile.exchange" class="badge">{{ profile.exchange }}</span>
          <span v-if="profile.listing_date" class="hint">Niêm yết {{ profile.listing_date }}</span>
        </div>

        <div v-if="profile.highlights.length" class="tiles">
          <div v-for="h in profile.highlights" :key="h.label" class="tile">
            <span class="k">{{ h.label }}</span>
            <span class="v">{{ h.value }}</span>
            <span v-if="h.note" class="hint">{{ h.note }}</span>
          </div>
        </div>
      </section>

      <!-- Khuyến nghị của bên thứ ba: tách bạch, ghi rõ nguồn, không phải điểm của công cụ -->
      <section v-if="profile.analyst" class="card third-party">
        <h3 class="sec-title">Khuyến nghị từ bên thứ ba</h3>
        <div class="analyst">
          <div class="tile">
            <span class="k">Đánh giá</span>
            <span class="v">{{ profile.analyst.rating }}</span>
          </div>
          <div v-if="profile.analyst.target_price !== null" class="tile">
            <span class="k">Giá mục tiêu</span>
            <span class="v">{{ profile.analyst.target_price }}</span>
            <span class="hint">nghìn đ/cp</span>
          </div>
          <div v-if="profile.analyst.upside_pct !== null" class="tile">
            <span class="k">Tiềm năng tăng</span>
            <span class="v">{{ profile.analyst.upside_pct }}%</span>
          </div>
          <div v-if="profile.analyst.analyst" class="tile">
            <span class="k">Chuyên viên</span>
            <span class="v small">{{ profile.analyst.analyst }}</span>
            <span v-if="profile.analyst.as_of" class="hint">{{ profile.analyst.as_of }}</span>
          </div>
        </div>
        <p class="disclaim">⚠️ {{ profile.analyst.source }}</p>
      </section>

      <div class="cols">
        <section v-if="profile.officers.length" class="card">
          <h3 class="sec-title">Ban lãnh đạo</h3>
          <div v-for="p in profile.officers" :key="p.name" class="row">
            <span class="row-main">
              <b>{{ p.name }}</b>
              <span class="hint">{{ p.position }}</span>
            </span>
            <span class="row-num tnum">
              {{ p.percent !== null ? p.percent + '%' : '—' }}
              <span class="hint">{{ shares(p.quantity) }}</span>
            </span>
          </div>
        </section>

        <section v-if="profile.shareholders.length" class="card">
          <h3 class="sec-title">Cổ đông lớn</h3>
          <div v-for="p in profile.shareholders" :key="p.name" class="row">
            <span class="row-main"><b>{{ p.name }}</b></span>
            <span class="row-num tnum">
              {{ p.percent !== null ? p.percent + '%' : '—' }}
              <span class="hint">{{ shares(p.quantity) }}</span>
            </span>
          </div>
        </section>

        <section v-if="profile.subsidiaries.length" class="card">
          <h3 class="sec-title">Công ty con</h3>
          <div v-for="c in profile.subsidiaries" :key="c.name + c.code" class="row">
            <span class="row-main">
              <b>{{ c.name }}</b>
              <span v-if="c.code" class="hint">{{ c.code }}</span>
            </span>
            <span class="row-num tnum">{{ c.percent !== null ? c.percent + '%' : '—' }}</span>
          </div>
        </section>

        <section v-if="profile.affiliates.length" class="card">
          <h3 class="sec-title">Công ty liên kết</h3>
          <div v-for="c in profile.affiliates" :key="c.name + c.code" class="row">
            <span class="row-main">
              <b>{{ c.name }}</b>
              <span v-if="c.code" class="hint">{{ c.code }}</span>
            </span>
            <span class="row-num tnum">{{ c.percent !== null ? c.percent + '%' : '—' }}</span>
          </div>
        </section>
      </div>
    </template>

    <p v-else class="hint">Chưa có dữ liệu hồ sơ.</p>
  </div>
</template>

<style scoped>
.meta-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.tile {
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tile .k {
  font-size: 10.5px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--muted);
}

.tile .v {
  font-size: 17px;
  font-weight: 800;
}

.tile .v.small {
  font-size: 14px;
}

/* Khối bên thứ ba: viền cảnh báo để không lẫn với kết luận của công cụ */
.third-party {
  border-color: var(--warn);
}

.analyst {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.disclaim {
  margin: 10px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--warn);
}

.cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
  align-items: start;
}

.row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}

.row:last-child {
  border-bottom: none;
}

/* flex:1 để tên dài không đẩy cột tỷ lệ xuống dòng riêng — nhìn dễ đọc nhầm
   thành một dòng dữ liệu khác. */
.row-main {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}

.row-num {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  font-weight: 700;
  white-space: nowrap;
}
</style>
