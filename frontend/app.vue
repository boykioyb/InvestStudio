<script setup lang="ts">
// Vỏ ứng dụng: chỉ giữ khung cao đúng một màn hình, mọi thứ khác do trang tự dựng.
</script>

<template>
  <!-- Nền toàn cục: aurora + lưới mờ (chỉ trình bày, không chặn tương tác). -->
  <div class="app-aura" aria-hidden="true" />
  <div class="app-grid" aria-hidden="true" />
  <!-- Nhắc xác minh email: đặt ở vỏ app để mọi trang đều thấy. -->
  <VerifyEmailBanner />
  <NuxtPage />
  <!-- Miễn trừ trách nhiệm + trang pháp lý: phải có ở mọi trang, không chỉ README. -->
  <AppFooter />
  <!-- Trợ lý RAG nổi ở góc — dùng được ở mọi trang, tự bắt mã đang xem. -->
  <ChatWidget />
</template>
