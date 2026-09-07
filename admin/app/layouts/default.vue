<script setup lang="ts">
const route = useRoute()
const me = useAdminUser()

async function dangXuat() {
  await $fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
  me.value = null
  await navigateTo('/dang-nhap')
}

const links = [
  { label: 'Tổng quan', icon: 'i-lucide-gauge', to: '/' },
  { label: 'Người dùng', icon: 'i-lucide-users', to: '/nguoi-dung' },
  { label: 'Cài đặt', icon: 'i-lucide-sliders-horizontal', to: '/cai-dat' },
  { label: 'Nhật ký', icon: 'i-lucide-scroll-text', to: '/nhat-ky' }
]
</script>

<template>
  <div class="min-h-screen bg-elevated/40">
    <div class="flex">
      <aside class="hidden md:flex w-60 shrink-0 flex-col gap-1 border-r border-default p-4 min-h-screen">
        <div class="px-2 pb-4">
          <p class="text-sm font-semibold">InvestStudio</p>
          <p class="text-xs text-muted">Khu quản trị</p>
        </div>
        <UButton
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          :icon="link.icon"
          :label="link.label"
          :color="route.path === link.to ? 'primary' : 'neutral'"
          :variant="route.path === link.to ? 'soft' : 'ghost'"
          class="justify-start"
        />
        <div class="mt-auto space-y-2 pt-4">
          <p class="px-2 text-xs text-muted">Mọi thao tác ghi đều được lưu nhật ký.</p>
          <div v-if="me" class="border-t border-default px-2 pt-3">
            <p class="truncate text-xs">{{ me.email }}</p>
            <UButton
              icon="i-lucide-log-out" label="Đăng xuất" size="xs" variant="ghost"
              color="neutral" class="mt-1 justify-start" @click="dangXuat"
            />
          </div>
        </div>
      </aside>

      <main class="flex-1 min-w-0 p-4 md:p-6">
        <nav class="md:hidden mb-4 flex gap-2 overflow-x-auto">
          <UButton
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            :label="link.label"
            size="xs"
            :variant="route.path === link.to ? 'soft' : 'ghost'"
          />
        </nav>
        <slot />
      </main>
    </div>
  </div>
</template>
