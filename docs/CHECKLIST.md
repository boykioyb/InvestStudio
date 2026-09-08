# Việc còn lại trước khi ship — Phân Tích Mã

> Cập nhật 2026-09-08 (S4 phần lớn đã xong) · Nhánh `feat/bao-mat-han-muc` (11 commit, **chưa push**)
> Đã xong: [S0](S0_DONE.md) chặn thủng quota · [S1](S1_DONE.md) tài khoản + vân tay thiết bị · [S2](S2_DONE.md) khu quản trị lõi
> Kế hoạch gốc: [SHIP_PLAN.md](SHIP_PLAN.md)

---

## 🔴 Làm ngay — 4 việc tay, không có thì hệ thống chạy sai

- [ ] **Cấu hình SMTP** (`.env` đang trống) — chưa có thì thư xác minh chỉ nằm trong log
      máy chủ, **người dùng mới mắc kẹt ngay bước đầu và không tự lấy lại được mật khẩu**.
      Cần: `APP_SMTP_HOST/PORT/USER/PASSWORD/FROM` + `APP_PUBLIC_BASE_URL`.
      *Tạm hoãn được bằng `APP_REQUIRE_VERIFIED_EMAIL=false`, nhưng khi đó rào chống tạo
      tài khoản hàng loạt chỉ còn vân tay thiết bị.*
- [ ] **Bật 2 lớp cho `hoatq.dev@gmail.com`** — tài khoản admin duy nhất **chưa có TOTP**,
      nên đang bị chặn khỏi mọi trang quản trị trừ phần bật 2 lớp trong Cài đặt.
      Vào <http://localhost:3020/cai-dat> → "Tạo mã bật 2 lớp".
- [ ] **Đọc quota thật của dự án trong AI Studio** rồi đặt `gemini_daily_call_cap` cho
      đúng (đang để ước lượng **1.400**). Google không còn công bố bảng cố định.
- [ ] **Khai `APP_ADMIN_IP_ALLOWLIST`** trước khi khu quản trị ra Internet (đang rỗng =
      không giới hạn).

---

## 🟠 S4 — Rõ sản phẩm *(chặn ship: thiếu là người lạ không dùng được)*

**Ba trang còn thiếu — backend đã xong từ S1, chỉ thiếu giao diện:**
- [x] `/verify-email?token=` — nhận link trong thư, gọi `POST /api/auth/verify`
- [x] `/forgot-password` — nhập email, gọi `POST /api/auth/forgot-password`
- [x] `/reset-password?token=` — đặt mật khẩu mới, gọi `POST /api/auth/reset-password`

**Trạng thái tài khoản trên giao diện:**
- [x] Dải nhắc "hãy xác minh email" khi `email_verified = false`, kèm nút gửi lại thư
- [x] Hiện "còn N/5 lượt hỏi hôm nay" — trang Trợ lý, widget nổi và trang Tài khoản
- [x] Thông báo 429 nói rõ rổ nào chạm trần (backend đã trả câu chữ, giao diện hiện nguyên văn)
- [x] Trang `/account`: thông tin · đổi mật khẩu · hạn mức · xóa tài khoản

**Định vị & onboarding:**
- [ ] Chốt một câu sản phẩm hứa gì, đặt lên hero
- [ ] Onboarding 3 bước cho lần đầu vào
- [x] Trang `/scoring` giải thích 14 tiêu chí — nội dung sinh từ `criteria.py` qua API mới `GET /api/stocks/scoring-model`
- [x] Trang lỗi 404 / 500 (`error.vue`) — 404 cho luôn ô nhập mã để đi tiếp
- [ ] Trạng thái rỗng cho mọi bảng
- [ ] Rà soát mobile — bảng screener 10+ cột chưa có phương án

---

## 🟡 S3 — Khu quản trị đầy đủ *(8 trang còn lại, không chặn ship)*

- [ ] **Sử dụng & hạn mức** — biểu đồ theo khoảng ngày, top 20 người/mã, tỷ lệ trúng cache
- [ ] **Hội thoại** — xem đầy đủ nội dung hỏi–đáp, tìm toàn văn *(bạn đã chốt: admin xem hết)*
- [ ] **Thiết bị & chống lạm dụng** — xếp theo số tài khoản chung một máy, nút chặn
      *(dữ liệu đã có từ S1: `device_fingerprints`, `device_accounts`)*
