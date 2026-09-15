<script setup lang="ts">
/** Đăng nhập khu quản trị. Tài khoản đã bật 2 lớp thì hiện thêm ô mã 6 số. */
definePageMeta({ layout: false })

const route = useRoute()
const me = useAdminUser()

const email = ref('')
const matKhau = ref('')
const ma = ref('')
const canMa = ref(false)          // chỉ hiện ô mã khi backend báo là cần
const dangGui = ref(false)
const loi = ref('')

const googleBat = ref(false)      // backend có cấu hình đăng nhập Google không
const dangGoogle = ref(false)

//  Vào thẳng trang này với ?error=forbidden nghĩa là đăng nhập được nhưng không phải admin.
if (route.query.error === 'forbidden') {
  loi.value = 'Tài khoản này không có quyền quản trị.'
}
//  Callback Google báo lỗi (không có quyền admin, phiên hết hạn…) → hiện lại ở đây.
if (route.query.oauth_error) {
  loi.value = String(route.query.oauth_error)
}

//  Chỉ hiện nút Google khi backend đã cấu hình khóa OAuth (tránh nút bấm vào 503).
onMounted(async () => {
  try {
    const cfg = await $fetch<{ google: boolean }>('/api/auth/oauth-config')
    googleBat.value = cfg.google
  } catch { /* để nút ẩn nếu không hỏi được */ }
})

async function dangNhapGoogle() {
  dangGoogle.value = true
  loi.value = ''
  try {
    //  `app=admin` → backend dùng redirect URI RIÊNG của khu quản trị, và ở
    //  callback chỉ cho vào nếu tài khoản Google khớp một admin đã có.
    const next = (route.query.next as string) || '/'
    const { url } = await $fetch<{ url: string }>('/api/auth/google/start', {
      params: { app: 'admin', next }
    })
    window.location.href = url
  } catch (e: any) {
    loi.value = e?.data?.detail || 'Không bắt đầu được đăng nhập Google.'
    dangGoogle.value = false
  }
}

async function dangNhap() {
  dangGui.value = true
  loi.value = ''
  try {
    const user = await $fetch<any>('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      body: { email: email.value, password: matKhau.value, totp_code: ma.value }
    })
    if (user?.role !== 'admin') {
      loi.value = 'Tài khoản này không có quyền quản trị.'
      return
    }
    me.value = user
    await navigateTo((route.query.next as string) || '/')
  } catch (e: any) {
    const detail = e?.data?.detail || 'Không đăng nhập được.'
    //  Backend nói "nhập mã 6 số" → mở ô nhập thay vì bắt người dùng tự đoán.
    if (detail.includes('6 số')) canMa.value = true
    loi.value = detail
  } finally {
    dangGui.value = false
  }
}
</script>

<template>
  <UApp>
    <div class="min-h-screen flex items-center justify-center bg-elevated/40 p-4">
      <UCard class="w-full max-w-sm">
        <template #header>
          <p class="font-semibold">Phân Tích Mã</p>
          <p class="text-sm text-muted">Đăng nhập khu quản trị</p>
        </template>

        <form class="space-y-3" @submit.prevent="dangNhap">
          <UInput v-model="email" type="email" placeholder="Email" autocomplete="username"
                  icon="i-lucide-mail" required class="w-full" />
          <UInput v-model="matKhau" type="password" placeholder="Mật khẩu"
                  autocomplete="current-password" icon="i-lucide-lock" required class="w-full" />
          <UInput v-if="canMa" v-model="ma" placeholder="Mã 6 số từ ứng dụng xác thực"
                  icon="i-lucide-shield-check" class="w-full" />

          <UAlert v-if="loi" color="error" variant="subtle" :title="loi" />

          <UButton type="submit" block :loading="dangGui">Đăng nhập</UButton>
        </form>

        <div v-if="googleBat" class="mt-4">
          <USeparator label="hoặc" />
          <UButton block color="neutral" variant="outline" class="mt-4"
                   :loading="dangGoogle" @click="dangNhapGoogle">
            <template #leading>
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.24 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
                <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84Z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
              </svg>
            </template>
            Tiếp tục với Google
          </UButton>
        </div>

        <template #footer>
          <p class="text-xs text-muted">
            Khu quản trị đọc được dữ liệu người dùng — mọi thao tác đều được ghi nhật ký.
          </p>
        </template>
      </UCard>
    </div>
  </UApp>
</template>
