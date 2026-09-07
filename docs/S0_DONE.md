# S0 — Chặn thủng quota: đã triển khai & nghiệm thu

> Ngày: 2026-09-07 · Phạm vi: pha S0 của [`SHIP_PLAN.md`](SHIP_PLAN.md) · Trạng thái: **XONG, đã chạy thật**
> Chưa commit — mã nằm trong working tree cùng với bản redesign v3 đang dở.

## 1. Kết quả nghiệm thu (chạy thật, không phải mô phỏng)

Kịch bản tấn công theo đúng tiêu chí trong kế hoạch, bắn qua **đường thật** (trình duyệt → proxy Nuxt → API):

| Phép thử | Kết quả | Ý nghĩa |
|---|---|---|
| 60 lượt `GET /api/stocks/FPT?refresh=true` (khách, mỗi lượt một IP giả khác nhau) | **30 × 200, 30 × 429** | Hạn mức khách 30/ngày chặn đúng; IP giả không tạo được "người mới" |
| 50 lần `POST /api/auth/register` liên tiếp | **10 × 201, 40 × 429** | Không tạo được tài khoản hàng loạt |
| **Số request Gemini phát sinh trong CẢ đợt tấn công** | **0** | ✅ Tiêu chí quan trọng nhất — đường công khai không còn nối vào quota Gemini |
| Hàng đợi Celery sau đợt tấn công | **0 job** | Không job nhúng nào bị đẩy |
| 20 request qua proxy với 20 cặp `X-Forwarded-For`/`X-Real-IP` giả | Tất cả rơi vào **một rổ đếm duy nhất** (`rl:api:<IP thật>` = 20) | Lỗ giả mạo IP (H4) đã đóng trên đường thật |
| 130 request/phút vào `/api` | **120 × 200, 10 × 429** | Trần request/phút hoạt động |
| `POST /api/chat/reindex` — khách / user thường | **401 / 403** | Việc tiêu hạn mức chung chỉ còn admin bấm được |
| Phân tích FPT lần 2 với `refresh=true` (khách) | 1,46s → **0,007s** | Khách không ép crawl được nữa, đọc cache |
| `?pe_sec=9.001` rồi `?pe_sec=9.004` | 1,36s → **0,004s** | Không phá được cache bằng số lẻ |
| Hỏi trợ lý 1 câu (thật, có Gemini key) | 200 · `used 1/5` · **bộ đếm Gemini = 2** | Đếm đúng REQUEST thật (1 nhúng + 1 gọi model), không đếm "lượt hỏi" |

`pytest tests -q` → **74 passed** (thêm 12 test mới trong `tests/test_quota.py`).

## 2. Đã sửa những gì

### Lỗ chính: đường phân tích công khai nối thẳng vào Gemini (H1)
- **`stocks.py`** — gỡ hẳn `_index_analysis()` khỏi cả hai endpoint phân tích. Kho RAG giờ chỉ nạp
  từ hai đường có kiểm soát: lịch `reindex-vn30-daily` 8h sáng, và nút reindex của admin.
- `refresh=true` chỉ có tác dụng với **người đã đăng nhập** (`_may_refresh`); khách gửi cờ này thì
  bị **lờ đi im lặng** — trang vẫn xem được, chỉ không ép crawl được.
- `_cache_key()` làm tròn `pe_sec`/`pb_fair` về 2 chữ số → hết trò `9.001, 9.002…` phá cache.
- 3 cache `dict` → **`TTLCache`** có trần (500/500/2000 mục): trước đây quét vài trăm mã lạ là
  bộ nhớ container phình tới lúc bị OOM kill.
- Thêm hạn mức phân tích/ngày: khách 30 (theo IP), thành viên 100, `refresh` 10 — **fail-open**
  (Redis hỏng thì cho qua: rào này bảo vệ nguồn dữ liệu, không đáng để đánh sập cả trang).

### Giả mạo IP (H4) — hóa ra còn nặng hơn kế hoạch dự đoán
`_client_ip` cũ lấy **hop đầu** của `X-Forwarded-For`, tức phần **client tự ghi**. Nhưng khi kiểm tra
đường thật thì phát hiện thêm: proxy Nuxt (`h3.proxyRequest`) **chuyển tiếp nguyên header của client
và không hề ghi thêm IP thật**. Nghĩa là dù có sửa backend, mọi người dùng qua proxy vẫn dùng chung
một rổ đếm, còn header thì vẫn 100% do client kiểm soát. Sửa cả hai đầu:
- **`frontend/server/api/[...].ts`** — proxy nay **ghi đè** `x-forwarded-for` + `x-real-ip` bằng địa
  chỉ socket thật (`getRequestIP(event, { xForwardedFor: false })`).
