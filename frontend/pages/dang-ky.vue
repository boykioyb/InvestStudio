<script setup lang="ts">
/** Trang đăng ký. Thành công là đăng nhập luôn (backend đặt cookie ngay). */
const { register, pending, error, ensureLoaded, isLoggedIn } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const displayName = ref('')
const localError = ref('')

useHead({ title: 'Đăng ký — InvestStudio' })

const nextPath = computed(() => {
  const next = String(route.query.next || '/')
  return next.startsWith('/') ? next : '/'
})

onMounted(async () => {
  await ensureLoaded()
  if (isLoggedIn.value) void navigateTo(nextPath.value)
})

async function submit(): Promise<void> {
  localError.value = ''
  if (password.value.length < 6) {
    localError.value = 'Mật khẩu cần tối thiểu 6 ký tự.'
    return
  }
  if (await register(email.value.trim(), password.value, displayName.value.trim())) {
    void navigateTo(nextPath.value)
  }
}
</script>

<template>
  <div class="wrap auth">
    <NuxtLink to="/" class="back">← Về phân tích mã</NuxtLink>

    <div class="card">
      <h1>Đăng ký tài khoản</h1>
      <p class="note">Miễn phí. Chỉ cần email và mật khẩu.</p>

      <p v-if="localError || error" class="msg error" role="alert">{{ localError || error }}</p>

      <form class="stack" @submit.prevent="submit">
        <div class="fg">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" autocomplete="email"
                 required placeholder="ban@vidu.com" />
        </div>
        <div class="fg">
          <label for="name">Tên hiển thị <span class="muted">(tùy chọn)</span></label>
          <input id="name" v-model="displayName" type="text" autocomplete="nickname"
                 maxlength="120" placeholder="Tên bạn muốn hiển thị" />
        </div>
        <div class="fg">
          <label for="password">Mật khẩu <span class="muted">(≥ 6 ký tự)</span></label>
          <input id="password" v-model="password" type="password"
                 autocomplete="new-password" required minlength="6" placeholder="••••••••" />
        </div>
        <button class="btn primary" type="submit" :disabled="pending">
          {{ pending ? 'Đang tạo tài khoản…' : 'Đăng ký' }}
        </button>
      </form>

      <p class="note switch">
        Đã có tài khoản?
        <NuxtLink :to="{ path: '/dang-nhap', query: route.query }">Đăng nhập</NuxtLink>
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
