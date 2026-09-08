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

## 🟠 S4 — Rõ sản phẩm ✅ *(đã xong 2026-09-08)*

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
- [x] Câu định vị trên hero: nói thẳng nhận được gì (điểm 14 tiêu chí + mất bao nhiêu nếu kịch bản xấu)
- [x] Onboarding 3 bước cho lần đầu vào (`OnboardingTour`, tự tắt vĩnh viễn khi đóng)
- [x] Trang `/scoring` giải thích 14 tiêu chí — nội dung sinh từ `criteria.py` qua API mới `GET /api/stocks/scoring-model`
- [x] Trang lỗi 404 / 500 (`error.vue`) — 404 cho luôn ô nhập mã để đi tiếp
- [x] Trạng thái rỗng cho mọi bảng (thiếu mỗi bảng screener — đã bổ sung; các bảng khác đã có sẵn)
- [x] Rà soát mobile: ghim cột mã khi cuộn ngang ở screener; 7 trang chính không tràn ngang ở 375px

---

## 🟡 S3 — Khu quản trị đầy đủ ✅ *(đã xong 2026-09-08 — 12/12 trang)*

- [x] **Sử dụng & hạn mức** — chuỗi ngày theo loại, top người/mã, số request Gemini mỗi lượt hỏi
- [x] **Hội thoại** — xem đầy đủ nội dung + tìm toàn văn; mỗi lần mở ghi audit
- [x] **Thiết bị & chống lạm dụng** — xếp theo số tài khoản chung một máy, chặn/bỏ chặn kèm lý do
- [x] **Kho tri thức (RAG)** — số tài liệu, tuổi dữ liệu (cảnh báo khi >3 ngày), reindex, xóa tài liệu
- [x] **Job & hàng đợi** — job gần đây, độ dài hàng đợi, lịch chạy nền
- [x] **Nguồn dữ liệu** — thử thật 5 nguồn, độ trễ, nút thử ngay (nhớ 60s)
- [x] **Cache** — xem/xóa theo mã hoặc toàn bộ, kèm cảnh báo cache là của một tiến trình
- [x] **Thông báo** — gửi thông báo hệ thống (chuông trong app, không phải email)

---

## 🟡 S5 — Vận hành & pháp lý ✅ *(đã xong 2026-09-08, trừ test khói frontend)*

**Hạ tầng:**
- [x] `docker-compose.prod.yml` — không publish cổng backend/admin/frontend, chỉ Caddy 80/443
- [x] HTTPS tự động qua Caddy (`ops/Caddyfile`) + cookie Secure + `APP_ENV=prod`
- [x] Mật khẩu Postgres bắt buộc truyền từ `.env.prod` (compose báo lỗi nếu thiếu)
- [x] `APP_JWT_SECRET` bắt buộc truyền từ `.env.prod`
- [x] Sao lưu `pg_dump` hằng đêm (`ops/backup.sh`) + `ops/restore.sh`; **đã thử phục hồi thật**, dữ liệu khớp

**Lưới an toàn:**
- [x] CI (`.github/workflows/ci.yml`): pytest + typecheck mỗi push/PR
- [x] Typecheck sạch (sửa lỗi kiểu cuối cùng); chạy ở CI thay vì bật lúc dev cho nhanh
- [x] 14 test cho `position._decide` và `portfolio.review`
- [x] Test khói frontend: 6 ca Playwright (trang chủ · nhập mã → thấy điểm · gợi ý mã · cách chấm điểm · 404 · trang pháp lý), có job CI
- [x] Log JSON + mã request + Sentry (bật khi có DSN); `/api/health` chạm thật DB · Redis · Gemini, trả 503 khi hỏng

**Pháp lý (Nghị định 13/2023):**
- [x] Trang `/terms` Điều khoản sử dụng
- [x] Trang `/privacy` — đã nêu rõ cả 2 điều bắt buộc (xem nội dung hội thoại · thu thập đặc điểm thiết bị)
- [x] Miễn trừ trách nhiệm ở `AppFooter` (mọi trang) + trong từng màn hình chính

---

## ⚪ Nợ kỹ thuật *(phần bảo mật & tính năng đã xong ở S6 — xem [S6_TEST.md](S6_TEST.md))*

- [x] **H11** — vé dùng-một-lần lấy qua `POST /chat/stream-ticket` (TTL 60s, gắn với đúng người xin, kiểm TRƯỚC quota)
- [x] **H12** — bọc `<du_lieu>`, vô hiệu hóa thẻ giả, dặn dò trong prompt hệ thống, ghi log nghi vấn (`rag/guard.py`)
- [x] Câu đố **proof-of-work** từ tài khoản thứ 3 trên một thiết bị (tự giải trong nền, không cần bên thứ ba)
- [x] Email cảnh báo ngưỡng (chỉ gửi cho tài khoản đã xác minh + còn bật; tắt được ở `/account`)
- [x] Ô tìm mã gợi ý theo mã · tên công ty · tên thương hiệu (`GET /api/stocks/search`, cache 1 giờ)
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
