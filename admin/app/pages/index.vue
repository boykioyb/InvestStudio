<script setup lang="ts">
/** Tổng quan: thẻ số + mức tiêu thụ quota Gemini + xếp hạng hôm nay. */
const api = useAdminApi()
const { number, percent, dateTime } = useAdminFormat()

const { data, pending, error, refresh } = await useAsyncData('overview', () =>
  api.get<any>('/admin/overview')
)

//  Thanh quota là thứ cần nhìn thấy TRƯỚC TIÊN: hết quota là trợ lý im với mọi
//  người tới 0h hôm sau, và không mua thêm được (đang dùng bản miễn phí).
const quotaColor = computed(() => {
  const level = data.value?.gemini_level
  return level === 'exhausted' ? 'error' : level === 'saving' ? 'warning' : 'success'
})
const quotaNote = computed(() => ({
  ok: 'Bình thường — trợ lý chạy đầy đủ.',
  saving: 'Tiết kiệm — đã tự tắt agent, mỗi câu chỉ còn 1 request.',
  exhausted: 'Sắp cạn — chỉ phục vụ người đã hỏi trong ngày.'
}[data.value?.gemini_level as string] || ''))

const cards = computed(() => [
  { label: 'Người dùng', value: number(data.value?.users_total), sub: `+${data.value?.users_new_today ?? 0} hôm nay` },
  { label: 'Đã xác minh email', value: number(data.value?.users_verified), sub: 'trên tổng số' },
  { label: 'Lượt hỏi trợ lý', value: number(data.value?.chat_today), sub: 'hôm nay' },
  { label: 'Lượt phân tích', value: number(data.value?.analyze_today), sub: 'hôm nay' },
  { label: 'Tỷ lệ lỗi', value: percent(data.value?.error_rate_today ?? 0), sub: 'hôm nay' },
  { label: 'Kho tri thức', value: number(data.value?.rag_documents), sub: `${data.value?.rag_tickers ?? 0} mã` }
])
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold">Tổng quan</h1>
        <p class="text-sm text-muted">Cập nhật {{ dateTime(new Date().toISOString()) }}</p>
      </div>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()">
        Làm mới
      </UButton>
    </div>

    <UAlert v-if="error" color="error" variant="subtle" :title="error.message" />

    <template v-else>
      <UCard>
        <div class="flex flex-wrap items-end justify-between gap-2">
          <div>
            <p class="text-sm text-muted">Quota Gemini hôm nay</p>
            <p class="text-2xl font-semibold">
              {{ number(data?.gemini_used) }}
              <span class="text-base font-normal text-muted">/ {{ number(data?.gemini_cap) }} request</span>
            </p>
          </div>
          <UBadge :color="quotaColor" variant="subtle">{{ percent(data?.gemini_ratio ?? 0) }}</UBadge>
        </div>
        <UProgress class="mt-3" :model-value="(data?.gemini_ratio ?? 0) * 100" :color="quotaColor" />
        <p class="mt-2 text-xs text-muted">{{ quotaNote }}</p>
      </UCard>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <UCard v-for="card in cards" :key="card.label">
          <p class="text-sm text-muted">{{ card.label }}</p>
          <p class="text-2xl font-semibold">{{ card.value }}</p>
          <p class="text-xs text-muted">{{ card.sub }}</p>
        </UCard>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <UCard>
          <template #header><span class="font-medium">Dùng nhiều nhất hôm nay</span></template>
          <p v-if="!data?.top_users?.length" class="text-sm text-muted">Chưa có hoạt động nào.</p>
          <ul v-else class="divide-y divide-default">
            <li v-for="row in data.top_users" :key="row.key" class="flex justify-between py-2 text-sm">
              <span class="truncate">{{ row.label }}</span>
              <span class="font-medium">{{ number(row.count) }}</span>
            </li>
          </ul>
        </UCard>

        <UCard>
          <template #header><span class="font-medium">Mã được tra nhiều nhất</span></template>
          <p v-if="!data?.top_tickers?.length" class="text-sm text-muted">Chưa có lượt phân tích nào.</p>
          <div v-else class="flex flex-wrap gap-2">
            <UBadge v-for="row in data.top_tickers" :key="row.key" variant="subtle">
              {{ row.label }} · {{ row.count }}
            </UBadge>
          </div>
        </UCard>
      </div>

      <UCard>
        <template #header><span class="font-medium">30 ngày gần nhất</span></template>
        <p v-if="!data?.series?.length" class="text-sm text-muted">
          Chưa có dữ liệu tổng hợp — job <code>usage.flush</code> gom số 5 phút một lần.
        </p>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="text-left text-muted">
              <tr><th class="py-1">Ngày</th><th>Loại</th><th class="text-right">Lượt</th><th class="text-right">Request</th><th class="text-right">Lỗi</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in data.series" :key="i" class="border-t border-default">
                <td class="py-1">{{ row.day }}</td>
                <td>{{ row.kind }}</td>
                <td class="text-right">{{ number(row.count) }}</td>
                <td class="text-right">{{ number(row.calls) }}</td>
                <td class="text-right">{{ number(row.error_count) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>
    </template>
  </div>
</template>
