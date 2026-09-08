<script setup lang="ts">
/**
 * Trang lỗi dùng chung (Nuxt tự dùng cho 404/500 và lỗi chưa bắt).
 *
 * Nguyên tắc: nói ĐÚNG chuyện gì xảy ra và cho một lối đi tiếp. Người dùng gõ
 * nhầm mã cổ phiếu vào URL không cần biết "404", họ cần một ô để nhập lại.
 */
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()

const laKhongTonTai = computed(() => props.error?.statusCode === 404)

useHead({ title: laKhongTonTai.value ? 'Không tìm thấy trang' : 'Có lỗi xảy ra' })

const ma = ref('')

function phanTich(): void {
  const code = ma.value.trim().toUpperCase()
  if (code) void clearError({ redirect: `/analysis?symbol=${code}` })
}
</script>

<template>
  <div class="wrap loi">
    <div class="card">
      <p class="code">{{ error?.statusCode || '' }}</p>

      <template v-if="laKhongTonTai">
        <h1>Không có trang này</h1>
        <p class="note">
          Đường dẫn bạn mở không tồn tại. Nếu đang tìm một mã cổ phiếu, nhập mã vào đây:
        </p>
        <form class="tim" @submit.prevent="phanTich">
          <input v-model="ma" maxlength="12" placeholder="VD: FPT" aria-label="Mã cổ phiếu"
                 autocapitalize="characters" spellcheck="false" />
          <button class="btn primary" type="submit">Phân tích →</button>
        </form>
      </template>

      <template v-else>
        <h1>Hệ thống đang trục trặc</h1>
        <p class="note">
          Lỗi nằm ở phía chúng tôi, không phải do bạn làm sai. Thử tải lại sau ít phút —
          dữ liệu bạn đã lưu vẫn còn nguyên.
        </p>
        <p v-if="error?.message" class="chi-tiet">{{ error.message }}</p>
      </template>

      <div class="loi-nav">
        <NuxtLink to="/" class="btn" @click="() => clearError()">← Về trang chủ</NuxtLink>
        <NuxtLink to="/screener" class="btn">Danh sách mã</NuxtLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.loi { max-width: 520px; margin-top: 12vh; }
.code { margin: 0; font-size: 40px; font-weight: 800; color: var(--muted); opacity: 0.5; }
h1 { margin: 4px 0 8px; font-size: 22px; }
.tim { display: flex; gap: 8px; margin-top: 14px; }
.tim input { flex: 1; padding: 10px 12px; font-size: 15px; text-transform: uppercase; }
.chi-tiet { margin-top: 10px; font-size: 12px; color: var(--muted); word-break: break-word; }
.loi-nav { display: flex; gap: 10px; margin-top: 18px; }
</style>
