<script setup lang="ts">
/** Tài khoản: thông tin, đổi mật khẩu, hạn mức trợ lý, và xóa tài khoản.
 *  Bố cục 2 cột: sidebar hồ sơ + điều hướng mục; nội dung bên phải theo mục chọn. */
definePageMeta({ middleware: 'auth' })

const { user, changePassword, deleteAccount, resendVerification, setAlertEmail,
        pending, error } = useAuth()
const { quota, load: loadQuota } = useChatQuota()

useHead({ title: 'Tài khoản — Phân Tích Mã' })

const MAT_KHAU_TOI_THIEU = 10

//  Mục đang xem ở cột phải.
type Muc = 'thong-tin' | 'bao-mat' | 'nguy-hiem'
const muc = ref<Muc>('thong-tin')

//  Tài khoản đăng nhập bằng Google chưa có mật khẩu → ẩn các thao tác cần mật khẩu.
const dungGoogle = computed(() => user.value?.has_password === false)

//  Phiên đăng nhập nạp ở client (cookie httpOnly + /me), nên lần reload đầu
//  `user` còn null → hiện skeleton thay vì để trống rồi mới nhảy ra dữ liệu.
const dangTai = computed(() => !user.value)

//  Chữ cái đầu cho avatar — từ tên hiển thị, lùi về email nếu trống.
const chuDau = computed(() => {
  const nguon = (user.value?.display_name || user.value?.email || '?').trim()
  const tu = nguon.split(/[\s@.]+/).filter(Boolean)
  const chu = (tu[0]?.[0] || '') + (tu.length > 1 ? tu[1][0] : '')
  return chu.toUpperCase() || '?'
})

const cu = ref('')
const moi = ref('')
const doiXong = ref('')
const thongBaoThu = ref('')

//  Xóa tài khoản là không hoàn tác được → bắt gõ đúng email, không chỉ bấm OK.
const xacNhanXoa = ref('')
const dangMoXoa = ref(false)
const khopEmail = computed(() => xacNhanXoa.value.trim().toLowerCase() === user.value?.email)
const matKhauXoa = ref('')

//  Nạp hạn mức NGAY Ở SSR (chạy trên server rồi chuyển sang client) để con số
//  hiện sẵn từ khung hình đầu, không chớp skeleton rồi mới ra "5/5".
await useAsyncData('account-quota', async () => {
  await loadQuota()
  return quota.value
})

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

const MUC_NAV: { key: Muc; nhan: string }[] = [
  { key: 'thong-tin', nhan: 'Thông tin' },
  { key: 'bao-mat', nhan: 'Bảo mật' },
  { key: 'nguy-hiem', nhan: 'Xóa tài khoản' },
]
</script>

