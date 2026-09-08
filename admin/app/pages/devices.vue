<script setup lang="ts">
/** Thiết bị & chống lạm dụng: một máy nuôi bao nhiêu tài khoản, chặn/bỏ chặn. */
const api = useAdminApi()
const { dateTime, number } = useAdminFormat()

const sort = ref('account_count')
const loi = ref('')
const thongBao = ref('')

const { data, pending, refresh } = await useAsyncData('devices',
  () => api.get<any[]>(`/admin/devices?sort=${sort.value}&limit=100`), { watch: [sort] })

async function doiChan(d: any) {
  loi.value = ''
  try {
    if (d.blocked) {
      await api.post(`/admin/devices/${d.fp_hash}/unblock`)
      thongBao.value = 'Đã bỏ chặn thiết bị.'
    } else {
      const ly_do = window.prompt('Lý do chặn (người dùng sẽ đọc được):',
                                  'Tạo nhiều tài khoản để vượt hạn mức')
      if (ly_do === null) return
      await api.post(`/admin/devices/${d.fp_hash}/block`, { reason: ly_do })
      thongBao.value = 'Đã chặn thiết bị.'
    }
    await refresh()
  } catch (e: any) {
    loi.value = e.message
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold">Thiết bị & chống lạm dụng</h1>
        <p class="text-sm text-muted">
          Nhiều tài khoản dùng chung một thiết bị là dấu hiệu rõ nhất của việc tạo tài khoản
          để nhân hạn mức.
        </p>
      </div>
      <div class="flex gap-2">
        <USelect
          v-model="sort"
          :items="[
            { label: 'Nhiều tài khoản nhất', value: 'account_count' },
            { label: 'Hoạt động gần nhất', value: 'last_seen' },
            { label: 'Nhiều request nhất', value: 'request_count' }
          ]"
          class="w-52"
        />
        <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
      </div>
    </div>

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" close @close="loi = ''" />
    <UAlert v-else-if="thongBao" color="success" variant="subtle" :title="thongBao" close
            @close="thongBao = ''" />

    <UAlert
      color="warning" variant="subtle" icon="i-lucide-triangle-alert"
      title="Chặn nhầm là có thật"
      description="Hai máy cùng đời, cùng hệ điều hành, cùng trình duyệt có thể trùng vân tay. Ưu tiên hạ hạn mức hoặc khóa từng tài khoản trước khi chặn cả thiết bị."
    />

    <UCard>
      <p v-if="!data?.length" class="text-sm text-muted">Chưa ghi nhận thiết bị nào.</p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-muted">
            <tr>
              <th class="py-2">Vân tay</th><th class="text-right">Tài khoản</th>
              <th class="text-right">Request</th><th>IP gần nhất</th>
              <th>Hoạt động gần nhất</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in data" :key="d.fp_hash" class="border-t border-default">
              <td class="py-2">
                <code class="text-xs">{{ d.fp_hash.slice(0, 12) }}</code>
                <p class="mt-1 max-w-md truncate text-xs text-muted">{{ d.emails.join(', ') || '—' }}</p>
                <p v-if="d.blocked" class="text-xs text-error">Đã chặn: {{ d.blocked_reason }}</p>
              </td>
              <td class="text-right" :class="d.account_count > 2 ? 'font-medium text-warning' : ''">
                {{ number(d.account_count) }}
              </td>
              <td class="text-right">{{ number(d.request_count) }}</td>
              <td class="text-xs">{{ d.last_ip || '—' }}</td>
              <td class="text-xs">{{ dateTime(d.last_seen) }}</td>
              <td class="text-right">
                <UButton size="xs" :color="d.blocked ? 'neutral' : 'error'" variant="ghost"
                         @click="doiChan(d)">
                  {{ d.blocked ? 'Bỏ chặn' : 'Chặn' }}
                </UButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>
  </div>
</template>
