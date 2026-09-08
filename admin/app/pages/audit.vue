<script setup lang="ts">
/** Nhật ký kiểm toán: ai làm gì, lúc nào, trước/sau ra sao. */
const api = useAdminApi()
const { dateTime } = useAdminFormat()

const { data, pending, refresh } = await useAsyncData('audit', () =>
  api.get<any[]>('/admin/audit?limit=200')
)

const nhan: Record<string, string> = {
  view_user_data: 'Xem dữ liệu người dùng',
  update_user: 'Sửa tài khoản',
  revoke_sessions: 'Thu hồi phiên',
  delete_user: 'Xóa tài khoản',
  update_settings: 'Đổi cấu hình',
  totp_setup: 'Tạo khóa 2 lớp',
  totp_enable: 'Bật 2 lớp',
  totp_disable: 'Tắt 2 lớp'
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold">Nhật ký kiểm toán</h1>
        <p class="text-sm text-muted">Chỉ ghi thêm, không sửa được — kể cả bởi quản trị.</p>
      </div>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <UCard>
      <p v-if="!data?.length" class="text-sm text-muted">Chưa có thao tác nào được ghi.</p>
      <ul v-else class="divide-y divide-default">
        <li v-for="row in data" :key="row.id" class="py-3 text-sm">
          <div class="flex flex-wrap items-center gap-2">
            <UBadge variant="subtle">{{ nhan[row.action] || row.action }}</UBadge>
            <span class="text-muted">{{ dateTime(row.at) }}</span>
            <span>{{ row.actor_email }}</span>
            <span v-if="row.target_type" class="text-muted">
              → {{ row.target_type }} #{{ row.target_id }}
            </span>
          </div>
          <p v-if="row.reason" class="mt-1 text-xs text-muted">Lý do: {{ row.reason }}</p>
          <details v-if="Object.keys(row.before || {}).length || Object.keys(row.after || {}).length" class="mt-1">
            <summary class="cursor-pointer text-xs text-muted">Trước / sau</summary>
            <pre class="mt-1 overflow-x-auto rounded bg-elevated p-2 text-xs">{{ { truoc: row.before, sau: row.after } }}</pre>
          </details>
        </li>
      </ul>
    </UCard>
  </div>
</template>
