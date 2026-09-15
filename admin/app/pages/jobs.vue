<script setup lang="ts">
/** Job nền & hàng đợi Celery. */
const api = useAdminApi()
const { dateTime } = useAdminFormat()

const { data, pending, refresh } = await useAsyncData('jobs', () => api.get<any>('/admin/jobs'))

//  Trạng thái do worker ghi vào bảng index_jobs là RUNNING/DONE/ERROR
//  (app/services/rag/tasks.py); Celery còn có SUCCESS/FAILURE. Map cả hai bộ
//  để badge không rơi về xám khi job đã xong.
const MAU: Record<string, string> = {
  SUCCESS: 'success', DONE: 'success', RUNNING: 'primary',
  QUEUED: 'neutral', PENDING: 'neutral', FAILURE: 'error', ERROR: 'error'
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

        <!--  0 job đang chờ KHÔNG phải lỗi khi có worker: worker hút job ngay nên
              hàng đợi gần như luôn rỗng. Thứ đáng lo là KHÔNG có worker nào. -->
        <p v-if="!data?.queue_ok" class="text-xs text-error">
          Redis không phản hồi — job nền có thể đang không chạy.
        </p>
        <p v-else-if="data && data.workers_online > 0" class="text-xs text-muted">
          {{ data.workers_online }} worker đang chạy — “0 đang chờ” là bình thường,
          worker nhặt job gần như tức thì (xem “Job gần đây” bên dưới).
        </p>
        <p v-else class="text-xs text-error">
          ⚠ Không có worker nào trả lời — job nền sẽ nằm chờ mãi. Kiểm tra service
          <code>worker</code> (Celery).
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
