<script setup lang="ts">
/** Người dùng: tìm/lọc, khóa/mở, đổi vai trò, hạng + hạn mức, thu hồi phiên, xóa. */
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

// ── Hạng & hạn mức riêng ───────────────────────────────────────────────────
//  Sửa NGAY TRONG BẢNG (một dòng phụ dưới người dùng) chứ không mở hộp thoại:
//  chỉ có ba ô, và khu quản trị này không dùng UModal ở đâu cả — thêm một kiểu
//  tương tác mới cho ba ô thì không đáng.
const HANG = [
  { label: 'Thường', value: 'free' },
  { label: 'VIP', value: 'vip' }
]
const nhanHang = (plan: string) => HANG.find((h) => h.value === plan)?.label ?? plan

const dangSua = ref<number | null>(null)
const dangLuu = ref(false)
//  Ô để trống giữ nguyên là chuỗi rỗng, KHÔNG quy về 0: 0 là "chặn hoàn toàn",
//  còn trống là "chưa đặt riêng, dùng mức của hạng". Hai nghĩa khác hẳn nhau.
const nhapHanMuc = reactive({
  plan: 'free',
  chat: '' as number | string,
  analyze: '' as number | string
})

/** Tài khoản này có hạn mức đặt riêng không (khác với thừa hưởng từ hạng/chung). */
const coRieng = (u: any) =>
  u.chat_daily_quota !== null || u.analyze_daily_quota !== null

function moSua(u: any) {
  dangSua.value = u.id
  nhapHanMuc.plan = u.plan ?? 'free'
  nhapHanMuc.chat = u.chat_daily_quota ?? ''
  nhapHanMuc.analyze = u.analyze_daily_quota ?? ''
}

/** '' (ô để trống) → null = xóa hạn mức riêng. Còn lại → số. */
const soHoacNull = (v: number | string): number | null =>
  v === '' ? null : Number(v)

function luuHanMuc(u: any) {
  dangLuu.value = true
  chay(async () => {
    await api.patch(`/admin/users/${u.id}`, {
      plan: nhapHanMuc.plan,
      chat_daily_quota: soHoacNull(nhapHanMuc.chat),
      analyze_daily_quota: soHoacNull(nhapHanMuc.analyze),
      reason: 'đặt hạng / hạn mức từ khu quản trị'
    })
    dangSua.value = null
  }, `Đã cập nhật hạn mức cho ${u.email}.`).finally(() => { dangLuu.value = false })
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
              <th>Hạng</th>
              <th>Trạng thái</th>
              <th class="text-right">Thiết bị</th>
              <th class="text-right">Câu hỏi</th>
              <th class="text-right">Hạn mức/ngày</th>
              <th>Đăng nhập gần nhất</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="u in data?.items ?? []" :key="u.id">
              <tr class="border-t border-default">
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
                  <UBadge :color="u.plan === 'vip' ? 'warning' : 'neutral'" variant="subtle">
                    {{ nhanHang(u.plan) }}
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
                <!-- Số CÓ HIỆU LỰC (riêng người → hạng → chung), không phải số
                     đặt riêng: đây mới là con số thật sẽ chặn người này. -->
                <td class="text-right whitespace-nowrap">
                  <p :class="coRieng(u) ? 'font-medium' : ''">
                    Trợ lý {{ number(u.chat_quota_effective) }}
                  </p>
                  <p class="text-xs text-muted">
                    Phân tích {{ number(u.analyze_quota_effective) }}
                    <span v-if="coRieng(u)"> · đặt riêng</span>
                  </p>
                </td>
                <td class="text-xs">{{ dateTime(u.last_login_at) }}</td>
                <td class="text-right whitespace-nowrap">
                  <UButton size="xs" variant="ghost" icon="i-lucide-gauge"
                           title="Hạng & hạn mức" @click="moSua(u)" />
                  <UButton size="xs" variant="ghost" :icon="u.status === 'active' ? 'i-lucide-lock' : 'i-lucide-lock-open'" @click="doiTrangThai(u)" />
                  <UButton size="xs" variant="ghost" icon="i-lucide-log-out" @click="thuHoiPhien(u)" />
                  <UButton size="xs" variant="ghost" color="error" icon="i-lucide-trash-2" @click="xoa(u)" />
                </td>
              </tr>

              <!-- Ba ô sửa tại chỗ: để TRỐNG một ô = xóa hạn mức riêng, quay về
                   mức của hạng rồi tới mức chung. Số 0 = chặn hoàn toàn. -->
              <tr v-if="dangSua === u.id" class="border-t border-default bg-elevated/50">
                <td colspan="9" class="py-3">
                  <div class="flex flex-wrap items-end gap-3">
                    <div>
                      <p class="mb-1 text-xs text-muted">Hạng</p>
                      <USelect v-model="nhapHanMuc.plan" :items="HANG" class="w-40" />
                    </div>
                    <div>
                      <p class="mb-1 text-xs text-muted">Lượt hỏi trợ lý / ngày</p>
                      <UInput v-model.number="nhapHanMuc.chat" type="number"
                              placeholder="trống = mức chung" class="w-48" />
                    </div>
                    <div>
                      <p class="mb-1 text-xs text-muted">Lượt phân tích / ngày</p>
                      <UInput v-model.number="nhapHanMuc.analyze" type="number"
                              placeholder="trống = mức chung" class="w-48" />
                    </div>
                    <UButton size="sm" icon="i-lucide-save" :loading="dangLuu"
                             @click="luuHanMuc(u)">Lưu</UButton>
                    <UButton size="sm" variant="ghost" @click="dangSua = null">Hủy</UButton>
                    <p class="text-xs text-muted">
                      Để trống = dùng mức của hạng, rồi tới mức chung. Số 0 = chặn hoàn toàn.
                    </p>
                  </div>
                </td>
              </tr>
            </template>
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
