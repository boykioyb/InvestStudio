<script setup lang="ts">
/**
 * Thanh điều hướng dùng chung cho mọi trang.
 * Mục đang mở tự sáng theo route. Slot mặc định để trang chèn nội dung giữa
 * (VD ô tìm kiếm); AuthNav luôn nằm bên phải.
 */
const route = useRoute()
const LINKS = [
  { to: '/', label: 'Home' },
  { to: '/danh-muc', label: 'Danh mục' },
  { to: '/phan-tich', label: 'Phân tích' },
  { to: '/danh-sach', label: 'Danh sách' },
  { to: '/theo-doi', label: 'Theo dõi' },
  { to: '/tro-ly', label: 'Trợ lý' }
]
const isOn = (to: string) => to === '/' ? route.path === '/' : route.path.startsWith(to)
</script>

<template>
  <header class="app-header">
    <NuxtLink to="/" class="brand"><span class="logo">IS</span> InvestStudio <small>· Terminal</small></NuxtLink>
    <nav class="tabs" aria-label="Điều hướng chính">
      <NuxtLink v-for="l in LINKS" :key="l.to" :to="l.to" :class="{ on: isOn(l.to) }">{{ l.label }}</NuxtLink>
    </nav>
    <div class="mid"><slot /></div>
    <div class="right"><AuthNav /></div>
  </header>
</template>

<style scoped>
.app-header { position: sticky; top: 0; z-index: 30; display: flex; align-items: center; gap: 16px;
  padding: 13px 26px; border-bottom: 1px solid var(--line);
  background: rgba(7, 11, 22, 0.72); backdrop-filter: blur(14px) saturate(1.4); }
.brand { display: flex; align-items: center; gap: 11px; font-weight: 800; font-size: 16px; text-decoration: none; color: var(--text); white-space: nowrap; }
.brand small { color: var(--muted); font-weight: 500; }
.logo { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
  background: conic-gradient(from 210deg, var(--accent), var(--accent2), var(--good), var(--accent));
  box-shadow: 0 0 22px -4px var(--accent); color: #04121f; font-weight: 900; }
.tabs { display: flex; gap: 4px; }
.tabs a { padding: 8px 14px; border-radius: 10px; color: var(--muted); text-decoration: none; font-size: 13.5px; font-weight: 600; transition: 0.18s; }
.tabs a:hover { color: var(--text); background: var(--panel-hi); }
.tabs a.on { color: var(--text); background: var(--panel); border: 1px solid var(--line-hi); }
.mid { flex: 1; display: flex; justify-content: center; min-width: 0; }
.right { margin-left: auto; }
.mid:empty + .right,
.mid:empty { margin-left: auto; }
@media (max-width: 900px) { .tabs { display: none; } }
</style>
