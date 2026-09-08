<script setup lang="ts">
/** Gửi thông báo hệ thống tới người dùng (hiện ở chuông trong app, không phải email). */
const api = useAdminApi()

const noiDung = ref('')
const chiDaXacMinh = ref(true)
const dangGui = ref(false)
const ketQua = ref('')
const loi = ref('')

const conLai = computed(() => 500 - noiDung.value.length)

async function gui() {
  if (noiDung.value.trim().length < 5) return
  if (!window.confirm('Gửi thông báo này tới tất cả người dùng đã chọn?')) return
  dangGui.value = true
  loi.value = ''
  try {
    const kq = await api.post<any>('/admin/broadcast', {
      message: noiDung.value.trim(), only_verified: chiDaXacMinh.value
    })
    ketQua.value = `Đã gửi tới ${kq.sent} người dùng.`
    noiDung.value = ''
  } catch (e: any) {
    loi.value = e.message
  } finally {
    dangGui.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-semibold">Thông báo hệ thống</h1>
      <p class="text-sm text-muted">
        Hiện ở chuông thông báo trong ứng dụng. <b>Không gửi email</b> — người dùng chỉ
        thấy khi họ mở trang.
      </p>
    </div>

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" close @close="loi = ''" />
    <UAlert v-else-if="ketQua" color="success" variant="subtle" :title="ketQua" close
            @close="ketQua = ''" />

    <UCard>
      <UTextarea v-model="noiDung" :rows="4" :maxlength="500" class="w-full"
                 placeholder="VD: Hệ thống sẽ bảo trì 22:00–22:30 hôm nay, trợ lý tạm ngưng trong thời gian này." />
      <p class="mt-1 text-xs text-muted">Còn {{ conLai }} ký tự.</p>

      <div class="mt-3 flex items-center justify-between gap-3">
        <label class="flex items-center gap-2 text-sm">
          <USwitch v-model="chiDaXacMinh" />
          Chỉ gửi cho tài khoản đã xác minh email
        </label>
        <UButton :loading="dangGui" :disabled="noiDung.trim().length < 5" @click="gui">
          Gửi thông báo
        </UButton>
      </div>
    </UCard>

    <UAlert
      color="warning" variant="subtle" icon="i-lucide-triangle-alert"
      title="Không thu hồi được"
      description="Thông báo đã gửi sẽ nằm trong chuông của từng người cho tới khi họ tự đánh dấu đã đọc. Đọc lại một lượt trước khi bấm gửi."
    />
  </div>
</template>
