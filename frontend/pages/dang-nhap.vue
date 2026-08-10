<script setup lang="ts">
/** Trang đăng nhập. Thành công thì quay lại `?next=` (mặc định trang chủ). */
const { login, pending, error, ensureLoaded, isLoggedIn } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')

useHead({ title: 'Đăng nhập — InvestStudio' })

const nextPath = computed(() => {
  const next = String(route.query.next || '/')
  //  Chỉ nhận đường dẫn nội bộ để tránh chuyển hướng ra ngoài (open redirect).
  return next.startsWith('/') ? next : '/'
})

onMounted(async () => {
  await ensureLoaded()
  if (isLoggedIn.value) void navigateTo(nextPath.value)
})

async function submit(): Promise<void> {
  if (await login(email.value.trim(), password.value)) {
    void navigateTo(nextPath.value)
  }
}
</script>

<template>
  <div class="wrap auth">
    <NuxtLink to="/" class="back">← Về phân tích mã</NuxtLink>

    <div class="card">
      <h1>Đăng nhập</h1>
      <p class="note">Đăng nhập để lưu mã yêu thích và dùng trợ lý hỏi–đáp.</p>

      <p v-if="error" class="msg error" role="alert">{{ error }}</p>

      <form class="stack" @submit.prevent="submit">
        <div class="fg">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" autocomplete="email"
                 required placeholder="ban@vidu.com" />
        </div>
        <div class="fg">
          <label for="password">Mật khẩu</label>
          <input id="password" v-model="password" type="password"
                 autocomplete="current-password" required placeholder="••••••••" />
        </div>
        <button class="btn primary" type="submit" :disabled="pending">
          {{ pending ? 'Đang đăng nhập…' : 'Đăng nhập' }}
        </button>
      </form>

      <p class="note switch">
        Chưa có tài khoản?
        <NuxtLink :to="{ path: '/dang-ky', query: route.query }">Đăng ký</NuxtLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth {
  max-width: 440px;
}

.back {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 13px;
  text-decoration: none;
}

h1 {
  margin: 0 0 6px;
  font-size: 22px;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.stack .fg input {
  font-size: 15px;
  padding: 11px 13px;
}

.stack .btn.primary {
  margin-top: 4px;
}

.switch {
  margin-top: 16px;
  text-align: center;
}
</style>
