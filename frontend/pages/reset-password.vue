<script setup lang="ts">
/** Đặt mật khẩu mới bằng token trong thư: `/reset-password?token=…`. */
const route = useRoute()
const { resetPassword, pending, error } = useAuth()

useHead({ title: 'Đặt lại mật khẩu — Phân Tích Mã' })

const MAT_KHAU_TOI_THIEU = 10   // khớp ràng buộc của backend (schemas/auth.py)

const token = String(route.query.token || '')
const matKhau = ref('')
const nhapLai = ref('')
const xong = ref(false)

const lechNhau = computed(() => nhapLai.value.length > 0 && matKhau.value !== nhapLai.value)
const hopLe = computed(() => matKhau.value.length >= MAT_KHAU_TOI_THIEU && !lechNhau.value)

async function submit(): Promise<void> {
  if (!hopLe.value) return
  xong.value = await resetPassword(token, matKhau.value)
}
</script>

<template>
  <div class="wrap auth">
    <NuxtLink to="/login" class="back">← Về đăng nhập</NuxtLink>

    <div class="card">
      <h1>Đặt mật khẩu mới</h1>

      <p v-if="!token" class="msg error" role="alert">
        Liên kết thiếu mã đặt lại. Hãy mở đúng liên kết trong thư chúng tôi gửi.
      </p>

      <template v-else-if="xong">
        <p class="msg ok" role="status">
          Đã đổi mật khẩu. Mọi thiết bị đang đăng nhập bằng mật khẩu cũ đều bị đăng xuất.
        </p>
        <NuxtLink to="/login" class="btn primary">Đăng nhập lại →</NuxtLink>
      </template>

      <template v-else>
        <p v-if="error" class="msg error" role="alert">{{ error }}</p>

        <form class="stack" @submit.prevent="submit">
          <div class="fg">
            <label for="pw">Mật khẩu mới</label>
            <input id="pw" v-model="matKhau" type="password" autocomplete="new-password"
                   required :minlength="MAT_KHAU_TOI_THIEU" placeholder="••••••••••" />
            <small class="muted">Tối thiểu {{ MAT_KHAU_TOI_THIEU }} ký tự.</small>
          </div>
          <div class="fg">
            <label for="pw2">Nhập lại mật khẩu mới</label>
            <input id="pw2" v-model="nhapLai" type="password" autocomplete="new-password"
                   required placeholder="••••••••••" />
            <small v-if="lechNhau" class="lech">Hai ô chưa khớp nhau.</small>
          </div>
          <button class="btn primary" type="submit" :disabled="pending || !hopLe">
            {{ pending ? 'Đang lưu…' : 'Đặt mật khẩu mới' }}
          </button>
        </form>
      </template>
    </div>
  </div>
</template>

<style scoped>
.auth { max-width: 440px; }
.back { display: inline-block; margin-bottom: 12px; font-size: 13px; text-decoration: none; }
h1 { margin: 0 0 12px; font-size: 22px; }
.stack { display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }
.stack .fg input { font-size: 15px; padding: 11px 13px; }
.fg small { display: block; margin-top: 5px; font-size: 12px; }
.lech { color: var(--bad); }
</style>
