<script setup lang="ts">
/**
 * Quên mật khẩu — nhập email để nhận liên kết đặt lại.
 *
 * Backend cố tình trả lời GIỐNG NHAU dù email có tồn tại hay không, nên màn này
 * cũng không được nói "email không tồn tại": làm vậy là biến trang này thành
 * công cụ dò xem ai đã đăng ký.
 */
const { forgotPassword, pending, error } = useAuth()

useHead({ title: 'Quên mật khẩu — Phân Tích Mã' })

const email = ref('')
const daGui = ref('')

async function submit(): Promise<void> {
  daGui.value = await forgotPassword(email.value.trim())
}
</script>

<template>
  <div class="wrap auth">
    <NuxtLink to="/login" class="back">← Về đăng nhập</NuxtLink>

    <div class="card">
      <h1>Quên mật khẩu</h1>

      <template v-if="daGui">
        <p class="msg ok" role="status">{{ daGui }}</p>
        <p class="note">
          Liên kết đặt lại sống 30 phút và chỉ dùng được một lần. Không thấy thư thì
          kiểm tra cả mục spam.
        </p>
      </template>

      <template v-else>
        <p class="note">Nhập email đã đăng ký, chúng tôi gửi liên kết đặt mật khẩu mới.</p>
        <p v-if="error" class="msg error" role="alert">{{ error }}</p>

        <form class="stack" @submit.prevent="submit">
          <div class="fg">
            <label for="email">Email</label>
            <input id="email" v-model="email" type="email" autocomplete="email"
                   required placeholder="ban@vidu.com" />
          </div>
          <button class="btn primary" type="submit" :disabled="pending">
            {{ pending ? 'Đang gửi…' : 'Gửi liên kết đặt lại' }}
          </button>
        </form>
      </template>
    </div>
  </div>
</template>

<style scoped>
.auth { max-width: 440px; }
.back { display: inline-block; margin-bottom: 12px; font-size: 13px; text-decoration: none; }
h1 { margin: 0 0 6px; font-size: 22px; }
.stack { display: flex; flex-direction: column; gap: 14px; margin-top: 16px; }
.stack .fg input { font-size: 15px; padding: 11px 13px; }
</style>
