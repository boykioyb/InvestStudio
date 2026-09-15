<script setup lang="ts">
/**
 * Ô đăng nhập/đăng xuất hiển thị trên header.
 *
 * Chưa đăng nhập → nút "Đăng nhập" (giữ đường dẫn hiện tại để quay lại sau).
 * Đã đăng nhập → tên người dùng + nút "Thoát". Chỉ hiển thị và gọi composable —
 * không chứa logic nghiệp vụ.
 */
import { LogIn, User } from 'lucide-vue-next'

const { user, isLoggedIn, ready, ensureLoaded, logout } = useAuth()
const route = useRoute()

onMounted(ensureLoaded)

async function onLogout(): Promise<void> {
  await logout()
  if (route.path !== '/') void navigateTo('/')
}
</script>

<template>
  <div class="auth-nav">
    <!-- Chưa biết trạng thái (đang gọi /me) → chỗ trống trung tính, KHÔNG hiện
         "Đăng nhập" rồi lật sang tên user gây nháy khi reload. -->
    <span v-if="!ready" class="auth-skeleton" aria-hidden="true" />
    <template v-else-if="isLoggedIn">
      <NotificationBell />
      <NuxtLink class="who" to="/account" :title="`${user?.email} · mở trang tài khoản`">
        <User /> {{ user?.display_name }}
      </NuxtLink>
      <button type="button" class="chip" @click="onLogout">Thoát</button>
    </template>
    <NuxtLink
      v-else
      class="chip login"
      :to="{ path: '/login', query: { next: route.fullPath } }"
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

/* Chỗ giữ trạng thái trong lúc chờ /me — bằng cỡ chip để không giật layout. */
.auth-skeleton {
  display: inline-block;
  width: 88px;
  height: 26px;
  border-radius: 20px;
  background: var(--panel2);
  border: 1px solid var(--line);
  opacity: 0.5;
}

.who {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}

.who:hover {
  text-decoration: underline;
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
