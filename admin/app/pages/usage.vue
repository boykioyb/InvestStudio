<script setup lang="ts">
/** Sử dụng & hạn mức: chuỗi ngày theo loại + ai/mã nào dùng nhiều nhất. */
const api = useAdminApi()
const { number } = useAdminFormat()

const songay = ref(30)
const { data: series, pending, refresh } = await useAsyncData('usage',
  () => api.get<any[]>(`/admin/usage?days=${songay.value}`), { watch: [songay] })
const { data: overview } = await useAsyncData('usage-overview', () => api.get<any>('/admin/overview'))

//  Gộp theo ngày để mỗi ngày một dòng, các loại nằm ngang — dễ so hơn là
//  đọc ba dòng rời cho cùng một ngày.
const theoNgay = computed(() => {
  const gom: Record<string, any> = {}
  for (const r of series.value ?? []) {
    const d = (gom[r.day] ??= { day: r.day, chat: 0, analyze: 0, embed: 0, calls: 0, loi: 0 })
    d[r.kind] = (d[r.kind] ?? 0) + r.count
    d.calls += r.calls
    d.loi += r.error_count
  }
  return Object.values(gom).sort((a: any, b: any) => (a.day < b.day ? 1 : -1))
})

const tong = computed(() => (theoNgay.value as any[]).reduce((acc: any, d: any) => ({
  chat: acc.chat + d.chat, analyze: acc.analyze + d.analyze,
  calls: acc.calls + d.calls, loi: acc.loi + d.loi
}), { chat: 0, analyze: 0, calls: 0, loi: 0 }))
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold">Sử dụng & hạn mức</h1>
        <p class="text-sm text-muted">
          Số liệu gom từ Redis mỗi 5 phút (job <code>usage.flush</code>), nên ngày hôm nay
          có thể trễ vài phút.
        </p>
      </div>
      <div class="flex gap-2">
        <USelect
          v-model="songay"
          :items="[{ label: '7 ngày', value: 7 }, { label: '30 ngày', value: 30 }, { label: '90 ngày', value: 90 }]"
          class="w-32"
        />
        <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UCard><p class="text-sm text-muted">Lượt hỏi trợ lý</p><p class="text-2xl font-semibold">{{ number(tong.chat) }}</p></UCard>
      <UCard><p class="text-sm text-muted">Lượt phân tích</p><p class="text-2xl font-semibold">{{ number(tong.analyze) }}</p></UCard>
      <UCard>
        <p class="text-sm text-muted">Request Gemini</p>
        <p class="text-2xl font-semibold">{{ number(tong.calls) }}</p>
        <p class="text-xs text-muted">≈ {{ tong.chat ? (tong.calls / tong.chat).toFixed(1) : '—' }} request mỗi lượt hỏi</p>
      </UCard>
      <UCard><p class="text-sm text-muted">Lỗi</p><p class="text-2xl font-semibold">{{ number(tong.loi) }}</p></UCard>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <UCard>
        <template #header><span class="font-medium">Dùng nhiều nhất hôm nay</span></template>
        <p v-if="!overview?.top_users?.length" class="text-sm text-muted">Chưa có hoạt động nào.</p>
        <ul v-else class="divide-y divide-default text-sm">
          <li v-for="r in overview.top_users" :key="r.key" class="flex justify-between py-2">
            <span class="truncate">{{ r.label }}</span><b>{{ number(r.count) }}</b>
          </li>
        </ul>
      </UCard>
      <UCard>
        <template #header><span class="font-medium">Mã được tra nhiều nhất hôm nay</span></template>
        <p v-if="!overview?.top_tickers?.length" class="text-sm text-muted">Chưa có lượt phân tích nào.</p>
        <div v-else class="flex flex-wrap gap-2">
          <UBadge v-for="r in overview.top_tickers" :key="r.key" variant="subtle">{{ r.label }} · {{ r.count }}</UBadge>
        </div>
      </UCard>
    </div>

    <UCard>
      <template #header><span class="font-medium">Theo ngày</span></template>
      <p v-if="!theoNgay.length" class="text-sm text-muted">
        Chưa có dữ liệu tổng hợp. Job gom số chạy 5 phút một lần.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-muted">
            <tr><th class="py-1">Ngày</th><th class="text-right">Trợ lý</th><th class="text-right">Phân tích</th><th class="text-right">Nhúng</th><th class="text-right">Request Gemini</th><th class="text-right">Lỗi</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in (theoNgay as any[])" :key="d.day" class="border-t border-default">
              <td class="py-1">{{ d.day }}</td>
              <td class="text-right">{{ number(d.chat) }}</td>
              <td class="text-right">{{ number(d.analyze) }}</td>
              <td class="text-right">{{ number(d.embed) }}</td>
              <td class="text-right">{{ number(d.calls) }}</td>
              <td class="text-right" :class="d.loi ? 'text-error font-medium' : ''">{{ number(d.loi) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>
  </div>
</template>
