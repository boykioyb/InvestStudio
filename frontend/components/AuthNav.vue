<script setup lang="ts">
/**
 * Ô đăng nhập/đăng xuất hiển thị trên header.
 *
 * Chưa đăng nhập → nút "Đăng nhập" (giữ đường dẫn hiện tại để quay lại sau).
 * Đã đăng nhập → tên người dùng + nút "Thoát". Chỉ hiển thị và gọi composable —
 * không chứa logic nghiệp vụ.
 */
import { LogIn, User } from 'lucide-vue-next'

const { user, isLoggedIn, ensureLoaded, logout } = useAuth()
const route = useRoute()

onMounted(ensureLoaded)

async function onLogout(): Promise<void> {
  await logout()
  if (route.path !== '/') void navigateTo('/')
}
</script>

<template>
  <div class="auth-nav">
    <template v-if="isLoggedIn">
      <span class="who" :title="user?.email"><User /> {{ user?.display_name }}</span>
      <button type="button" class="chip" @click="onLogout">Thoát</button>
    </template>
    <NuxtLink
      v-else
      class="chip login"
      :to="{ path: '/dang-nhap', query: { next: route.fullPath } }"
    >
      <LogIn /> Đăng nhập
    </NuxtLink>
  </div>
</template>

<style scoped>
.auth-nav {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.who {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip {
  font-size: 11.5px;
  font-weight: 700;
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--text);
  border-radius: 20px;
  padding: 4px 10px;
  cursor: pointer;
  white-space: nowrap;
  text-decoration: none;
}

.chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.chip.login {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
