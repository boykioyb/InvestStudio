<script setup lang="ts">
/** Job nền & hàng đợi Celery. */
const api = useAdminApi()
const { dateTime } = useAdminFormat()

const { data, pending, refresh } = await useAsyncData('jobs', () => api.get<any>('/admin/jobs'))

const MAU: Record<string, string> = {
  SUCCESS: 'success', RUNNING: 'primary', QUEUED: 'neutral', FAILURE: 'error'
}

//  Lịch khai trong app/core/celery_app.py — hiện ra đây để người vận hành không
//  phải mở mã nguồn mới biết cái gì chạy lúc nào.
const LICH = [
  { ten: 'Lập chỉ mục VN30 + tin', khi: '08:00 hằng ngày' },
  { ten: 'Quét ngưỡng mã theo dõi', khi: 'mỗi 30 phút' },
  { ten: 'Dồn bộ đếm sử dụng', khi: 'mỗi 5 phút' }
]
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Job & hàng đợi</h1>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <UCard>
        <p class="text-sm text-muted">Hàng đợi Celery</p>
        <p class="text-2xl font-semibold">
          <template v-if="data?.queue_ok">{{ data.queue_length }} job đang chờ</template>
          <span v-else class="text-error">không đọc được</span>
        </p>
        <p v-if="!data?.queue_ok" class="text-xs text-muted">
          Redis không phản hồi — job nền có thể đang không chạy.
        </p>
      </UCard>

      <UCard>
        <template #header><span class="font-medium">Lịch chạy nền</span></template>
        <ul class="space-y-1 text-sm">
          <li v-for="l in LICH" :key="l.ten" class="flex justify-between gap-3">
            <span>{{ l.ten }}</span><span class="text-muted">{{ l.khi }}</span>
          </li>
        </ul>
      </UCard>
    </div>

    <UCard>
      <template #header><span class="font-medium">Job lập chỉ mục gần đây</span></template>
      <p v-if="!data?.jobs?.length" class="text-sm text-muted">Chưa có job nào.</p>
      <ul v-else class="divide-y divide-default">
        <li v-for="j in data.jobs" :key="j.id" class="flex flex-wrap items-center gap-3 py-2 text-sm">
          <UBadge :color="MAU[j.status] || 'neutral'" variant="subtle">{{ j.status }}</UBadge>
          <span class="text-xs text-muted">{{ dateTime(j.created_at) }}</span>
          <span class="min-w-0 flex-1 truncate">{{ j.message || '—' }}</span>
          <code class="text-xs text-muted">{{ j.task_id.slice(0, 8) }}</code>
        </li>
      </ul>
    </UCard>
  </div>
</template>
