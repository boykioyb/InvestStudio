<script setup lang="ts">
/** Nguồn dữ liệu: sống/chết, độ trễ, thử lại từng nguồn. */
const api = useAdminApi()
const { dateTime } = useAdminFormat()

const { data, pending, refresh } = await useAsyncData('providers',
  () => api.get<any[]>('/admin/providers'))

const dangThu = ref('')

async function thuLai(name: string) {
  dangThu.value = name
  try {
    await api.post(`/admin/providers/${name}/probe`)
    await refresh()
  } finally {
    dangThu.value = ''
  }
}

const MO_TA: Record<string, string> = {
  vci: 'Vietcap — cơ bản, bảng giá, danh sách rổ',
  dnse: 'DNSE — lịch sử giá (ưu tiên) và tin tức',
  cafef: 'CafeF — lịch sử giá dự phòng',
  google_news: 'Google News — nguồn tin thứ hai',
  gemini: 'Google Gemini — nhúng và sinh câu trả lời'
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold">Nguồn dữ liệu</h1>
        <p class="text-sm text-muted">
          Kết quả nhớ trong 60 giây — mở trang mà bắn thật vào cả 5 nguồn mỗi lần thì
          chính trang này làm nguồn chặn IP của mình.
        </p>
      </div>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()">
        Làm mới
      </UButton>
    </div>

    <UCard v-for="p in data ?? []" :key="p.name">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="inline-block h-2 w-2 rounded-full"
                  :class="p.ok ? 'bg-success' : 'bg-error'" />
            <span class="font-medium">{{ p.name }}</span>
            <UBadge :color="p.ok ? 'success' : 'error'" variant="subtle" size="sm">
              {{ p.ok ? 'sống' : 'hỏng' }}
            </UBadge>
            <span class="text-xs text-muted">{{ p.latency_ms }}ms</span>
          </div>
          <p class="mt-1 text-xs text-muted">{{ MO_TA[p.name] || '' }}</p>
          <p class="mt-1 text-sm" :class="p.ok ? 'text-muted' : 'text-error'">{{ p.detail }}</p>
        </div>
        <div class="text-right">
          <p class="text-xs text-muted">{{ dateTime(p.checked_at) }}</p>
          <UButton size="xs" variant="soft" class="mt-1" :loading="dangThu === p.name"
                   @click="thuLai(p.name)">
            Thử ngay
          </UButton>
        </div>
      </div>
    </UCard>
  </div>
</template>
