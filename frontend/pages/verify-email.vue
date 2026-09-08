<script setup lang="ts">
/**
 * Đích đến của liên kết trong thư xác minh: `/verify-email?token=…`.
 *
 * Tự gọi API ngay khi mở — người dùng vừa bấm link trong email, bắt họ bấm thêm
 * một nút "Xác nhận" nữa là thừa. Xác minh xong backend đặt luôn cookie phiên
 * mới nên dùng được ngay, không phải đăng nhập lại.
 */
const route = useRoute()
const { verifyEmail, resendVerification, ensureLoaded, isLoggedIn, pending, error } = useAuth()

useHead({ title: 'Xác minh email — Phân Tích Mã' })

const xong = ref(false)
const thongBao = ref('')
const token = String(route.query.token || '')

onMounted(async () => {
  await ensureLoaded()
  if (!token) return
  xong.value = await verifyEmail(token)
})

async function guiLai(): Promise<void> {
  thongBao.value = await resendVerification()
}
</script>

<template>
  <div class="wrap auth">
    <NuxtLink to="/" class="back">← Về trang chủ</NuxtLink>

    <div class="card">
      <h1>Xác minh email</h1>

      <p v-if="!token" class="msg error" role="alert">
        Liên kết thiếu mã xác minh. Hãy mở đúng liên kết trong thư chúng tôi gửi.
      </p>

      <template v-else-if="pending">
        <p class="note">Đang xác minh…</p>
      </template>

      <template v-else-if="xong">
        <p class="msg ok" role="status">
          Đã xác minh xong. Tài khoản của bạn dùng được trợ lý ngay bây giờ.
        </p>
        <div class="actions">
          <NuxtLink to="/assistant" class="btn primary">Mở trợ lý →</NuxtLink>
          <NuxtLink to="/analysis" class="btn">Phân tích một mã</NuxtLink>
        </div>
      </template>

      <template v-else>
        <p class="msg error" role="alert">{{ error }}</p>
        <p class="note">
          Liên kết xác minh chỉ sống 24 giờ. Nếu đã quá hạn, đăng nhập rồi bấm nút
          dưới đây để nhận thư mới.
        </p>
        <div class="actions">
          <button v-if="isLoggedIn" class="btn primary" type="button"
                  :disabled="pending" @click="guiLai">
            Gửi lại thư xác minh
          </button>
          <NuxtLink v-else class="btn primary" :to="{ path: '/login', query: { next: '/verify-email' } }">
            Đăng nhập để gửi lại
          </NuxtLink>
        </div>
        <p v-if="thongBao" class="msg ok" role="status">{{ thongBao }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.auth { max-width: 460px; }
.back { display: inline-block; margin-bottom: 12px; font-size: 13px; text-decoration: none; }
h1 { margin: 0 0 12px; font-size: 22px; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
</style>