<template>
  <div class="wrap acc">
    <AppHeader />

    <h1>Tài khoản</h1>

    <div class="layout">
      <!-- ── Sidebar: hồ sơ + điều hướng ── -->
      <aside class="side">
        <div class="prof">
          <div class="avatar">{{ chuDau }}</div>
          <div class="who">
            <span v-if="dangTai" key="sk-name" class="sk sk-name" />
            <b v-else key="v-name">{{ user?.display_name || '—' }}</b>
            <span v-if="dangTai" key="sk-email" class="sk sk-email" />
            <span v-else key="v-email" class="email" :title="user?.email">{{ user?.email }}</span>
            <span v-if="!dangTai" class="prov">
              <svg v-if="dungGoogle" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.24 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
                <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84Z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
              </svg>
              {{ dungGoogle ? 'Đăng nhập bằng Google' : 'Tài khoản mật khẩu' }}
            </span>
          </div>
        </div>

        <nav class="nav">
          <button v-for="m in MUC_NAV" :key="m.key" type="button"
                  class="nav-item" :class="{ on: muc === m.key, danger: m.key === 'nguy-hiem' }"
                  @click="muc = m.key">
            {{ m.nhan }}
          </button>
        </nav>
      </aside>

      <!-- ── Nội dung ── -->
      <div class="content">
        <!-- Thông tin -->
        <section v-show="muc === 'thong-tin'" class="card">
          <h2>Thông tin</h2>
          <dl class="info">
            <dt>Email</dt>
            <dd>
              <span v-if="dangTai" key="sk-em" class="sk sk-line" />
              <span v-else key="v-em">
                {{ user?.email }}
                <span v-if="user?.email_verified" class="tag ok">đã xác minh</span>
                <template v-else>
                  <span class="tag warn">chưa xác minh</span>
                  <button type="button" class="chip" :disabled="pending"
                          @click="resendVerification().then(m => (thongBaoThu = m))">
                    Gửi lại thư
                  </button>
                </template>
              </span>
            </dd>
            <dt>Tên hiển thị</dt>
            <dd>
              <span v-if="dangTai" key="sk-nm" class="sk sk-short" />
              <span v-else key="v-nm">{{ user?.display_name }}</span>
            </dd>
            <dt>Email cảnh báo</dt>
            <dd>
              <span v-if="dangTai" key="sk-al" class="sk sk-line" />
              <span v-else key="v-al">
                <!-- Người dùng đặt ngưỡng thì mặc định muốn được báo; ai không thích
                     thì tắt ở đây thay vì phải đi tìm trong thư rác. -->
                <label class="cong-tac">
                  <input type="checkbox" :checked="user?.alert_email"
                         :disabled="pending"
                         @change="setAlertEmail(($event.target as HTMLInputElement).checked)" />
                  Gửi email khi mã theo dõi chạm ngưỡng giá hoặc điểm
                </label>
                <span v-if="!user?.email_verified" class="tag warn">cần xác minh email trước</span>
              </span>
            </dd>
            <dt>Hạn mức trợ lý hôm nay</dt>
            <dd>
              <span v-if="quota" key="v-q">
                Còn <b>{{ quota.remaining }}</b>/{{ quota.limit }} lượt
                <span v-if="quota.level !== 'ok'" class="tag warn">
                  hệ thống đang tiết kiệm hạn mức chung
                </span>
              </span>
              <span v-else key="sk-q" class="sk sk-short" />
            </dd>
          </dl>
          <p v-if="thongBaoThu" class="msg ok" role="status">{{ thongBaoThu }}</p>
        </section>

        <!-- Bảo mật -->
        <section v-show="muc === 'bao-mat'" class="card">
          <h2>Bảo mật</h2>

          <div v-if="dungGoogle" class="google-note">
            <p class="note">
              Bạn đăng nhập bằng <b>Google</b> nên tài khoản chưa có mật khẩu riêng.
              Đăng nhập bằng nút Google là cách an toàn nhất — không có mật khẩu để lộ.
            </p>
            <p class="note">Tính năng “đặt mật khẩu” cho tài khoản Google đang được bổ sung.</p>
          </div>

          <template v-else>
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
          </template>
        </section>

        <!-- Vùng nguy hiểm -->
        <section v-show="muc === 'nguy-hiem'" class="card nguy-hiem">
          <h2>Xóa tài khoản</h2>
          <p class="note">
            Xóa vĩnh viễn tài khoản cùng toàn bộ mã theo dõi, hội thoại với trợ lý và tệp
            đính kèm. <b>Không hoàn tác được.</b>
          </p>

          <p v-if="dungGoogle" class="msg warn" role="note">
            Tài khoản Google chưa có mật khẩu nên chưa thể tự xóa ở đây — tính năng đặt
            mật khẩu đang được bổ sung. Liên hệ hỗ trợ nếu bạn cần xóa ngay.
          </p>

          <template v-else>
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
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.acc { max-width: 940px; }
h1 { margin: 18px 0 16px; font-size: 24px; }

/* Skeleton lúc chờ /me — thanh xám bo góc, lấp lánh nhẹ. */
.sk {
  display: inline-block;
  height: 14px;
  border-radius: 6px;
  vertical-align: middle;
  background: linear-gradient(90deg, var(--panel-hi), var(--line-hi), var(--panel-hi));
  background-size: 200% 100%;
  animation: sk-shimmer 1.2s ease-in-out infinite;
}
.sk-name { width: 108px; height: 15px; }
.sk-email { width: 150px; height: 12px; }
.sk-line { width: 230px; max-width: 100%; }
.sk-short { width: 88px; }
@keyframes sk-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .sk { animation: none; }
}
h2 { margin: 0 0 10px; font-size: 16px; }

.layout {
  display: grid;
  grid-template-columns: 248px 1fr;
  gap: 20px;
  align-items: start;
}

/* ── Sidebar ── */
.side {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.prof {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.avatar {
  flex: none;
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 17px;
  color: var(--on-accent);
  background: linear-gradient(135deg, var(--accent), var(--accent2));
}

.who { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.who b { font-size: 14.5px; }
.who .email {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.who .prov {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--muted-2);
}

.nav { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  text-align: left;
  padding: 10px 13px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.14s, color 0.14s;
}
.nav-item:hover { background: var(--panel-hi); }
.nav-item.on {
  background: var(--panel-hi);
  border-color: var(--line-hi);
  color: var(--text);
  font-weight: 600;
}
.nav-item.danger { color: var(--bad-2, var(--bad)); }
.nav-item.danger.on { border-color: color-mix(in oklab, var(--bad) 45%, transparent); }

/* ── Nội dung ── */
.info { display: grid; grid-template-columns: 170px 1fr; gap: 10px 12px; margin: 0; font-size: 14px; }
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
.google-note { margin-top: 4px; }

.nguy-hiem { border-color: color-mix(in oklab, var(--bad) 35%, var(--line)); }
.btn.xoa { color: var(--bad); border-color: color-mix(in oklab, var(--bad) 45%, transparent); }
.msg.warn { border-left: 4px solid var(--warn); background: rgba(255, 194, 75, 0.08); }

@media (max-width: 760px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; }
  .nav { flex-direction: row; flex-wrap: wrap; }
  .nav-item { flex: 1; min-width: 120px; text-align: center; }
  .info { grid-template-columns: 1fr; gap: 2px 0; }
  .info dt { margin-top: 8px; }
}
</style>