- [ ] **Trợ lý (RAG)** — số tài liệu, tuổi dữ liệu, nút reindex
- [ ] **Job & hàng đợi** — job Celery đang chạy/thất bại, nút chạy lại
- [ ] **Nguồn dữ liệu** — VCI · DNSE · CafeF · Google News · Gemini: sống/chết, độ trễ
- [ ] **Cache** — xem/xóa cache theo mã khi nguồn trả số sai
- [ ] **Thông báo** — gửi thông báo hệ thống tới người dùng

---

## 🟡 S5 — Vận hành & pháp lý *(chặn ship khi mở công khai)*

**Hạ tầng:**
- [ ] `docker-compose.prod.yml` — **không publish cổng backend (8010) và admin (3020)**,
      chỉ reverse proxy ra ngoài
- [ ] HTTPS (Caddy/Nginx) + `APP_COOKIE_SECURE=true` + `APP_ENV=prod` (tự tắt `/docs`)
- [ ] Đổi mật khẩu Postgres (đang là `invest/invest`)
- [ ] `APP_JWT_SECRET` ngẫu nhiên ≥32 ký tự *(app tự từ chối khởi động nếu quên khi bật HTTPS)*
- [ ] Sao lưu `pg_dump` hằng đêm **và thử phục hồi một lần thật**

**Lưới an toàn:**
- [ ] CI (`.github/workflows`) chạy pytest + typecheck khi push — **chưa có**
- [ ] Bật `typeCheck: true` cho frontend (`nuxt.config.ts:44` đang `false`)
- [ ] Test cho `position._decide` (quy tắc cắt lỗ — sai là mất tiền thật) và `portfolio.review`
- [ ] Một test khói frontend: nhập mã → thấy điểm
- [ ] Log JSON + Sentry; `/api/health` mở rộng (DB · Redis · Gemini · nguồn dữ liệu)

**Pháp lý (Nghị định 13/2023):**
- [ ] Trang Điều khoản sử dụng
- [ ] Trang Chính sách quyền riêng tư — **phải nêu rõ 2 điều**: đội vận hành có thể xem
      nội dung hội thoại; hệ thống thu thập đặc điểm thiết bị để chống lạm dụng hạn mức
- [ ] Miễn trừ "không phải khuyến nghị đầu tư" hiển thị trên giao diện
      *(hiện chỉ nằm trong README và mô tả API — người dùng không đọc được)*

---

## ⚪ Nợ kỹ thuật đã biết *(có kiểm soát, để sau)*

- [ ] **H11** — `GET /chat/stream` là GET nhưng có tác dụng phụ (tạo hội thoại, trừ quota):
      dụ bấm link là mất lượt. Sửa bằng vé dùng-một-lần lấy qua POST.
- [ ] **H12** — nhồi lệnh qua tin tức (prompt injection): bọc ngữ cảnh bằng nhãn
      "DỮ LIỆU, KHÔNG PHẢI CHỈ THỊ"
- [ ] **CAPTCHA** ở bước đăng ký khi một thiết bị có ≥3 tài khoản *(hiện chặn cứng ở mức 5)*
- [ ] Email cho cảnh báo giá — `Notification` mới chỉ hiện trong app
- [ ] Ô tìm mã có gợi ý tên công ty
- [ ] Đổi tên thư mục dự án `InvestStudio` → kéo theo tên volume Docker, **cần chuyển
      volume thủ công**; chưa làm vì là quyết định của bạn
- [ ] Dọn nợ trong [REFACTOR_PLAN.md](REFACTOR_PLAN.md): tách `schemas/stock.py` (556 dòng),
      `rag/agent.py`, `vci_direct.py`; gom `useApi()`; bỏ `window.prompt/confirm`

---

## Nhắc lại giới hạn đã biết *(để không kỳ vọng sai)*

| Thứ | Chặn được | KHÔNG chặn được |
|---|---|---|
| Vân tay thiết bị | Tab ẩn danh · xóa cookie · đổi IP · đăng ký email mới | Đổi trình duyệt · Brave chống-fingerprint · máy khác |
| Trần toàn cục Gemini | Mọi kiểu lạm dụng — đây là lớp bảo đảm duy nhất | (chạm trần thì trợ lý hạ cấp rồi dừng, đúng thiết kế) |
| Quota bản miễn phí | ~42–120 người/ngày tùy độ nặng câu hỏi | Không mua thêm được — hết là hết tới 0h |
