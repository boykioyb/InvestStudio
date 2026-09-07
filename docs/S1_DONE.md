# S1 — Nền tài khoản + chống lách hạn mức: đã triển khai & nghiệm thu

> Ngày: 2026-09-07 · Nhánh `feat/bao-mat-han-muc` · commit `751047e`
> Tiếp nối [`S0_DONE.md`](S0_DONE.md). Kế hoạch gốc: [`SHIP_PLAN.md`](SHIP_PLAN.md) §2.4, §6.

## 1. Nghiệm thu (chạy thật)

| Phép thử | Kết quả |
|---|---|
| Đăng ký xong hỏi trợ lý khi **chưa xác minh email** | **403** "cần xác minh email trước khi dùng trợ lý" |
| Bấm link xác minh (lấy từ log vì chưa có SMTP) | 200, `email_verified: true`, dùng được ngay |
| Tài khoản A hỏi 1 câu | `used 1/5`, `remaining 4` |
| **Tạo tài khoản B mới tinh trên CÙNG thiết bị** | `used: 0` nhưng **`remaining: 4`** ✅ — đăng ký email mới không reset được hạn mức |
| Tạo tài khoản thứ 6 trên một thiết bị | **429** "Thiết bị này đã tạo 5 tài khoản" |
| Đăng ký từ **thiết bị khác** (cookie jar mới) | 201 — không chặn nhầm người thật |
| Vân tay ghi vào DB | 1 dòng `device_fingerprints`, 2 dòng `device_accounts` trỏ về cùng thiết bị |
| Plugin chạy trên trình duyệt thật | cookie `fpjs=53cc5884…` được đặt; cookie `did` không đọc được bằng JS (đúng — httpOnly) |
| Đổi mật khẩu rồi dùng lại token cũ | **401** — mọi phiên cũ chết |
| Link đặt lại mật khẩu dùng lần 2 | **400** — chỉ dùng được một lần |
| `POST /auth/forgot-password` với email không tồn tại | Phản hồi **giống hệt** email có thật |
| Upload `<html>` khai là `image/png` | **415**; PDF khai là PNG → **415**; PNG thật → 200 |
| Xóa tài khoản | 204, kéo theo mã theo dõi/hội thoại (CASCADE), đăng nhập lại → 401 |

`pytest tests -q` → **91 passed** (thêm 17 test: `test_account.py` + phần thiết bị trong `test_quota.py`).

## 2. Đã làm những gì

### Nền tài khoản (migration `0006_user_account`)
Thêm `status` · `email_verified_at` · `token_version` · `last_login_at` · `last_ip`.
Tài khoản cũ được backfill là **đã xác minh** — nâng cấp không đá ai ra ngoài.

- **Thu hồi phiên**: JWT mang thêm `tv`; đổi/đặt lại mật khẩu tăng `users.token_version`
  → token cũ hết hiệu lực ngay. Trước đây token sống 7 ngày, nên đổi mật khẩu gần như
  vô nghĩa trước kẻ đã trộm được cookie.
- **Xác minh email** bắt buộc cho trợ lý + upload (`require_verified`); có nút gửi lại thư.
- **Quên/đặt lại mật khẩu**: token gắn với **hash mật khẩu hiện tại** → đổi xong là link tự
  hỏng, không cần bảng lưu token đã dùng. `forgot-password` trả lời như nhau dù email có
  tồn tại hay không (nếu không, đây thành công cụ dò xem ai đã đăng ký).
- **Xóa tài khoản** (`DELETE /api/auth/me`, bắt nhập lại mật khẩu) — quyền xóa dữ liệu theo
  Nghị định 13/2023.
- **Khóa tài khoản** (`status='suspended'`) → 403 ở mọi endpoint và cả lúc đăng nhập.
- Mật khẩu tối thiểu **6 → 10 ký tự** (không ép ký tự đặc biệt: độ dài mới là thứ quyết
  định, quy tắc rườm rà chỉ đẩy người dùng sang `Matkhau@123`).
- `mailer.py`: SMTP thật nếu cấu hình; chưa cấu hình thì **in link ra log** để dev dùng được.

### Vân tay thiết bị (migration `0007_fingerprints`)
`fp_hash = sha256(visitorId · deviceId · dòng-trình-duyệt · ngôn-ngữ)` — hai nửa:

