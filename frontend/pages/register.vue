<script setup lang="ts">
/** Trang đăng ký. Thành công là đăng nhập luôn (backend đặt cookie ngay). */
const { register, pending, error, solvingChallenge, ensureLoaded, isLoggedIn } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const displayName = ref('')
const localError = ref('')

useHead({ title: 'Đăng ký — Phân Tích Mã' })

const nextPath = computed(() => isSafeNext(String(route.query.next || '/')))

onMounted(async () => {
  await ensureLoaded()
  if (isLoggedIn.value) void navigateTo(nextPath.value)
})

async function submit(): Promise<void> {
  localError.value = ''
  if (password.value.length < 10) {
    localError.value = 'Mật khẩu cần tối thiểu 10 ký tự.'
    return
  }
  if (await register(email.value.trim(), password.value, displayName.value.trim())) {
    void navigateTo(nextPath.value)
  }
}
</script>

<template>
  <div class="wrap auth reg">
    <NuxtLink to="/analysis" class="back">← Về phân tích mã</NuxtLink>

    <div class="card auth-card">
      <div class="grid">
        <!-- Cột lợi ích: cho biết tạo tài khoản để làm gì -->
        <aside class="perks">
          <div class="brand"><span class="mark">◆</span> Phân Tích Mã</div>
          <h2>Tạo tài khoản miễn phí</h2>
          <p class="lead">Mở khoá các tính năng theo dõi riêng cho bạn.</p>

          <ul class="benefits">
            <li>
              <span class="ic" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="m12 3 2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.2l1-5.8L3.5 9.2l5.9-.9L12 3Z" />
                </svg>
              </span>
              <div><b>Lưu mã theo dõi</b><span>Danh mục & watchlist của riêng bạn, còn nguyên khi quay lại.</span></div>
            </li>
            <li>
              <span class="ic" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2Z" />
                </svg>
              </span>
              <div><b>Trợ lý hỏi–đáp</b><span>Hỏi sâu về một mã và nhận trả lời có dẫn số liệu.</span></div>
            </li>
            <li>
              <span class="ic" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" />
                </svg>
              </span>
              <div><b>Email cảnh báo</b><span>Nhận thư khi mã bạn theo dõi có biến động đáng chú ý.</span></div>
            </li>
          </ul>

          <p class="rea">Miễn phí · không cần thẻ · huỷ bất cứ lúc nào.</p>
        </aside>

        <!-- Cột form -->
        <div class="formcol">
          <h1>Đăng ký</h1>
          <p class="note">Chỉ cần email và mật khẩu là xong.</p>

          <p v-if="localError || error" class="msg error" role="alert">{{ localError || error }}</p>

          <form class="stack" @submit.prevent="submit">
            <div class="fg">
              <label for="email">Email</label>
              <input id="email" v-model="email" type="email" autocomplete="email"
                     required placeholder="ban@vidu.com" />
            </div>
            <div class="fg">
              <label for="name">Tên hiển thị <span class="muted">(tùy chọn)</span></label>
              <input id="name" v-model="displayName" type="text" autocomplete="nickname"
                     maxlength="120" placeholder="Tên bạn muốn hiển thị" />
            </div>
            <div class="fg">
              <label for="password">Mật khẩu</label>
              <input id="password" v-model="password" type="password"
                     autocomplete="new-password" required minlength="10" placeholder="••••••••" />
              <span class="hint">Tối thiểu 10 ký tự.</span>
            </div>
            <button class="btn primary" type="submit" :disabled="pending">
              {{ solvingChallenge ? 'Đang xác minh chống tự động…'
                : pending ? 'Đang tạo tài khoản…' : 'Tạo tài khoản' }}
            </button>
          </form>

          <AuthSocial :next="nextPath" />

          <p class="note switch">
            Đã có tài khoản?
            <NuxtLink :to="{ path: '/login', query: route.query }">Đăng nhập</NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth.reg {
  max-width: 760px;
}

.back {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 13px;
  text-decoration: none;
}

/* card bọc cả hai cột — bỏ padding để mỗi cột tự đặt */
.auth-card {
  padding: 0;
  overflow: hidden;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.brand {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 16px;
}

.brand .mark {
  color: var(--accent);
}

/* ---- cột lợi ích ---- */
.perks {
  padding: 28px 26px;
  border-right: 1px solid var(--line);
  background: linear-gradient(160deg, rgba(90, 200, 255, 0.07), rgba(168, 130, 255, 0.06));
}

.perks h2 {
  margin: 0 0 6px;
  font-size: 19px;
}

.perks .lead {
  margin: 0 0 20px;
  color: var(--text-2);
  font-size: 13px;
}

.benefits {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.benefits li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.benefits .ic {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: rgba(90, 200, 255, 0.12);
  color: var(--accent);
}

.benefits .ic svg {
  width: 17px;
  height: 17px;
}

.benefits b {
  display: block;
  font-size: 13.5px;
  color: var(--text);
}

.benefits span {
  display: block;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
  margin-top: 2px;
}

.rea {
  margin: 22px 0 0;
  font-size: 11.5px;
  color: var(--muted-2);
}

/* ---- cột form ---- */
.formcol {
  padding: 28px 26px;
}

.formcol h1 {
  margin: 0 0 4px;
  font-size: 20px;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

.stack .fg input {
  width: 100%;
  font-size: 14.5px;
  padding: 11px 13px;
}

.stack .btn.primary {
  width: 100%;
  margin-top: 6px;
  padding: 12px;
  font-size: 14.5px;
}

.switch {
  margin-top: 18px;
  text-align: center;
}

/* xếp chồng trên màn hẹp */
@media (max-width: 720px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .perks {
    border-right: none;
    border-bottom: 1px solid var(--line);
  }
}
</style>
