<script setup lang="ts">
/**
 * Dải nhắc "hãy xác minh email" — hiện ở mọi trang khi tài khoản chưa xác minh.
 *
 * Vì sao cần: backend chặn trợ lý và upload ở tài khoản chưa xác minh
 * (require_verified). Không có dải này thì người dùng chỉ thấy lỗi 403 lúc bấm
 * hỏi, không hiểu vì sao và cũng không biết bấm gửi lại thư ở đâu.
 */
const { user, isLoggedIn, ensureLoaded, resendVerification, pending } = useAuth()
const route = useRoute()

const daTat = ref(false)
const thongBao = ref('')

onMounted(ensureLoaded)

//  Không hiện trên chính trang xác minh (ở đó đã có nút gửi lại rồi).
const hien = computed(() =>
  isLoggedIn.value && user.value?.email_verified === false
  && !daTat.value && route.path !== '/verify-email')

async function guiLai(): Promise<void> {
  thongBao.value = await resendVerification()
}
</script>

<template>
  <div v-if="hien" class="verify-bar" role="status">
    <span class="txt">
      <strong>Chưa xác minh email.</strong>
      Bấm liên kết trong thư gửi tới <b>{{ user?.email }}</b> để mở khóa trợ lý.
    </span>
    <span class="act">
      <button type="button" class="chip" :disabled="pending" @click="guiLai">
        {{ pending ? 'Đang gửi…' : 'Gửi lại thư' }}
      </button>
      <button type="button" class="chip ghost" aria-label="Ẩn nhắc nhở" @click="daTat = true">✕</button>
    </span>
    <span v-if="thongBao" class="done">{{ thongBao }}</span>
  </div>
</template>

<style scoped>
.verify-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  font-size: 13px;
  color: var(--text);
  background: color-mix(in oklab, var(--warn, #d9a441) 16%, var(--panel));
  border-bottom: 1px solid color-mix(in oklab, var(--warn, #d9a441) 40%, transparent);
}

.txt { flex: 1 1 320px; }
.act { display: inline-flex; gap: 6px; }
.done { flex-basis: 100%; color: var(--good); }

@media (max-width: 700px) {
  .verify-bar { padding: 8px 12px; font-size: 12px; }
}
</style>
