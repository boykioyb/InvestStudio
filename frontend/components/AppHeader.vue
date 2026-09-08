<script setup lang="ts">
/**
 * Thanh điều hướng dùng chung cho mọi trang.
 *
 * Desktop: logo + tab điều hướng + AuthNav bên phải.
 * Mobile (< 900px): logo + nút hamburger; menu mở ra dạng drawer trượt phải.
 * Mục đang mở tự sáng theo route. Slot mặc định để trang chèn nội dung giữa
 * (VD ô tìm kiếm); AuthNav luôn nằm bên phải.
 */
import { Menu, X } from 'lucide-vue-next'

const route = useRoute()
const LINKS = [
  { to: '/', label: 'Trang chủ' },
  { to: '/portfolio', label: 'Danh mục' },
  { to: '/analysis', label: 'Phân tích' },
  { to: '/screener', label: 'Danh sách mã' },
  { to: '/watchlist', label: 'Theo dõi' },
  { to: '/assistant', label: 'Trợ lý' },
  { to: '/scoring', label: 'Cách chấm điểm' }
]
const isOn = (to: string): boolean => (to === '/' ? route.path === '/' : route.path.startsWith(to))

const menuOpen = ref(false)
//  Đổi trang thì đóng drawer để không che nội dung mới.
watch(() => route.fullPath, () => { menuOpen.value = false })
</script>

<template>
  <header class="app-header">
    <NuxtLink to="/" class="brand"><span class="logo">PT</span> Phân Tích Mã <small>· Terminal</small></NuxtLink>
    <nav class="tabs" aria-label="Điều hướng chính">
      <NuxtLink v-for="l in LINKS" :key="l.to" :to="l.to" :class="{ on: isOn(l.to) }">{{ l.label }}</NuxtLink>
    </nav>
    <div class="mid"><slot /></div>
    <div class="right"><AuthNav /></div>

    <!-- mobile: hamburger + drawer -->
    <button
      type="button"
      class="burger"
      :aria-label="menuOpen ? 'Đóng menu' : 'Mở menu'"
      :aria-expanded="menuOpen"
      @click="menuOpen = !menuOpen"
    >
      <X v-if="menuOpen" />
      <Menu v-else />
    </button>

    <div v-if="menuOpen" class="drawer-wrap">
      <div class="scrim" aria-hidden="true" @click="menuOpen = false" />
      <nav class="drawer" aria-label="Điều hướng chính">
        <NuxtLink v-for="l in LINKS" :key="l.to" :to="l.to" :class="{ on: isOn(l.to) }">
          {{ l.label }}
          <span v-if="isOn(l.to)" class="mark">Đang xem</span>
        </NuxtLink>
        <div class="sep" />
        <AuthNav />
        <p class="note">
          Đăng nhập để lưu mã theo dõi và hỏi trợ lý. Xem phân tích không cần tài khoản.
        </p>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.app-header { position: sticky; top: 0; z-index: 30; display: flex; align-items: center; gap: 16px;
  padding: 13px 26px; border-bottom: 1px solid var(--line);
  background: rgba(7, 11, 22, 0.86); backdrop-filter: blur(14px) saturate(1.4); }
.brand { display: flex; align-items: center; gap: 11px; font-weight: 800; font-size: 16px; text-decoration: none; color: var(--text); white-space: nowrap; }
.brand small { color: var(--muted); font-weight: 500; }
.logo { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
  background: conic-gradient(from 210deg, var(--accent), var(--accent2), var(--good), var(--accent));
  box-shadow: 0 0 22px -4px var(--accent); color: var(--on-accent); font-weight: 900; }
.tabs { display: flex; gap: 4px; min-width: 0; overflow-x: auto; scrollbar-width: none; }
.tabs a { display: inline-flex; align-items: center; padding: 8px 14px; border-radius: 10px; color: var(--muted);
  text-decoration: none; font-size: 13.5px; font-weight: 600; white-space: nowrap;
  border: 1px solid transparent; transition: 0.18s; }
.tabs a:hover { color: var(--text); background: var(--panel-hi); }
.tabs a.on { color: var(--text); background: rgba(90, 200, 255, 0.12); border-color: rgba(90, 200, 255, 0.45); }
.mid { flex: 1; display: flex; justify-content: center; min-width: 0; }
.right { margin-left: auto; }
.mid:empty + .right,
.mid:empty { margin-left: auto; }

/* mobile */
.burger { display: none; width: 44px; height: 44px; margin-left: auto; border-radius: 10px;
  border: 1px solid transparent; background: none; color: var(--text); place-items: center; cursor: pointer; }
.burger:hover { background: var(--panel-hi); }
.burger :deep(.lucide) { width: 22px; height: 22px; }
.drawer-wrap { position: absolute; top: 100%; left: 0; right: 0; height: calc(100dvh - 100%); z-index: 50; }
.scrim { position: absolute; inset: 0; background: rgba(7, 11, 22, 0.7); }
.drawer { position: absolute; top: 0; right: 0; bottom: 0; width: min(320px, 86%);
  background: var(--panel-deep); border-left: 1px solid var(--line);
  padding: 12px 12px calc(16px + env(safe-area-inset-bottom)); display: flex; flex-direction: column; gap: 4px;
  overflow-y: auto; box-shadow: -20px 0 40px -20px rgba(0, 0, 0, 0.8); }
.drawer a { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 48px;
  padding: 0 14px; border-radius: 10px; text-decoration: none; font-size: 15px; font-weight: 500;
  color: var(--text); border: 1px solid transparent; }
.drawer a:hover { background: var(--panel-hi); }
.drawer a.on { font-weight: 700; background: rgba(90, 200, 255, 0.12); border-color: rgba(90, 200, 255, 0.45); }
.drawer .mark { font-size: 12px; color: var(--muted-2); font-weight: 400; }
.drawer .sep { height: 1px; background: var(--line); margin: 8px 0; }
/* Nút đăng nhập trong drawer to bằng cỡ ngón tay như thiết kế. */
.drawer :deep(.auth-nav) { justify-content: center; }
.drawer :deep(.chip) { min-height: 48px; display: inline-flex; align-items: center;
  justify-content: center; gap: 8px; padding: 0 18px; font-size: 14px; border-radius: 10px; }
.drawer .note { margin: 10px 4px 0; font-size: 12.5px; color: var(--muted-2); line-height: 1.5; }

@media (max-width: 900px) {
  .app-header { padding: 8px 10px 8px 16px; gap: 8px; }
  .tabs,
  .mid,
  .right { display: none; }
  .burger { display: grid; }
}
</style>
