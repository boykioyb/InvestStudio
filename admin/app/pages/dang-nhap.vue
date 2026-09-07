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

//  Vào thẳng trang này với ?loi=quyen nghĩa là đăng nhập được nhưng không phải admin.
if (route.query.loi === 'quyen') {
  loi.value = 'Tài khoản này không có quyền quản trị.'
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

        <template #footer>
          <p class="text-xs text-muted">
            Khu quản trị đọc được dữ liệu người dùng — mọi thao tác đều được ghi nhật ký.
          </p>
        </template>
      </UCard>
    </div>
  </UApp>
</template>
