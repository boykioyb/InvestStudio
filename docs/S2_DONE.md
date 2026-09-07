# S2 — Khu quản trị lõi: đã triển khai & nghiệm thu

> Ngày: 2026-09-07 · Nhánh `feat/bao-mat-han-muc` · commit `42016dc`
> Tiếp nối [`S1_DONE.md`](S1_DONE.md) · Kế hoạch: [`SHIP_PLAN.md`](SHIP_PLAN.md) §3

## 1. Nghiệm thu (chạy thật trên trình duyệt)

| Phép thử | Kết quả |
|---|---|
| **Tiêu chí chính:** gạt tắt "Bật trợ lý" trong `/admin` → hỏi trợ lý | **503** "Trợ lý đang tạm nghỉ để bảo trì" — **không deploy lại** ✅ |
| Người dùng thường / khách gọi `/api/admin/*` | **403** / **401** |
| Bật danh sách IP cho phép rồi gọi từ IP khác | **404** (cố ý — không xác nhận là có khu quản trị ở đây) |
| Admin chưa bật 2 lớp mở `/admin/overview` | **403**, nhưng `/admin/2fa/setup` vẫn vào được để còn bật |
| Bật 2 lớp qua giao diện → đăng nhập lại **không** nhập mã | **401** "Nhập mã 6 số từ ứng dụng xác thực" |
| Đăng nhập **có** mã 6 số | **200** |
| Khóa một tài khoản đang mở phiên ở máy khác | Phiên đó chết ngay (**401**), không đợi token hết hạn |
| 1 câu hỏi thật → `usage_events` | `calls=2, tokens_in=4963, tokens_out=774, latency 35s` |
| Chạy `usage.flush` | 2 dòng `usage_daily` (tổng ngày + theo người dùng) |
| Nhật ký kiểm toán | 4 dòng đúng thứ tự thao tác, kèm `before/after` và lý do |

`pytest tests -q` → **105 passed** (thêm 14 test trong `test_admin.py`).

## 2. Kiến trúc: vì sao admin là APP RIÊNG

| Lý do | Chi tiết |
|---|---|
| **CSS** | Nuxt UI kéo theo Tailwind, mà preflight của Tailwind reset toàn cục — nhét chung sẽ đè vỡ hệ thiết kế tự viết trong `frontend/assets/css/main.css` |
| **Bảo mật** | Tách được ở tầng mạng: `admin.<domain>` đặt sau danh sách IP cho phép, trang công khai vẫn mở. Khu quản trị đọc được dữ liệu của mọi người dùng nên không nên nằm chung bề mặt tấn công |
| **Vòng đời** | Nâng cấp Nuxt/Tailwind bên này không đụng bên kia |

Chạy **SPA (`ssr: false`)** — không phải mặc định của Nuxt, mà là quyết định có lý do:
mọi lời gọi API quản trị dựa vào **cookie của trình duyệt**, còn render phía máy chủ sẽ
gọi API mà không mang theo cookie đó và luôn nhận 401. Trang quản trị cũng không cần SEO.

**Giấy phép:** Nuxt UI v4 đã gộp bản Pro và mở nguồn **MIT** → 4 trang này không tốn phí bản quyền.

## 3. Backend

### `settings_store.py` — cấu hình đổi được lúc chạy
Nguồn giá trị: bảng `app_settings` → `config.py`. Cache **30 giây** nên bấm là có hiệu lực
trên mọi tiến trình (web + worker) mà không bắt mỗi request phải hỏi cơ sở dữ liệu.

| Cần gạt khẩn cấp | Tác dụng |
|---|---|
| `assistant_enabled` | Tắt trợ lý toàn hệ thống |
| `registration_open` | Đóng đăng ký khi thấy bot tạo tài khoản hàng loạt |
| `refresh_enabled` | Cấm ép crawl lại khi nguồn dữ liệu đang căng |
| `maintenance_mode` | Chỉ quản trị vào được — **vẫn chừa `/api/admin` và `/api/auth`**, nếu không là tự nhốt mình bên ngoài |

Cộng 8 hạn mức chỉnh trực tiếp (lượt hỏi/người, /thiết bị, /IP, lượt phân tích khách và
thành viên, trần Gemini/ngày, số câu chạy đồng thời, số vòng gọi công cụ).

### `usage.py` — đo mức tiêu thụ
Số token nằm sâu trong `rag/gemini.py`, còn "ai hỏi, mã nào, mất bao lâu" chỉ có ở tầng
route → dùng **ContextVar** để tầng dưới cộng dồn mà không phải đổi chữ ký cả chuỗi hàm.
Redis đếm nhanh trong ngày; job `usage.flush` (5 phút/lần) dồn sang `usage_daily` để
`/admin` vẽ biểu đồ nhiều ngày mà không quét bảng thô.
**Không có cột tiền** — bản miễn phí không có hóa đơn; token vẫn lưu vì còn trần TPM.

### `audit.py` — nhật ký kiểm toán
Mọi thao tác GHI và mọi lần XEM dữ liệu cá nhân của một người cụ thể đều để lại một dòng
kèm `before/after`. Bảng chỉ ghi thêm. Ghi audit **không chặn** thao tác.

### Rào cho khu quản trị
1. Vai trò `admin`.
2. **Danh sách IP cho phép** (`APP_ADMIN_IP_ALLOWLIST`, hỗ trợ CIDR) — rào ngoài cùng,
   đứng trước cả đăng nhập. Trả **404** chứ không 403.
3. **Bắt buộc TOTP** (`APP_ADMIN_REQUIRE_2FA`, mặc định bật). Chừa đúng hai đường
   `/2fa/setup` và `/2fa/enable`, nếu không sẽ không ai bật được lần đầu.
4. Bật 2 lớp / khóa tài khoản đều tăng `token_version` → mọi phiên cũ chết ngay.
5. Không cho tự bỏ quyền quản trị của chính mình (tránh cảnh không còn admin nào).

## 4. Việc còn phải làm tay

1. **Bật 2 lớp cho tài khoản của bạn** — hiện `admin_require_2fa` đang BẬT, nên tài khoản
   admin chưa có TOTP sẽ thấy 403 ở mọi trang trừ phần bật 2 lớp trong **Cài đặt**.
   Muốn hoãn: `APP_ADMIN_REQUIRE_2FA=false`.
2. **Khai `APP_ADMIN_IP_ALLOWLIST`** trước khi mở ra Internet (hiện rỗng = không giới hạn).
3. **Ở môi trường thật: KHÔNG publish cổng 3020**, chỉ để reverse proxy trỏ vào; đặt
   `APP_COOKIE_DOMAIN=.mien-cua-ban.vn` để hai tên miền con dùng chung phiên đăng nhập.
4. Chạy `./dev.sh` (đã thêm service `admin`) — khu quản trị ở <http://localhost:3020>.

## 5. Còn lại của khu quản trị (S3)

8 trang chưa làm: Sử dụng & hạn mức · Trợ lý (RAG) · **Hội thoại** (xem đầy đủ nội dung,
tìm toàn văn) · Job & hàng đợi · Nguồn dữ liệu · Thiết bị & chống lạm dụng · Cache ·
Thông báo. Dữ liệu cho trang Thiết bị đã có sẵn từ S1 (`device_fingerprints`,
`device_accounts`), trang Hội thoại đọc từ `conversations`/`chat_messages` đã có.
