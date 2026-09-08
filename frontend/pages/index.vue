<script setup lang="ts">
/**
 * Trang chủ (Home Redesign v3): cửa vào → tìm mã → đi vào phân tích từng mã.
 *
 * Trang chỉ lắp các khối và truyền dữ liệu thật từ composable xuống; mọi trình
 * bày nằm trong component con. Thẻ "kết quả mẫu" là VÍ DỤ MINH HOẠ tĩnh.
 */
const {
  group, pending, error, inSession, sessionLabel,
  gainers, losers, mostActive, activeLabel, breadth, load, selectGroup
} = useMarketOverview()

function go(code: string): void {
  const c = code.trim().toUpperCase()
  if (c) void navigateTo({ path: '/analysis', query: { symbol: c } })
}

onMounted(() => { void load() })

useHead({ title: 'Phân Tích Mã — Đầu tư có cơ sở' })
</script>

<template>
  <div class="home">
    <AppHeader />
    <TickerTape :items="mostActive" />

    <HomeHero :in-session="inSession" :session-label="sessionLabel" @pick="go" />

    <HomeDemoStrip />
    <HomeDemoSection />

    <MarketSection
      :group="group"
      :pending="pending"
      :error="error"
      :in-session="inSession"
      :session-label="sessionLabel"
      :gainers="gainers"
      :losers="losers"
      :most-active="mostActive"
      :active-label="activeLabel"
      :breadth="breadth"
      @pick-group="selectGroup"
    />

    <MarketHighlights :group="group" />

    <HomeCta @pick="go" />

    <footer class="disclaimer">
      Số liệu <b>thu thập tự động từ nguồn công khai</b> nên có thể chậm hoặc sai lệch.
      Đây là <b>công cụ hỗ trợ tư duy</b>, <b>không phải khuyến nghị đầu tư</b>.
    </footer>
  </div>
</template>

<style scoped>
.home { min-height: 100dvh; }
.disclaimer { max-width: 1320px; margin: 34px auto 0; padding: 16px 26px 96px; }

@media (max-width: 700px) {
  .disclaimer { margin-top: 28px; padding: 16px 16px calc(84px + env(safe-area-inset-bottom)); text-align: left; }
}
</style>
