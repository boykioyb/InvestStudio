<script setup lang="ts">
/** Cache trong tiến trình: xem và xóa khi nguồn trả số sai. */
const api = useAdminApi()
const { number } = useAdminFormat()

const { data, pending, refresh } = await useAsyncData('cache', () => api.get<any>('/admin/cache'))

const ma = ref('')
const thongBao = ref('')
const loi = ref('')

async function xoa(tatCa = false) {
  loi.value = ''
  const code = tatCa ? '' : ma.value.trim().toUpperCase()
  if (tatCa && !window.confirm('Xóa TOÀN BỘ cache? Lượt truy cập tiếp theo sẽ crawl lại từ nguồn.')) return
  if (!tatCa && !code) return
  try {
    const kq = await api.del<any>(`/admin/cache?ticker=${code}`)
    thongBao.value = `Đã xóa ${kq.removed} mục (${kq.ticker}).`
    ma.value = ''
    await refresh()
  } catch (e: any) {
    loi.value = e.message
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Cache</h1>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" close @close="loi = ''" />
    <UAlert v-else-if="thongBao" color="success" variant="subtle" :title="thongBao" close
            @close="thongBao = ''" />

    <UAlert color="neutral" variant="subtle" icon="i-lucide-info" title="Đọc kỹ trước khi dựa vào con số này"
            :description="data?.note" />

    <div class="grid gap-4 sm:grid-cols-3">
      <UCard v-for="c in data?.caches ?? []" :key="c.name">
        <p class="text-sm text-muted">{{ c.name }}</p>
        <p class="text-2xl font-semibold">{{ number(c.size) }}<span class="text-base font-normal text-muted">/{{ number(c.maxsize) }}</span></p>
        <p class="text-xs text-muted">hết hạn sau {{ Math.round(c.ttl_seconds / 60) }} phút</p>
      </UCard>
    </div>

    <UCard>
      <template #header><span class="font-medium">Xóa cache</span></template>
      <p class="text-sm text-muted">
        Dùng khi nguồn trả số sai và bạn muốn ép lấy lại ngay. Xóa xong lượt truy cập kế
        tiếp sẽ chậm hơn vì phải crawl thật.
      </p>
      <div class="mt-3 flex flex-wrap gap-2">
        <UInput v-model="ma" placeholder="Mã cần xóa, VD: FPT" class="w-48" @keydown.enter="xoa(false)" />
        <UButton :disabled="!ma.trim()" @click="xoa(false)">Xóa theo mã</UButton>
        <UButton color="error" variant="soft" @click="xoa(true)">Xóa toàn bộ</UButton>
      </div>
    </UCard>
  </div>
</template>
