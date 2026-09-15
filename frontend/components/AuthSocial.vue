<script setup lang="ts">
/**
 * Khối "đăng nhập ngoài" dùng chung cho trang đăng nhập & đăng ký.
 * Chỉ có Google. Nút luôn hiện; nếu backend chưa cấu hình thì kèm dòng nhắc và
 * bấm vào sẽ báo rõ (không im lặng).
 */
const props = withDefaults(defineProps<{ next?: string }>(), { next: '/' })
const { googleEnabled, loadOauthConfig, startGoogle } = useAuth()

onMounted(loadOauthConfig)
</script>

<template>
  <div class="social">
    <div class="divider"><span>hoặc</span></div>

    <button type="button" class="gbtn" @click="startGoogle(props.next)">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.24 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
        <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84Z" />
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
      </svg>
      <span>Tiếp tục với Google</span>
    </button>

    <p v-if="!googleEnabled" class="cfg-note">
      Đăng nhập Google sẽ hoạt động khi quản trị viên cấu hình khóa OAuth.
    </p>
  </div>
</template>

<style scoped>
.social {
  margin-top: 18px;
}

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0 16px;
  color: var(--muted);
  font-size: 12px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

.gbtn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--line-hi);
  background: #fff;
  color: #1f2328;
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.16s, transform 0.16s;
}

.gbtn:hover {
  filter: brightness(0.97);
  transform: translateY(-1px);
}

.cfg-note {
  margin: 10px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: var(--muted-2);
}
</style>
