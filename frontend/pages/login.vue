<script setup lang="ts">
/** Trang đăng nhập. Thành công thì quay lại `?next=` (mặc định trang chủ). */
const { login, pending, error, ensureLoaded, isLoggedIn } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')

useHead({ title: 'Đăng nhập — Phân Tích Mã' })

const nextPath = computed(() => isSafeNext(String(route.query.next || '/')))

onMounted(async () => {
  //  Callback Google thất bại đưa về đây kèm ?oauth_error= — hiện cho người dùng.
  const oauthError = route.query.oauth_error
  if (typeof oauthError === 'string' && oauthError) error.value = oauthError
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
    <NuxtLink to="/analysis" class="back">← Về phân tích mã</NuxtLink>

    <div class="card auth-card">
      <div class="brand"><span class="mark">◆</span> Phân Tích Mã</div>
      <h1>Đăng nhập</h1>
      <p class="note">Lưu mã yêu thích và dùng trợ lý hỏi–đáp.</p>

      <p v-if="error" class="msg error" role="alert">{{ error }}</p>

      <form class="stack" @submit.prevent="submit">
        <div class="fg">
          <label for="email">Email</label>
          <div class="field">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" />
            </svg>
            <input id="email" v-model="email" type="email" autocomplete="email"
                   required placeholder="ban@vidu.com" />
          </div>
        </div>
        <div class="fg">
          <label for="password">Mật khẩu</label>
          <div class="field">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <input id="password" v-model="password" type="password"
                   autocomplete="current-password" required placeholder="••••••••" />
          </div>
        </div>
        <button class="btn primary" type="submit" :disabled="pending">
          {{ pending ? 'Đang đăng nhập…' : 'Đăng nhập' }}
        </button>
      </form>

      <AuthSocial :next="nextPath" />

      <p class="note switch">
        Chưa có tài khoản?
        <NuxtLink :to="{ path: '/register', query: route.query }">Đăng ký</NuxtLink>
        <span class="sep">·</span>
        <NuxtLink to="/forgot-password">Quên mật khẩu?</NuxtLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Card đăng nhập: gọn, căn giữa theo chiều dọc để không trôi lên đầu trang. */
.auth {
  max-width: 384px;
  min-height: calc(100dvh - 210px);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.back {
  align-self: flex-start;
  margin-bottom: 12px;
  font-size: 13px;
  text-decoration: none;
}

.auth-card {
  width: 100%;
  padding: 26px 26px 24px;
  margin: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 14px;
}

.brand .mark {
  color: var(--accent);
}

h1 {
  margin: 0 0 4px;
  font-size: 20px;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

/* ô nhập có icon dẫn ở mép trái */
.field {
  position: relative;
}

.field svg {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--muted);
  opacity: 0.75;
  pointer-events: none;
}

.stack .fg input {
  width: 100%;
  font-size: 14.5px;
  padding: 11px 13px 11px 38px;
}

.stack .btn.primary {
  width: 100%;
  margin-top: 6px;
  padding: 12px;
  font-size: 14.5px;
}

.switch {
  margin-top: 18px;
  text-align: center;
}

.sep {
  margin: 0 6px;
  opacity: 0.5;
}
</style>
