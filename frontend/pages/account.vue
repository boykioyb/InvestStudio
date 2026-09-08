<script setup lang="ts">
/** Tài khoản: thông tin, đổi mật khẩu, hạn mức trợ lý, và xóa tài khoản. */
definePageMeta({ middleware: 'auth' })

const { user, changePassword, deleteAccount, resendVerification, setAlertEmail,
        pending, error } = useAuth()
const { quota, load: loadQuota } = useChatQuota()

useHead({ title: 'Tài khoản — Phân Tích Mã' })

const MAT_KHAU_TOI_THIEU = 10

const cu = ref('')
const moi = ref('')
const doiXong = ref('')
const thongBaoThu = ref('')

//  Xóa tài khoản là không hoàn tác được → bắt gõ đúng email, không chỉ bấm OK.
const xacNhanXoa = ref('')
const dangMoXoa = ref(false)
const khopEmail = computed(() => xacNhanXoa.value.trim().toLowerCase() === user.value?.email)
const matKhauXoa = ref('')

onMounted(loadQuota)

async function doiMatKhau(): Promise<void> {
  doiXong.value = ''
  if (await changePassword(cu.value, moi.value)) {
    cu.value = ''
    moi.value = ''
    //  Đổi mật khẩu thu hồi mọi phiên (kể cả phiên này) — nói thẳng để người
    //  dùng không hoang mang khi thao tác tiếp bị đá ra đăng nhập.
    doiXong.value = 'Đã đổi mật khẩu. Mọi thiết bị khác đã bị đăng xuất; bạn cũng cần đăng nhập lại.'
    setTimeout(() => navigateTo('/login?next=/account'), 2500)
  }
}

async function xoa(): Promise<void> {
  if (!khopEmail.value) return
  if (await deleteAccount(matKhauXoa.value)) void navigateTo('/')
}
</script>

<template>
  <div class="wrap acc">
    <AppHeader />

    <h1>Tài khoản</h1>

    <section class="card">
      <h2>Thông tin</h2>
      <dl class="info">
        <dt>Email</dt>
        <dd>
          {{ user?.email }}
          <span v-if="user?.email_verified" class="tag ok">đã xác minh</span>
          <template v-else>
            <span class="tag warn">chưa xác minh</span>
            <button type="button" class="chip" :disabled="pending"
                    @click="resendVerification().then(m => (thongBaoThu = m))">
              Gửi lại thư
            </button>
          </template>
        </dd>
        <dt>Tên hiển thị</dt>
        <dd>{{ user?.display_name }}</dd>
        <dt>Email cảnh báo</dt>
        <dd>
          <!-- Người dùng đặt ngưỡng thì mặc định muốn được báo; ai không thích
               thì tắt ở đây thay vì phải đi tìm trong thư rác. -->
          <label class="cong-tac">
            <input type="checkbox" :checked="user?.alert_email"
                   :disabled="pending"
                   @change="setAlertEmail(($event.target as HTMLInputElement).checked)" />
            Gửi email khi mã theo dõi chạm ngưỡng giá hoặc điểm
          </label>
          <span v-if="!user?.email_verified" class="tag warn">cần xác minh email trước</span>
        </dd>
        <dt>Hạn mức trợ lý hôm nay</dt>
        <dd>
          <template v-if="quota">
            Còn <b>{{ quota.remaining }}</b>/{{ quota.limit }} lượt
            <span v-if="quota.level !== 'ok'" class="tag warn">
              hệ thống đang tiết kiệm hạn mức chung
            </span>
          </template>
          <span v-else class="muted">—</span>
        </dd>
      </dl>
      <p v-if="thongBaoThu" class="msg ok" role="status">{{ thongBaoThu }}</p>
    </section>

    <section class="card">
      <h2>Đổi mật khẩu</h2>
      <p v-if="error" class="msg error" role="alert">{{ error }}</p>
      <p v-if="doiXong" class="msg ok" role="status">{{ doiXong }}</p>
      <form class="stack" @submit.prevent="doiMatKhau">
        <div class="fg">
          <label for="cu">Mật khẩu hiện tại</label>
          <input id="cu" v-model="cu" type="password" autocomplete="current-password" required />
        </div>
        <div class="fg">
          <label for="moi">Mật khẩu mới</label>
          <input id="moi" v-model="moi" type="password" autocomplete="new-password"
                 :minlength="MAT_KHAU_TOI_THIEU" required />
          <small class="muted">Tối thiểu {{ MAT_KHAU_TOI_THIEU }} ký tự.</small>
        </div>
        <button class="btn primary" type="submit" :disabled="pending">Đổi mật khẩu</button>
      </form>
    </section>

    <section class="card nguy-hiem">
      <h2>Xóa tài khoản</h2>
      <p class="note">
        Xóa vĩnh viễn tài khoản cùng toàn bộ mã theo dõi, hội thoại với trợ lý và tệp
        đính kèm. <b>Không hoàn tác được.</b>
      </p>

      <button v-if="!dangMoXoa" type="button" class="btn xoa" @click="dangMoXoa = true">
        Tôi muốn xóa tài khoản
      </button>

      <form v-else class="stack" @submit.prevent="xoa">
        <div class="fg">
          <label for="xacnhan">Gõ lại email <b>{{ user?.email }}</b> để xác nhận</label>
          <input id="xacnhan" v-model="xacNhanXoa" autocomplete="off" />
        </div>
        <div class="fg">
          <label for="mkxoa">Mật khẩu</label>
          <input id="mkxoa" v-model="matKhauXoa" type="password" autocomplete="current-password" />
        </div>
        <div class="hang">
          <button class="btn xoa" type="submit" :disabled="!khopEmail || !matKhauXoa || pending">
            Xóa vĩnh viễn
          </button>
          <button class="btn" type="button" @click="dangMoXoa = false">Thôi</button>
        </div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.acc { max-width: 720px; }
h1 { margin: 18px 0 14px; font-size: 24px; }
h2 { margin: 0 0 10px; font-size: 16px; }
.card + .card { margin-top: 16px; }

.info { display: grid; grid-template-columns: 160px 1fr; gap: 8px 12px; margin: 0; font-size: 14px; }
.info dt { color: var(--muted); }
.info dd { margin: 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.cong-tac { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.cong-tac input { width: 15px; height: 15px; }
.tag { padding: 1px 7px; border-radius: 999px; font-size: 11px; }
.tag.ok { color: var(--good); border: 1px solid color-mix(in oklab, var(--good) 45%, transparent); }
.tag.warn { color: var(--warn, #d9a441); border: 1px solid color-mix(in oklab, var(--warn, #d9a441) 45%, transparent); }

.stack { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.hang { display: flex; gap: 10px; }
.fg small { display: block; margin-top: 5px; font-size: 12px; }

.nguy-hiem { border-color: color-mix(in oklab, var(--bad) 35%, var(--line)); }
.btn.xoa { color: var(--bad); border-color: color-mix(in oklab, var(--bad) 45%, transparent); }

@media (max-width: 620px) {
  .info { grid-template-columns: 1fr; gap: 2px 0; }
  .info dt { margin-top: 8px; }
}
</style>