| Nửa | Ai tạo | Chống được gì |
|---|---|---|
| `fpjs` (FingerprintJS v5, MIT) | Trình duyệt, plugin Nuxt | Xóa cookie, tab ẩn danh, đổi IP |
| `did` (JWT có ký, **httpOnly**) | Máy chủ | `curl`/script tự chế header — không ký nổi vì không có khóa |

- Dùng **cookie** thay vì header `X-Device-Id`: trình duyệt tự đính cookie vào mọi request
  cùng origin nên không phải sửa từng composable, và **luồng SSE** (EventSource không đặt
  được header) cũng có vân tay.
- Dòng trình duyệt được rút gọn (`chrome:mac`), không dùng nguyên chuỗi User-Agent — nếu
  không, Chrome tự cập nhật một lần là hạn mức tự reset.
- **Hạn mức nhiều rổ**: `min(tài khoản 5, thiết bị 5, IP 8, dải /24 60)`. Đọc hết rồi mới
  tăng, để request bị rổ cuối chặn không bị trừ oan ở các rổ trước. Thông báo 429 nói rõ
  rổ nào chạm trần.
- Rổ dải mạng để **rộng** (60): nhà mạng Việt Nam cho hàng nghìn thuê bao dùng chung một
  IP (NAT), siết chặt là chặn nhầm cả khu.
- **Thang leo thang**: 5 tài khoản/thiết bị → chặn tạo tài khoản mới, tài khoản cũ vẫn
  chạy bình thường; quản trị đánh dấu được thiết bị (`blocked`) kèm lý do.

### Kèm theo
- **Upload**: kiểm **magic bytes** (không tin `Content-Type` client khai), trần **50 MB/tài
  khoản**, PDF trả về dạng `attachment` + `nosniff` (PDF mở inline là mặt phẳng tấn công
  chạy trên chính origin của mình).
- **`POST /portfolio/review`**: bắt đăng nhập, trần **100 → 20 mã/lượt** (H7) — một request
  100 mã là hàng trăm lượt crawl, đủ để nguồn chặn IP máy chủ và cả trang chết.
- `GET /api/chat/quota` trả `remaining` là **số nhỏ nhất** giữa rổ tài khoản và rổ thiết bị
  — đúng cái người dùng thực sự còn, thay vì hứa 5 rồi chặn ở lượt thứ 2.

## 3. Việc còn phải làm tay

1. **Cấu hình SMTP** — chưa có thì thư xác minh chỉ nằm trong log máy chủ, người lạ sẽ mắc
   kẹt ngay bước đầu. Đặt `APP_SMTP_HOST/PORT/USER/PASSWORD/FROM` và `APP_PUBLIC_BASE_URL`.
2. **Frontend còn thiếu 3 trang** (thuộc S4, backend đã sẵn sàng): `/xac-minh`,
   `/quen-mat-khau`, `/dat-lai-mat-khau`; thêm dải thông báo "hãy xác minh email" và hiển
   thị "còn N/5 lượt hôm nay" từ `GET /api/chat/quota`.
3. **Chính sách quyền riêng tư phải nêu việc thu thập đặc điểm thiết bị** — vân tay là dữ
   liệu cá nhân theo Nghị định 13/2023.
4. `APP_REQUIRE_VERIFIED_EMAIL=false` nếu muốn tạm tắt rào xác minh khi chưa có SMTP.

## 4. Giới hạn đã biết (nói trước, không phải phát hiện sau)

- Đổi trình duyệt (Chrome → Firefox), bật chống-fingerprint của Brave/Firefox, dùng trình
  duyệt chống phát hiện, hoặc dùng máy khác → **vân tay đổi hẳn, lách được**.
- Hai máy **cùng đời, cùng hệ điều hành, cùng trình duyệt** có thể **trùng vân tay** → nên
  dùng thang leo thang thay vì chặn cứng.
- Vì vậy vân tay là **lớp ma sát**, không phải lớp bảo đảm. Lớp bảo đảm vẫn là **trần toàn
  cục fail-closed** trong `app/core/budget.py` (S0).
- Chưa có CAPTCHA ở bước đăng ký (kế hoạch để ở mức "3 tài khoản/thiết bị"); hiện thay bằng
  rào xác minh email + chặn cứng ở mức 5.
