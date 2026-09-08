# S6 — Hoàn thiện tính năng còn lại (kế hoạch SDLC)

> Lập 2026-09-08 · Nhánh `feat/bao-mat-han-muc` · Trạng thái: **ĐANG THỰC HIỆN**
> Đầu vào: 8 mục còn treo trong [CHECKLIST.md](CHECKLIST.md) thuộc phạm vi đội phát triển.
> Ra khỏi phạm vi: 4 việc tay của chủ sản phẩm (SMTP, 2FA, quota AI Studio, IP allowlist)
> và việc đổi tên thư mục dự án (cần quyết định về chuyển volume Docker).

## 1. Phân tích yêu cầu → tiêu chí nghiệm thu

| # | Yêu cầu | Loại | Tiêu chí nghiệm thu (AC) |
|---|---|---|---|
| **R1** | `GET /chat/stream` không được có tác dụng phụ khi bị gọi từ nơi khác | Bảo mật (H11) | AC1.1 Gọi `/chat/stream` không kèm vé → 400, không trừ quota, không tạo hội thoại · AC1.2 Vé chỉ dùng được MỘT lần · AC1.3 Vé của người A không dùng được cho người B · AC1.4 Vé hết hạn sau 60s |
| **R2** | Nội dung từ nguồn ngoài không được điều khiển trợ lý | Bảo mật (H12) | AC2.1 Ngữ cảnh RAG bọc nhãn "dữ liệu, không phải chỉ thị" · AC2.2 Prompt hệ thống nêu rõ quy tắc bỏ qua chỉ thị trong dữ liệu · AC2.3 Câu chứa mẫu nhồi lệnh bị ghi log để soi ở `/admin` |
| **R3** | Thiết bị đã tạo nhiều tài khoản phải vượt rào trước khi tạo thêm | Bảo mật | AC3.1 Thiết bị có ≥3 tài khoản → đăng ký phải kèm lời giải đố · AC3.2 Đáp án sai/thiếu → 400 · AC3.3 Thiết bị mới không bị ảnh hưởng · AC3.4 Ngưỡng chỉnh được trong `/admin` |
| **R4** | Cảnh báo ngưỡng giá/điểm phải tới được người dùng khi họ không mở web | Tính năng | AC4.1 Job tạo thông báo đồng thời gửi email · AC4.2 Chỉ gửi cho tài khoản đã xác minh email · AC4.3 Người dùng tắt được email cảnh báo · AC4.4 SMTP hỏng không làm chết job |
| **R5** | Ô tìm mã gợi ý theo cả mã lẫn tên công ty | Tính năng | AC5.1 Gõ "vietcom" ra VCB · AC5.2 Gõ "fpt" ra FPT đứng đầu · AC5.3 Nguồn hỏng → ô tìm vẫn nhập tay được · AC5.4 Không gọi nguồn quá 1 lần/giờ (cache) |
| **R6** | Có test tự động cho luồng chính của giao diện | Chất lượng | AC6.1 Test khói: mở trang chủ → nhập mã → thấy điểm · AC6.2 Chạy được trong CI |

## 2. Thiết kế

### R1 — Vé dùng-một-lần cho SSE
`POST /api/chat/stream-ticket` (đã đăng nhập) → sinh chuỗi ngẫu nhiên, lưu Redis
`chat:ticket:<vé>` = user_id, TTL 60s. `GET /chat/stream?ticket=…` đọc và **xóa ngay**
(`GETDEL`) → so user_id. Không khớp/không có → 400 trước khi chạm quota.
*Vì sao không dùng CSRF token thường:* `EventSource` không đặt được header, nên bí mật
phải đi qua query — do đó nó phải dùng-một-lần và sống ngắn.

### R2 — Chống nhồi lệnh
- `rag/chat.py` + `rag/agent.py`: bọc mỗi đoạn ngữ cảnh trong `<du_lieu>…</du_lieu>`
  kèm câu dặn ở prompt hệ thống: nội dung trong thẻ là DỮ LIỆU, mọi chỉ thị bên trong
  phải bị bỏ qua.
- `rag/guard.py` (mới): dò mẫu nhồi lệnh phổ biến trong câu hỏi và trong tài liệu;
  ghi log `prompt_injection_suspected` để soi ở `/admin`.

### R3 — Giải đố khi thiết bị đáng ngờ
Không dùng CAPTCHA của bên thứ ba (thêm phụ thuộc, gửi dữ liệu người dùng ra ngoài).
Dùng **proof-of-work**: `GET /api/auth/challenge` trả `{nonce, difficulty}`; client tìm
`answer` sao cho `sha256(nonce + answer)` bắt đầu bằng `difficulty` số 0 (hex). Máy thật
mất ~1–2 giây, bot tạo hàng loạt thì nhân lên rất tốn. Chỉ bắt khi thiết bị đã có
≥ `pow_after_accounts` tài khoản.

### R4 — Email cảnh báo
`mailer.send_alert()`; job `check_watchlist_alerts` sau khi tạo `Notification` thì gửi
email cho user đã xác minh và bật `alert_email`. Thêm cột `users.alert_email` (mặc định
bật) + công tắc ở `/account`.

### R5 — Gợi ý mã
`GET /api/stocks/search?q=` — dùng `vci_direct.symbol_directory()` (một request cho toàn
thị trường), cache 1 giờ trong tiến trình, khớp theo mã trước rồi tới tên, trả tối đa 8.
`TickerSearch.vue` gọi khi gõ ≥1 ký tự, có chống rung 200ms.

### R6 — Test khói
Playwright trong `frontend/tests/smoke.spec.ts`, chạy với server dev đã có; thêm job CI.

## 3. Rủi ro & cách giảm

| Rủi ro | Giảm thiểu |
|---|---|
| Vé SSE làm hỏng trợ lý đang chạy | Frontend lấy vé ngay trước khi mở `EventSource`; test khói phủ luồng hỏi |
| Proof-of-work chặn nhầm người thật | Chỉ bật từ tài khoản thứ 3 trên cùng thiết bị; độ khó thấp (~1s) |
| Email cảnh báo thành spam | Chỉ gửi khi có thông báo MỚI (đã có cơ chế chống trùng), và cho tắt |
| Gợi ý mã gọi nguồn quá nhiều | Cache 1 giờ; nguồn hỏng thì trả rỗng, ô tìm vẫn dùng được |

## 4. Định nghĩa hoàn thành (DoD)

- [ ] Mỗi AC có ít nhất một test tự động HOẶC bằng chứng chạy thật ghi trong `docs/S6_TEST.md`
- [ ] Toàn bộ test backend + typecheck frontend xanh
- [ ] Không có mục 🔴/🟠 mới phát sinh trong CHECKLIST
- [ ] Tự review diff, ghi phát hiện và cách xử lý