- **`ratelimit._client_ip`** — chỉ tin header khi người gọi nằm trong `trusted_proxies` (hỗ trợ **dải
  CIDR** vì IP container Docker là động), ưu tiên `x-real-ip`, còn `X-Forwarded-For` thì lấy **hop cuối**.
- **`docker-compose.yml`** — `APP_TRUSTED_PROXIES=["172.16.0.0/12"]`: tin mạng nội bộ compose, còn ai
  gọi thẳng vào cổng API từ ngoài thì header bịa bị lờ đi.

### Ngân sách Gemini (mới: `app/core/budget.py`)
- Đếm **request thật** ở tầng `rag/gemini.py` — nơi mọi lệnh gọi đi qua — chứ không đếm "lượt hỏi".
  Đo được ngay: một câu hỏi = **2 request** (câu đơn giản) đến 7 (agent gọi nhiều công cụ).
- **Xếp hàng** tối đa 2 câu chạy cùng lúc + **thử lại giãn cách** 1s→2s→4s khi Google trả 429.
- **Hạ cấp mềm**: ≥70% quota ngày → tự bỏ agent, lui về RAG một nhịp (1 request thay vì 3–7);
  ≥90% → chỉ phục vụ người đã hỏi trong ngày, người mới nhận lời từ chối **nói thật** thay vì lỗi kỹ thuật.
- **FAIL-CLOSED**: Redis hỏng → không gọi Gemini. Ngược hẳn với rào chống dò mật khẩu (fail-open).
  Lý do: hết quota không mua lại được, thà báo bận vài phút.
- Thêm `QuotaError` tách khỏi `GeminiError`: hết hạn mức thì **không** lui về RAG một nhịp (lui cũng
  vẫn phải gọi Gemini) mà báo thẳng 429 cho người dùng.

### Phân quyền (H3)
- Cột `users.role` + migration **`0005_user_role`** (idempotent) + `deps.require_admin`.
- `POST /chat/reindex` nay là endpoint quản trị.
- Cấp admin đầu tiên: `UPDATE users SET role='admin' WHERE email='...';`

### Rào chung + header bảo mật (H5 một phần)
- Middleware trong `main.py`: **120 request/phút/IP** cho toàn bộ `/api` (trừ `/api/health`), fail-open.
- Header mọi phản hồi: `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `X-Frame-Options: DENY`,
  thêm `Strict-Transport-Security` khi `APP_ENV=prod`.
- `APP_ENV=prod` → tắt `/docs`, `/redoc`, `/openapi.json`.

### Cấu hình đổi
| Biến | Cũ | Mới |
|---|---|---|
| `rag_daily_quota` | 100 | **5** |
| `rag_agent_max_steps` | 5 | **3** |
| `rag_history_turns` | 6 | 4 |
| `gemini_daily_call_cap` | — | 1400 |
| `gemini_max_concurrent` | — | 2 |

### Thêm mới
- `GET /api/chat/quota` → `{limit, used, remaining, level}` để giao diện hiện "còn 4/5 lượt hôm nay"
  thay vì để người dùng đâm vào 429 (phần hiển thị thuộc S4).
- `cachetools` vào `requirements.txt` (**image backend đã build lại**).

## 3. Việc còn phải làm tay

1. **Cấp admin cho tài khoản của bạn** — chưa ai là admin nên nút reindex đang khóa với tất cả:
   ```bash
   docker compose exec -T postgres psql -U invest -d investstudio -c "UPDATE users SET role='admin' WHERE email='hoatq.dev@gmail.com';"
   ```
2. **Đọc quota thật trong AI Studio** rồi đặt `APP_GEMINI_DAILY_CALL_CAP` cho đúng dự án (mặc định 1400 là ước lượng).
3. **Xem lại ngưỡng 70%/90%** của hạ cấp mềm.
4. Chưa commit: mã S0 đang nằm chung working tree với 40 tệp redesign v3 dở dang — nên tách commit.

## 4. Cố ý CHƯA làm trong S0 (nằm ở pha sau)

- Vân tay thiết bị (§2.4) → S1, cùng xác minh email và các rổ hạn mức `min(user, fp, ip, net)`.
- `POST /portfolio/review` vẫn công khai (H7) → S1.
- Kiểm tra magic bytes khi upload (H8), `token_version` (H9), quên mật khẩu (H10) → S1.
- Không publish cổng backend + HTTPS + mật khẩu DB ngẫu nhiên (H5, H6 đầy đủ) → S5.
