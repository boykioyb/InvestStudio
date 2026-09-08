<script setup lang="ts">
/** Người dùng: tìm/lọc, khóa/mở, đổi vai trò, thu hồi phiên, xóa. */
const api = useAdminApi()
const { number, dateTime } = useAdminFormat()

const q = ref('')
//  Không dùng chuỗi rỗng làm giá trị: USelect (Reka UI) cấm — chuỗi rỗng là
//  tín hiệu "xóa lựa chọn". Dùng 'all' rồi quy đổi khi dựng query.
const trangThai = ref('all')
const page = ref(1)
const thongBao = ref('')
const loi = ref('')

const { data, pending, refresh } = await useAsyncData(
  'users',
  () => {
    const loc = trangThai.value === 'all' ? '' : trangThai.value
    return api.get<any>(
      `/admin/users?q=${encodeURIComponent(q.value)}&status=${loc}&page=${page.value}`)
  },
  { watch: [q, trangThai, page] }
)

async function chay(viec: () => Promise<unknown>, xong: string) {
  loi.value = ''
  try {
    await viec()
    thongBao.value = xong
    await refresh()
  } catch (e: any) {
    loi.value = e.message
  }
}

const doiTrangThai = (u: any) =>
  chay(() => api.patch(`/admin/users/${u.id}`, {
    status: u.status === 'active' ? 'suspended' : 'active',
    reason: 'thao tác từ khu quản trị'
  }), u.status === 'active' ? 'Đã khóa tài khoản.' : 'Đã mở khóa tài khoản.')

const thuHoiPhien = (u: any) =>
  chay(() => api.post(`/admin/users/${u.id}/revoke-sessions`), 'Đã thu hồi mọi phiên đăng nhập.')

const xoa = (u: any) => {
  //  Xóa là không hoàn tác được → bắt gõ lại email, không chỉ bấm "OK".
  const nhap = window.prompt(`Xóa vĩnh viễn ${u.email}? Gõ lại email để xác nhận:`)
  if (nhap !== u.email) return
  chay(() => api.del(`/admin/users/${u.id}`), 'Đã xóa tài khoản.')
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">Người dùng</h1>

    <div class="flex flex-wrap gap-2">
      <UInput v-model="q" placeholder="Tìm theo email hoặc tên…" icon="i-lucide-search" class="w-64" />
      <USelect
        v-model="trangThai"
        :items="[
          { label: 'Tất cả trạng thái', value: 'all' },
          { label: 'Đang hoạt động', value: 'active' },
          { label: 'Đã khóa', value: 'suspended' }
        ]"
        class="w-48"
      />
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" @close="loi = ''" close />
    <UAlert v-else-if="thongBao" color="success" variant="subtle" :title="thongBao" @close="thongBao = ''" close />

    <UCard>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-muted">
            <tr>
              <th class="py-2">Email</th>
              <th>Vai trò</th>
              <th>Trạng thái</th>
              <th class="text-right">Thiết bị</th>
              <th class="text-right">Câu hỏi</th>
              <th>Đăng nhập gần nhất</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in data?.items ?? []" :key="u.id" class="border-t border-default">
              <td class="py-2">
                <p class="font-medium">{{ u.email }}</p>
                <p class="text-xs text-muted">
                  {{ u.email_verified ? 'đã xác minh' : 'chưa xác minh email' }} · {{ u.last_ip || '—' }}
                </p>
              </td>
              <td>
                <UBadge :color="u.role === 'admin' ? 'primary' : 'neutral'" variant="subtle">
                  {{ u.role }}
                </UBadge>
              </td>
              <td>
                <UBadge :color="u.status === 'active' ? 'success' : 'error'" variant="subtle">
                  {{ u.status === 'active' ? 'hoạt động' : 'đã khóa' }}
                </UBadge>
              </td>
              <!-- Nhiều tài khoản chung một thiết bị là dấu hiệu rõ nhất của tài khoản ảo. -->
              <td class="text-right" :class="u.device_count > 2 ? 'text-warning font-medium' : ''">
                {{ number(u.device_count) }}
              </td>
              <td class="text-right">{{ number(u.chat_count) }}</td>
              <td class="text-xs">{{ dateTime(u.last_login_at) }}</td>
              <td class="text-right whitespace-nowrap">
                <UButton size="xs" variant="ghost" :icon="u.status === 'active' ? 'i-lucide-lock' : 'i-lucide-lock-open'" @click="doiTrangThai(u)" />
                <UButton size="xs" variant="ghost" icon="i-lucide-log-out" @click="thuHoiPhien(u)" />
                <UButton size="xs" variant="ghost" color="error" icon="i-lucide-trash-2" @click="xoa(u)" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template #footer>
        <div class="flex items-center justify-between text-sm text-muted">
          <span>{{ number(data?.total) }} tài khoản</span>
          <div class="flex gap-2">
            <UButton size="xs" variant="ghost" :disabled="page <= 1" @click="page--">Trước</UButton>
            <span>{{ data?.page }} / {{ data?.pages }}</span>
            <UButton size="xs" variant="ghost" :disabled="page >= (data?.pages ?? 1)" @click="page++">Sau</UButton>
          </div>
        </div>
      </template>
    </UCard>
  </div>
</template>
