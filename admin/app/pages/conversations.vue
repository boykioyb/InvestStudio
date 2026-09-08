<script setup lang="ts">
/**
 * Hội thoại: xem đầy đủ nội dung người dùng hỏi trợ lý + tìm toàn văn.
 *
 * Mỗi lần mở nội dung của một cuộc, backend ghi một dòng nhật ký kiểm toán.
 * Nói rõ điều đó ngay trên màn hình để người vận hành biết mình đang để lại vết.
 */
const api = useAdminApi()
const { dateTime, number } = useAdminFormat()

const tuKhoa = ref('')
const dangTim = ref(false)
const ketQuaTim = ref<any[] | null>(null)

const { data: conversations, pending, refresh } = await useAsyncData('conversations',
  () => api.get<any[]>('/admin/conversations?limit=100'))

const dangMo = ref<any | null>(null)
const tinNhan = ref<any[]>([])
const dangTai = ref(false)

async function mo(conv: any) {
  dangMo.value = conv
  dangTai.value = true
  try {
    tinNhan.value = await api.get<any[]>(`/admin/conversations/${conv.id}/messages`)
  } finally {
    dangTai.value = false
  }
}

async function tim() {
  if (tuKhoa.value.trim().length < 2) return
  dangTim.value = true
  try {
    ketQuaTim.value = await api.get<any[]>(
      `/admin/chat/search?q=${encodeURIComponent(tuKhoa.value.trim())}`)
  } finally {
    dangTim.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-semibold">Hội thoại</h1>
      <p class="text-sm text-muted">
        Mở nội dung của một cuộc sẽ ghi một dòng vào <NuxtLink to="/audit" class="underline">nhật ký kiểm toán</NuxtLink>.
      </p>
    </div>

    <div class="flex flex-wrap gap-2">
      <UInput v-model="tuKhoa" placeholder="Tìm toàn văn trong câu hỏi và câu trả lời…"
              icon="i-lucide-search" class="w-96" @keydown.enter="tim" />
      <UButton :loading="dangTim" @click="tim">Tìm</UButton>
      <UButton v-if="ketQuaTim" variant="ghost" @click="ketQuaTim = null">Xóa kết quả</UButton>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()" />
    </div>

    <UCard v-if="ketQuaTim">
      <template #header>
        <span class="font-medium">{{ ketQuaTim.length }} kết quả cho "{{ tuKhoa }}"</span>
      </template>
      <p v-if="!ketQuaTim.length" class="text-sm text-muted">Không tìm thấy gì khớp.</p>
      <ul v-else class="divide-y divide-default">
        <li v-for="h in ketQuaTim" :key="h.message_id" class="py-2 text-sm">
          <div class="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span>{{ dateTime(h.at) }}</span>
            <span>{{ h.user_email }}</span>
            <UBadge v-if="h.ticker" size="sm" variant="subtle">{{ h.ticker }}</UBadge>
            <UButton v-if="h.conversation_id" size="xs" variant="link"
                     @click="mo({ id: h.conversation_id, title: `Cuộc #${h.conversation_id}` })">
              mở cuộc
            </UButton>
          </div>
          <p class="mt-1">{{ h.snippet }}</p>
        </li>
      </ul>
    </UCard>

    <div class="grid gap-4 lg:grid-cols-[360px_1fr]">
      <UCard>
        <template #header><span class="font-medium">Cuộc trò chuyện gần nhất</span></template>
        <p v-if="!conversations?.length" class="text-sm text-muted">Chưa có cuộc nào.</p>
        <ul v-else class="divide-y divide-default">
          <li v-for="c in conversations" :key="c.id">
            <button type="button" class="w-full py-2 text-left text-sm hover:text-primary"
                    @click="mo(c)">
              <p class="truncate font-medium">{{ c.title || `Cuộc #${c.id}` }}</p>
              <p class="text-xs text-muted">
                {{ c.user_email }} · {{ number(c.message_count) }} lượt · {{ dateTime(c.updated_at) }}
                <span v-if="c.ticker"> · {{ c.ticker }}</span>
              </p>
            </button>
          </li>
        </ul>
      </UCard>

      <UCard>
        <template #header>
          <span class="font-medium">
            {{ dangMo ? (dangMo.title || `Cuộc #${dangMo.id}`) : 'Chọn một cuộc để xem' }}
          </span>
        </template>

        <p v-if="!dangMo" class="text-sm text-muted">
          Nội dung hội thoại hiện ở đây sau khi bạn chọn một cuộc bên trái.
        </p>
        <p v-else-if="dangTai" class="text-sm text-muted">Đang tải…</p>
        <p v-else-if="!tinNhan.length" class="text-sm text-muted">Cuộc này chưa có tin nhắn.</p>

        <ul v-else class="space-y-4">
          <li v-for="m in tinNhan" :key="m.id" class="text-sm">
            <p class="text-xs text-muted">
              {{ dateTime(m.at) }}<span v-if="m.ticker"> · {{ m.ticker }}</span>
            </p>
            <p class="mt-1 rounded bg-elevated p-2"><b>Hỏi:</b> {{ m.question }}</p>
            <p class="mt-1 whitespace-pre-wrap p-2">{{ m.answer }}</p>
            <details v-if="m.citations?.length" class="mt-1">
              <summary class="cursor-pointer text-xs text-muted">
                {{ m.citations.length }} nguồn trích dẫn
              </summary>
              <ul class="mt-1 space-y-1 text-xs text-muted">
                <li v-for="(c, i) in m.citations" :key="i">{{ c.ticker }} · {{ c.title }}</li>
              </ul>
            </details>
            <p v-if="m.attachments?.length" class="mt-1 text-xs text-muted">
              📎 {{ m.attachments.map((a: any) => a.filename).join(', ') }}
            </p>
          </li>
        </ul>
      </UCard>
    </div>
  </div>
</template>
