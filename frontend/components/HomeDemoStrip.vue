<script setup lang="ts">
/**
 * Dải "kết quả mẫu" của trang chủ — VÍ DỤ MINH HOẠ tĩnh (mã FPT, số liệu chốt
 * ngày 24/08/2026) để người xem hình dung đầu ra. Không phải số liệu live.
 */
</script>

<template>
  <section class="strip">
    <div class="box">
      <div class="head">
        <div class="who">
          <span class="kicker">Kết quả mẫu</span>
          <span class="demo-tag">Ví dụ minh hoạ</span>
          <span class="sym">FPT</span>
          <span class="name">Công ty Cổ phần FPT · Công nghệ</span>
        </div>
        <span class="src">
          Cập nhật <b class="tnum">24/08/2026</b> · nguồn
          <span class="badge">CafeF</span><span class="badge">VCI</span>
        </span>
      </div>

      <div class="kpis">
        <div class="kpi">
          <div class="k">Điểm tổng</div>
          <div class="v"><span class="big lv-good tnum">81</span><span class="unit tnum">/100</span></div>
          <div class="sub lv-good strong">Xuất sắc — ưu tiên giải ngân</div>
        </div>
        <div class="kpi">
          <div class="k">Định giá</div>
          <div class="v"><span class="big lv-good tnum">18</span><span class="unit tnum">/20</span></div>
          <div class="sub">P/E <b class="tnum">12.2</b> vs ngành <b class="tnum">18.0</b> · P/B <b class="tnum">3.06</b></div>
        </div>
        <div class="kpi">
          <div class="k">Mức rủi ro · kịch bản xấu</div>
          <div class="v"><span class="big lv-bad tnum">−8%</span><span class="unit">cắt lỗ tại <b class="tnum">65,69</b></span></div>
          <div class="sub">≈ <b class="tnum">1,6%</b> tổng tài khoản nếu dồn tối đa 20%</div>
        </div>
        <div class="kpi">
          <div class="k">Giá đóng cửa</div>
          <div class="v"><span class="big tnum">71,40</span><span class="unit">nghìn đ/cp</span></div>
          <div class="sub">Tầm nhìn hợp nhất: <b>Trung hạn</b> <span class="lv-good tnum">80</span><span class="muted tnum">/100</span></div>
        </div>
      </div>

      <div class="foot">
        <span>Chi tiết 14 tiêu chí, biểu đồ giá và kịch bản xấu nhất ở phần dưới.</span>
        <NuxtLink :to="{ path: '/analysis', query: { symbol: 'FPT' } }" class="ghost">Mở phân tích đầy đủ FPT →</NuxtLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.strip { max-width: 1320px; margin: 0 auto; padding: 40px 26px 0; }
.box { background: var(--panel-solid); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px 16px;
  flex-wrap: wrap; margin-bottom: 14px; }
.who { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.kicker { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
.demo-tag { font-size: 10.5px; font-weight: 700; color: var(--warn); background: var(--warn-soft);
  border-radius: 12px; padding: 2px 8px; white-space: nowrap; }
.sym { font-size: 20px; font-weight: 700; font-family: var(--mono); color: var(--text); }
.name { font-size: 13px; color: var(--muted); }
.src { font-size: 12.5px; color: var(--muted); display: inline-flex; gap: 8px; align-items: center;
  flex-wrap: wrap; line-height: 1.8; }
.src b { color: var(--text); font-weight: 600; }
.badge { font-size: 11.5px; padding: 1px 8px; }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: 10px; }
.kpi { background: var(--panel-deep); border: 1px solid var(--line); border-radius: 10px; padding: 14px; }
.k { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); }
.v { display: flex; align-items: baseline; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.big { font-size: 34px; font-weight: 700; line-height: 1; }
.unit { font-size: 13px; color: var(--muted); }
.unit b { color: var(--text); font-weight: 600; }
.sub { font-size: 12.5px; color: var(--text-2); margin-top: 6px; }
.sub b { font-weight: 600; }
.sub.strong { font-weight: 600; }

.foot { display: flex; gap: 8px 16px; align-items: center; justify-content: space-between;
  flex-wrap: wrap; margin-top: 14px; font-size: 13px; color: var(--muted); }
.ghost { display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px; border-radius: 10px;
  text-decoration: none; color: var(--accent); font-weight: 600; border: 1px solid rgba(90, 200, 255, 0.45); }
.ghost:hover { background: rgba(90, 200, 255, 0.12); }

@media (max-width: 700px) {
  .strip { padding: 22px 16px 0; }
  .box { padding: 16px 14px; }
  /* mobile: 2×2 cho gọn màn hình, giống bản thiết kế */
  .kpis { grid-template-columns: 1fr 1fr; gap: 8px; }
  .kpi { padding: 12px 12px; }
  .big { font-size: 22px; }
  .k { font-size: 10px; }
  .sub { font-size: 11.5px; }
  .unit { font-size: 12px; }
  .ghost { width: 100%; justify-content: center; min-height: 48px; }
}
</style>
