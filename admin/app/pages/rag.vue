<script setup lang="ts">
/** Kho tri thức (RAG): còn bao nhiêu tài liệu, cũ tới đâu, chạy lại chỉ mục. */
const api = useAdminApi()
const { dateTime, number } = useAdminFormat()

const { data: status, pending, refresh } = await useAsyncData('rag-status',
  () => api.get<any>('/admin/rag/status'))

const ma = ref('')
const { data: docs, refresh: refreshDocs } = await useAsyncData('rag-docs',
  () => api.get<any[]>(`/admin/rag/documents?ticker=${ma.value.toUpperCase()}&limit=100`),
  { watch: [ma] })

const loi = ref('')
const thongBao = ref('')

//  Kho đứng yên nghĩa là trợ lý trả lời bằng dữ liệu cũ mà không ai biết — cảnh
//  báo khi tài liệu mới nhất đã quá 3 ngày.
const kho_cu = computed(() => (status.value?.newest_days ?? 0) > 3)

async function chayLai(deep = false) {
  loi.value = ''
  try {
    await api.post(`/chat/reindex?deep=${deep}`)
    thongBao.value = 'Đã đưa vào hàng đợi. Worker sẽ xử lý dần — theo dõi ở trang Job.'
    await refresh()
  } catch (e: any) {
    loi.value = e.message
  }
}

async function xoa(doc: any) {
  if (!window.confirm(`Xóa tài liệu "${doc.title}" khỏi kho?`)) return
  try {
    await api.del(`/admin/rag/documents/${doc.id}`)
    await Promise.all([refresh(), refreshDocs()])
  } catch (e: any) {
    loi.value = e.message
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Kho tri thức (RAG)</h1>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <UAlert v-if="loi" color="error" variant="subtle" :title="loi" close @close="loi = ''" />
    <UAlert v-else-if="thongBao" color="success" variant="subtle" :title="thongBao" close
            @close="thongBao = ''" />

    <UAlert
      v-if="kho_cu" color="warning" variant="subtle" icon="i-lucide-clock-alert"
      title="Kho tri thức đang cũ"
      :description="`Tài liệu mới nhất đã ${status?.newest_days} ngày. Trợ lý vẫn trả lời, nhưng bằng dữ liệu cũ — kiểm tra xem job lập chỉ mục hằng sáng có chạy không.`"
    />

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UCard><p class="text-sm text-muted">Tài liệu</p><p class="text-2xl font-semibold">{{ number(status?.documents) }}</p></UCard>
      <UCard><p class="text-sm text-muted">Số mã</p><p class="text-2xl font-semibold">{{ number(status?.tickers) }}</p></UCard>
      <UCard>
        <p class="text-sm text-muted">Tuổi dữ liệu</p>
        <p class="text-2xl font-semibold">{{ status?.newest_days ?? '—' }} ngày</p>
        <p class="text-xs text-muted">cũ nhất {{ status?.oldest_days ?? '—' }} ngày</p>
      </UCard>
      <UCard>
        <p class="text-sm text-muted">Trạng thái</p>
        <p class="text-2xl font-semibold">{{ status?.running ? 'đang chạy' : 'rảnh' }}</p>
        <p class="truncate text-xs text-muted" :title="status?.last_message">{{ status?.last_message }}</p>
      </UCard>
    </div>

    <UCard>
      <template #header><span class="font-medium">Lập chỉ mục lại</span></template>
      <p class="text-sm text-muted">
        Mỗi lần chạy tiêu khá nhiều request Gemini (mỗi tài liệu là một lệnh nhúng). Bản
        thường nạp tổng quan rổ VN30 + tin; bản "kèm điểm số" chậm hơn nhiều.
      </p>
      <div class="mt-3 flex flex-wrap gap-2">
        <UButton :disabled="status?.running" @click="chayLai(false)">Chạy lại (thường)</UButton>
        <UButton variant="soft" :disabled="status?.running" @click="chayLai(true)">
          Chạy lại kèm điểm số
        </UButton>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <UBadge v-for="(n, loai) in status?.by_type ?? {}" :key="loai" variant="subtle">
          {{ loai }}: {{ n }}
        </UBadge>
      </div>
    </UCard>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between gap-3">
          <span class="font-medium">Tài liệu</span>
          <UInput v-model="ma" placeholder="Lọc theo mã…" size="xs" class="w-40" />
        </div>
      </template>
      <p v-if="!docs?.length" class="text-sm text-muted">Không có tài liệu nào khớp.</p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-muted">
            <tr><th class="py-1">Mã</th><th>Loại</th><th>Tiêu đề</th><th class="text-right">Ký tự</th><th>Nạp lúc</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="d in docs" :key="d.id" class="border-t border-default">
              <td class="py-1 font-medium">{{ d.ticker }}</td>
              <td><UBadge size="sm" variant="subtle">{{ d.doc_type }}</UBadge></td>
              <td class="max-w-sm truncate">{{ d.title }}</td>
              <td class="text-right">{{ number(d.chars) }}</td>
              <td class="text-xs">{{ dateTime(d.created_at) }}</td>
              <td class="text-right">
                <UButton size="xs" color="error" variant="ghost" icon="i-lucide-trash-2"
                         @click="xoa(d)" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>
  </div>
</template>
