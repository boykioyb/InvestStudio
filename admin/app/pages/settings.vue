<script setup lang="ts">
/** Cài đặt: cần gạt khẩn cấp + hạn mức + bật xác thực 2 lớp. */
const api = useAdminApi()
const route = useRoute()
const me = useAdminUser()

//  Bị đẩy sang đây vì chưa bật 2 lớp → nói rõ lý do ngay đầu trang, thay vì để
//  người dùng ngơ ngác không hiểu sao vừa bấm Tổng quan lại nhảy sang Cài đặt.
const cangBat2Lop = computed(() => route.query.warn === '2fa' || me.value?.totp_enabled === false)

const { data, pending, refresh } = await useAsyncData('settings', () =>
  api.get<any[]>('/admin/settings').catch(() => [])
)

const nhap = reactive<Record<string, any>>({})
watchEffect(() => {
  for (const item of data.value ?? []) nhap[item.key] = item.value
})

const nhom = computed(() => {
  const out: Record<string, any[]> = {}
  for (const item of data.value ?? []) (out[item.group] ??= []).push(item)
  return out
})

const dangLuu = ref(false)
const thongBao = ref('')
const loi = ref('')

async function luu() {
  dangLuu.value = true
  loi.value = ''
  try {
    await api.put('/admin/settings', { values: { ...nhap }, reason: 'sửa từ khu quản trị' })
    //  Cache cấu hình ở backend sống 30 giây, nói rõ để không ai tưởng nút hỏng.
    thongBao.value = 'Đã lưu. Có hiệu lực trên toàn hệ thống trong vòng 30 giây.'
    await refresh()
  } catch (e: any) {
    loi.value = e.message
  } finally {
    dangLuu.value = false
  }
}

// ── Xác thực 2 lớp ─────────────────────────────────────────────────────────
const totp = ref<any>(null)
const ma = ref('')

async function taoKhoa() {
  loi.value = ''
  try {
    totp.value = await api.post<any>('/admin/2fa/setup')
  } catch (e: any) {
    loi.value = e.message
  }
}

async function bat() {
  loi.value = ''
  try {
    await api.post(`/admin/2fa/enable?code=${ma.value}`)
    totp.value = null
    ma.value = ''
    //  Bật 2 lớp làm token_version tăng → phiên hiện tại đã chết. Nói thật và
    //  đưa về trang đăng nhập thay vì để người dùng bấm tiếp rồi ăn 401.
    thongBao.value = 'Đã bật xác thực 2 lớp. Đang đưa bạn về trang đăng nhập…'
    me.value = null
    setTimeout(() => navigateTo('/login?next=/'), 1800)
  } catch (e: any) {
    loi.value = e.message
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold">Cài đặt hệ thống</h1>
        <p class="text-sm text-muted">Đổi ở đây có hiệu lực ngay, không cần deploy lại.</p>
      </div>
      <UButton :loading="dangLuu" icon="i-lucide-save" @click="luu">Lưu thay đổi</UButton>
    </div>

    <UAlert
      v-if="cangBat2Lop"
      color="warning"
      variant="subtle"
      icon="i-lucide-shield-alert"
      title="Hãy bật xác thực 2 lớp trước"
      description="Khu quản trị đọc được dữ liệu của mọi người dùng, nên chỉ mở sau khi tài khoản có 2 lớp. Bật ở thẻ bên dưới, sau đó đăng nhập lại."
    />

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" close @close="loi = ''" />
    <UAlert v-else-if="thongBao" color="success" variant="subtle" :title="thongBao" close @close="thongBao = ''" />

    <UCard v-for="(items, ten) in nhom" :key="ten">
      <template #header>
        <div>
          <span class="font-medium">{{ ten }}</span>
          <p v-if="ten === 'Cần gạt khẩn cấp'" class="text-xs text-muted">
            Dùng khi đang bị lạm dụng: tắt tính năng ngay thay vì chờ một lần deploy.
          </p>
        </div>
      </template>

      <div class="space-y-3">
        <div v-for="item in items" :key="item.key" class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm">{{ item.label }}</p>
            <p class="text-xs text-muted">
              <code>{{ item.key }}</code>
              <span v-if="item.overridden"> · đang ghi đè mặc định</span>
            </p>
          </div>
          <USwitch v-if="item.type === 'bool'" v-model="nhap[item.key]" />
          <UInput v-else v-model.number="nhap[item.key]" type="number" class="w-28" />
        </div>
      </div>
    </UCard>

    <UCard>
      <template #header><span class="font-medium">Xác thực 2 lớp (bắt buộc với quản trị)</span></template>
      <p class="text-sm text-muted">
        Khu quản trị đọc được dữ liệu của mọi người dùng — chiếm được một tài khoản admin là
        chiếm toàn bộ. Mật khẩu thôi không đủ.
      </p>

      <p v-if="me?.totp_enabled" class="mt-3 text-sm text-success">
        Tài khoản này đã bật 2 lớp.
      </p>
      <div v-else-if="!totp" class="mt-3">
        <UButton icon="i-lucide-shield-check" variant="soft" @click="taoKhoa">Tạo mã bật 2 lớp</UButton>
      </div>

      <div v-else class="mt-3 space-y-3">
        <p class="text-sm">Thêm vào ứng dụng xác thực (Google Authenticator, Authy…):</p>
        <pre class="overflow-x-auto rounded bg-elevated p-2 text-xs">{{ totp.otpauth_url }}</pre>
        <p class="text-xs text-muted">Hoặc nhập tay khóa: <code>{{ totp.secret }}</code></p>
        <div class="flex gap-2">
          <UInput v-model="ma" placeholder="Mã 6 số" class="w-32" />
          <UButton :disabled="ma.length < 6" @click="bat">Bật</UButton>
        </div>
      </div>
    </UCard>

    <p v-if="pending" class="text-sm text-muted">Đang tải…</p>
  </div>
</template>
